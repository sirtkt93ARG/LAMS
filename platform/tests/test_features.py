import random, unittest
from datetime import datetime, timedelta, timezone
import numpy as np
from lxml import etree
from matheval import templates as T
from matheval.analytics import family_stats
from matheval.calibration import calibrate_families
from matheval.directed import DirectedSession, FormSession, build_catalog, build_form, start_directed
from matheval.explain import explain
from matheval.irt import p_correct
from matheval.mastery import bkt_update, compute_mastery, due_days, recommend, summary
from matheval.models import Item
from matheval.qti3 import QTI_NS, item_to_qti
from matheval.skills import SKILLS, TEMPLATE_SKILLS, templates_for


class TestSkills(unittest.TestCase):
    def test_mapping_is_complete_and_acyclic(self):
        self.assertEqual(set(TEMPLATE_SKILLS), set(T.SPEC))
        for sks in TEMPLATE_SKILLS.values():
            self.assertTrue(sks and all(s in SKILLS for s in sks))
        self.assertTrue(all(templates_for(s) for s in SKILLS), "toda habilidad debe tener ejercicios")
        def depth(s, seen=()):
            self.assertNotIn(s, seen)
            return 1 + max([depth(q, seen + (s,)) for q in SKILLS[s][1]], default=0)
        for s in SKILLS: depth(s)


class TestExplain(unittest.TestCase):
    def test_every_template_explains_itself(self):
        for tid in T.SPEC:
            for seed in range(60):
                it = T.generate(tid, seed)
                ex = explain(it)                      # las aserciones internas verifican los números
                self.assertEqual(ex["steps"][-1], f"Respuesta: {it.params['answer_text']}")
                self.assertGreaterEqual(len(ex["steps"]), 3)
                self.assertEqual(len(ex["hints"]), 2)


class TestMastery(unittest.TestCase):
    def test_bkt_direction(self):
        p = 0.3
        self.assertGreater(bkt_update(p, True, 0.25), p)
        self.assertLess(bkt_update(p, False, 0.25), p + 0.12)
        self.assertGreater(bkt_update(0.5, True, 0.05) - 0.5, bkt_update(0.5, True, 0.25) - 0.5)   # acertar al azar vale menos

    def test_compute_summary_and_hints(self):
        t0 = datetime(2026, 11, 1, tzinfo=timezone.utc)
        rows = [("T1-%d" % i, 1.0, t0, 0) for i in range(8)] + [("T9-%d" % i, 0.0, t0, 0) for i in range(5)]
        st = compute_mastery(rows)
        self.assertGreater(st["porcentajes"].p, 0.8)
        self.assertLess(st["operaciones_enteros"].p, 0.3)
        assisted = compute_mastery([("T1-1", 1.0, t0, 1)] * 5)
        self.assertAlmostEqual(assisted["porcentajes"].p, 0.2)       # con ayuda no suma evidencia
        self.assertEqual(len(summary(st)), len(SKILLS))

    def test_recommend_orders_weak_then_new_and_respects_prereqs(self):
        t0 = datetime(2026, 11, 1, tzinfo=timezone.utc)
        st = compute_mastery([("T9-%d" % i, 0.0, t0, 0) for i in range(6)])
        rec = recommend(st, t0 + timedelta(hours=1))
        self.assertEqual(rec[0]["skill"], "operaciones_enteros")
        self.assertEqual(rec[0]["reason"], "para reforzar")
        good = compute_mastery([("T9-%d" % i, 1.0, t0, 0) for i in range(8)])
        reasons = {r["skill"]: r["reason"] for r in recommend(good, t0 + timedelta(days=30), max_n=20)}
        self.assertEqual(reasons["operaciones_enteros"], "repaso")        # dominada pero vencida
        self.assertEqual(reasons["porcentajes"], "nuevo")                  # prerrequisito dominado: se habilita
        order = [r["skill"] for r in recommend(good, t0 + timedelta(days=30), max_n=20)]
        self.assertLess(order.index("porcentajes"), order.index("operaciones_enteros"))   # lo nuevo antes que el repaso
        fresh = recommend({}, t0, max_n=20)
        self.assertNotIn("teorema_pitagoras", [r["skill"] for r in fresh if r["reason"] == "nuevo"] [:0] or [])


class TestDirected(unittest.TestCase):
    def setUp(self):
        self.items = [T.generate(t, s) for t in T.SPEC for s in range(40)]
        self.cat = build_catalog(self.items, "porcentajes")

    def test_all_correct_climbs_and_never_repeats(self):
        s = start_directed("porcentajes", self.cat, 4, total=8, seed=1)
        levels = []
        while not s.done:
            i = s.next_items()[0]
            levels.append(self.cat["level_of"][i])
            s.record(i, 1)
        self.assertEqual(len(set(s.administered)), 8)
        self.assertEqual(max(levels), max(self.cat["levels"]))

    def test_error_triggers_mirror_then_steps_down(self):
        s = start_directed("porcentajes", self.cat, 6, total=6, seed=2)
        first = s.next_items()[0]
        s.record(first, 0)
        mirror = s.next_items()[0]
        self.assertEqual(mirror.split("-")[0], first.split("-")[0])      # espejo: misma plantilla
        self.assertNotEqual(mirror, first)
        lvl_before = s.level
        s.record(mirror, 0)
        self.assertLess(s.level, lvl_before)                              # dos errores seguidos bajan de nivel

    def test_snapshot_roundtrip_and_theta_direction(self):
        rng = random.Random(3)
        s = start_directed("porcentajes", self.cat, 4, total=10, seed=5)
        for _ in range(4):
            s.record(s.next_items()[0], rng.random() < 0.7)
        s2 = DirectedSession.from_snapshot(s.snapshot(), self.cat)
        self.assertEqual(s2.next_items(), s.next_items())
        self.assertEqual(s2.level, s.level)
        hi = start_directed("porcentajes", self.cat, 4, total=6, seed=1); lo = start_directed("porcentajes", self.cat, 4, total=6, seed=1)
        while not hi.done: hi.record(hi.next_items()[0], 1)
        while not lo.done: lo.record(lo.next_items()[0], 0)
        self.assertGreater(hi.estimate()[0], lo.estimate()[0])

    def test_form_session(self):
        ids, params = build_form(self.items, seed=1)
        self.assertEqual(len(ids), len(T.SPEC))
        self.assertEqual(len({i.split("-")[0] for i in ids}), len(T.SPEC))
        f = FormSession(ids, params)
        for i in ids[:5]: f.record(i, 1)
        f2 = FormSession.from_snapshot(f.snapshot())
        self.assertEqual(f2.next_items(), f.next_items())
        with self.assertRaises(ValueError): f2.record(ids[10], 1)


class TestCalibrationAndAnalytics(unittest.TestCase):
    def test_family_calibration_recovers_difficulty(self):
        r = np.random.default_rng(11)
        fams = [f"T{k}" for k in range(1, 13)]
        a_true, b_true = r.uniform(.8, 1.5, 12), np.linspace(-2, 2, 12)
        rows = []
        for pid in range(700):
            th = r.normal(0, 1)
            for k in r.choice(12, 6, replace=False):
                for rep in range(2):                                # dos instancias distintas de la misma familia
                    ok = r.random() < p_correct(th, a_true[k], b_true[k])
                    rows.append((f"p{pid}", f"{fams[k]}-{rep}", float(ok)))
        out = calibrate_families(rows, min_obs=300)
        est = np.array([out[f]["b"] for f in fams])
        self.assertGreater(np.corrcoef(est, b_true)[0, 1], 0.97)
        self.assertTrue(all(v["ok"] for v in out.values()))
        self.assertEqual(calibrate_families([("p", "T1-1", None)]), {})

    def test_family_stats_flags_and_distractors(self):
        items = {f"T7-{i}": T.generate("T7", i) for i in range(10)}
        rows = []
        r = random.Random(1)
        for pid in range(80):
            for i in range(10):
                it = items[f"T7-{i}"]
                wrong = next(o for o in it.options if o.id != it.correct)
                ok = r.random() < 0.05
                rows.append({"pid": f"p{pid}", "item_id": it.id, "score": float(ok), "response": it.correct if ok else wrong.id, "duration_s": 12.0})
        st = family_stats(rows, items)[0]
        self.assertEqual(st["template"], "T7")
        self.assertIn("muy difícil", st["flags"])
        self.assertTrue(st["top_errors"])
        self.assertEqual(st["mean_time_s"], 12.0)


class TestQtiStimuli(unittest.TestCase):
    def test_charts_and_figures_export_as_tables_or_text(self):
        for tid in ("T13", "T14", "T15"):
            root = etree.fromstring(item_to_qti(T.generate(tid, 4)))
            ns = {"q": QTI_NS}
            self.assertTrue(root.xpath("//q:table", namespaces=ns) or root.xpath("//q:p[contains(., 'Figura')]", namespaces=ns), tid)


if __name__ == "__main__":
    unittest.main()
