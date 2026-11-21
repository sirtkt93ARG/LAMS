import json, random, unittest
import numpy as np
from lxml import etree
from matheval import templates as T
from matheval.models import Item, Status, IRTParams
from matheval.numfmt import parse_es_number, fmt_ars, fmt_pct
from matheval.safe_expr import to_sympy, equivalent, UnsafeExpression
from matheval.scoring import score_response
from matheval.qti3 import item_to_qti, QTI_NS
from matheval.bank import ItemBank, BankError
from matheval.xapi import pseudonymize, answered_statement
from matheval.ai_gateway import redact_pii, ContextDrafter, MockProvider
from matheval.levels import level_of, prior_difficulty
from matheval.irt import eap, p_correct
from matheval.adaptive import PoolItem, build_design, MSTSession, CATSession
from matheval.calibration import calibrate_2pl


class TestNumbers(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_es_number("$2.800"), 2800)
        self.assertEqual(parse_es_number("0,5"), 0.5)
        self.assertEqual(parse_es_number("1.234,5"), 1234.5)
        self.assertEqual(parse_es_number("20 %"), 20)
        self.assertIsNone(parse_es_number("abc"))
        self.assertIsNone(parse_es_number("1,2,3"))

    def test_format(self):
        self.assertEqual(fmt_ars(2800), "$2.800")
        self.assertEqual(fmt_pct(100 / 3, 1), "33,3 %")


class TestSafeExpr(unittest.TestCase):
    def test_equivalence(self):
        self.assertTrue(equivalent("1500+200n", "1.500 + 200*n"))
        self.assertTrue(equivalent("n*200+1500", "1500+200n"))
        self.assertTrue(equivalent("200(n)+1500", "1500+200*n"))
        self.assertFalse(equivalent("1500+300n", "1500+200n"))

    def test_rejects_malicious(self):
        for bad in ["__import__('os').system('ls')", "open('/etc/passwd')", "exec(1)", "9**9**9",
                    "n**100", "1/0", "a+b", "n" * 200, "lambda: 1", "[1,2]"]:
            with self.assertRaises(UnsafeExpression, msg=bad):
                to_sympy(bad, ["n"])
            self.assertFalse(equivalent(bad, "n", ["n"]))


class TestTemplates(unittest.TestCase):
    def test_all_templates_verified_and_consistent(self):
        for tid in T.SPEC:
            for seed in range(300):
                it = T.generate(tid, seed)
                self.assertEqual(it.status, Status.VERIFICADO)
                self.assertEqual(Item.from_dict(json.loads(json.dumps(it.to_dict()))).to_dict(), it.to_dict())
                if it.kind == "choice":
                    self.assertEqual(len(it.options), 4)
                    self.assertEqual(len({o.text for o in it.options}), 4)
                    self.assertEqual(score_response(it, it.correct).score, 1.0)
                    wrong = next(o for o in it.options if o.id != it.correct)
                    r = score_response(it, wrong.id)
                    self.assertEqual((r.score, r.tag), (0.0, wrong.tag))

    def test_determinism(self):
        self.assertEqual(T.generate("T1", 7).to_dict(), T.generate("T1", 7).to_dict())

    def test_numeric_and_expression_scoring(self):
        it = T.generate("T6", 4)
        self.assertEqual(score_response(it, str(it.correct)).score, 1.0)
        self.assertEqual(score_response(it, str(it.correct + 1)).score, 0.0)
        self.assertEqual(score_response(it, "doce").tag, "formato_invalido")
        e = T.generate("T3", 4)
        self.assertEqual(score_response(e, f"{e.params['v']}n+{e.params['c']}").score, 1.0)
        self.assertEqual(score_response(e, "").tag, "sin_respuesta")

    def test_tampered_key_is_detected(self):
        it = T.generate("T1", 3)
        it.params["answer"] = str(int(it.params["answer"]) + 10)
        with self.assertRaises(AssertionError):
            T.verify_item(it)


class TestQTI(unittest.TestCase):
    def test_xml_wellformed_and_content(self):
        for tid in T.SPEC:
            it = T.generate(tid, 11)
            root = etree.fromstring(item_to_qti(it))
            ns = {"q": QTI_NS}
            self.assertEqual(root.get("identifier"), it.id)
            self.assertEqual(root.xpath("string(//q:qti-correct-response/q:qti-value)", namespaces=ns), str(it.correct))
            if it.kind == "choice":
                self.assertEqual(len(root.xpath("//q:qti-simple-choice", namespaces=ns)), 4)
            if it.stimulus:
                self.assertTrue(root.xpath("//q:table", namespaces=ns) or it.stimulus["type"] == "rect")


class TestBankGovernance(unittest.TestCase):
    def test_gating(self):
        bank = ItemBank([T.generate("T1", 1)])
        it = bank.items["T1-1"]
        self.assertEqual(bank.pool("medicion"), [])
        with self.assertRaises(BankError):
            bank.promote(it.id, Status.PILOTO)               # salto de estado
        with self.assertRaises(BankError):
            bank.promote(it.id, Status.REVISADO)             # sin revisor
        bank.promote(it.id, Status.REVISADO, reviewed_by="docente-01")
        self.assertEqual(len(bank.pool("practica")), 1)
        self.assertEqual(bank.pool("medicion"), [])
        bank.promote(it.id, Status.PILOTO)
        with self.assertRaises(BankError):
            bank.promote(it.id, Status.CALIBRADO)            # sin parámetros IRT
        it.irt = IRTParams(1.1, -0.3, 0.2)
        bank.promote(it.id, Status.CALIBRADO)
        self.assertEqual(len(bank.pool("medicion")), 1)

    def test_ai_items_need_reviewer(self):
        it = T.generate("T7", 2)
        it.provenance = {"method": "ia"}
        it.status = Status.REVISADO
        with self.assertRaises(BankError):
            ItemBank().add(it)

    def test_noncommercial_license_excluded(self):
        it = T.generate("T7", 3)
        it.license = "CC-BY-NC-SA"
        it.status = Status.OPERATIVO
        self.assertEqual(ItemBank([it]).pool("practica"), [])


class TestPrivacyAndXapi(unittest.TestCase):
    def test_pseudonym_and_statement(self):
        a = pseudonymize("alumno-123", b"secreto-escuela-1")
        self.assertEqual(a, pseudonymize("alumno-123", b"secreto-escuela-1"))
        self.assertNotEqual(a, pseudonymize("alumno-123", b"secreto-escuela-2"))
        self.assertNotIn("alumno-123", a)
        s = answered_statement(pid=a, tenant_home="https://escuela1.example", item_id="T1-1", item_title="Descuento",
                               response="A", score=0.0, success=False, level_target=4, axis="numeros_algebra",
                               process="resolver", tag="suma_en_lugar_de_restar")
        self.assertEqual(s["actor"]["account"]["name"], a)
        self.assertNotIn("mbox", json.dumps(s))
        self.assertEqual(s["verb"]["id"], "http://adlnet.gov/expapi/verbs/answered")

    def test_redaction_and_drafts(self):
        self.assertEqual(redact_pii("escribime a ana@mail.com o al 11 5555-1234"), "escribime a [email] o al [telefono]")
        drafts = ContextDrafter(MockProvider()).draft("T3", "bicicletas", 2)
        self.assertEqual(len(drafts), 2)
        self.assertEqual(drafts[0].provenance["status"], "borrador")


class TestIRTandAdaptive(unittest.TestCase):
    def test_levels_and_prior(self):
        self.assertEqual(level_of(-3), 1)
        self.assertEqual(level_of(0.05), 5)
        self.assertEqual(level_of(3), 8)
        self.assertLess(prior_difficulty(1), prior_difficulty(8))

    def test_eap_monotone(self):
        prm = IRTParams(1.2, 0.0, 0.0)
        hi, _ = eap([(prm, 1)] * 5)
        lo, _ = eap([(prm, 0)] * 5)
        self.assertGreater(hi, 0.5)
        self.assertLess(lo, -0.5)

    def _pool(self, n=200, seed=1):
        r = np.random.default_rng(seed)
        axes = ["numeros_algebra", "funciones_relaciones", "geometria_medida", "datos_azar"]
        return [PoolItem(f"i{k}", axes[k % 4], IRTParams(float(r.uniform(.8, 1.6)), float(np.clip(r.normal(-.5, 1.3), -3, 3)), 0.0))
                for k in range(n)]

    def test_mst_randomizes_exposure_without_repeating_content(self):
        axes = ["numeros_algebra", "funciones_relaciones", "geometria_medida", "datos_azar"]
        pool = [PoolItem(f"i{k}", axes[k % 4], IRTParams(1.0, (k % 17 - 8) / 4, 0.0), f"fp-{k}")
                for k in range(240)]
        first = build_design(pool, rng=random.Random(11))
        second = build_design(pool, rng=random.Random(29))
        self.assertNotEqual(first.stage1, second.stage1)
        by_id = {p.id: p for p in pool}
        for design in (first, second):
            ids = design.stage1 + [i for block in design.stage2.values() for i in block] + [i for block in design.stage3.values() for i in block]
            self.assertEqual(len(ids), len(set(ids)))
            fps = [by_id[i].fp for i in ids]
            self.assertEqual(len(fps), len(set(fps)))

    def test_mst_routing_and_balance(self):
        pool = self._pool()
        d = build_design(pool)
        params = {p.id: p.params for p in pool}
        used = d.stage1 + [i for v in d.stage2.values() for i in v] + [i for v in d.stage3.values() for i in v]
        self.assertEqual(len(used), len(set(used)))                       # sin ítems repetidos
        axes = {p.id: p.axis for p in pool}
        self.assertEqual(len({axes[i] for i in d.stage1}), 4)             # balance de contenido
        strong = MSTSession(d, params)
        weak = MSTSession(d, params)
        for s, ok in ((strong, 1), (weak, 0)):
            while not s.done:
                for iid in s.next_items():
                    s.record(iid, ok)
        self.assertEqual(strong.route, ["high", "high"])
        self.assertEqual(weak.route, ["low", "low"])
        self.assertGreater(strong.estimate()[0], weak.estimate()[0])

    def test_cat_no_repeats_and_axis_balance(self):
        pool = self._pool()
        params = {p.id: p.params for p in pool}
        s = CATSession(pool, max_items=20, seed=3)
        rng = random.Random(5)
        while (iid := s.next_item()) is not None:
            s.record(iid, int(rng.random() < p_correct(0.0, params[iid].a, params[iid].b)))
        self.assertEqual(len(s.administered), 20)
        self.assertEqual(len(set(s.administered)), 20)
        self.assertEqual(max(s.axis_count.values()) - min(s.axis_count.values()), 0)

    def test_calibration_recovers_parameters(self):
        r = np.random.default_rng(7)
        J, N = 30, 1500
        a = r.uniform(.8, 1.6, J); b = r.uniform(-2, 2, J)
        th = r.normal(0, 1, N)
        Y = (r.random((N, J)) < p_correct(th[:, None], a[None], b[None])).astype(float)
        Y[r.random((N, J)) < 0.3] = np.nan                                  # 30% de datos faltantes
        ea, eb = calibrate_2pl(Y)
        self.assertGreater(np.corrcoef(b, eb)[0, 1], 0.97)
        self.assertGreater(np.corrcoef(a, ea)[0, 1], 0.70)


if __name__ == "__main__":
    unittest.main()
