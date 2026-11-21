"""Flujo completo con el banco de demostración: generación -> sesión multietapa -> corrección -> informe."""
import random, unittest
from matheval.bank import ItemBank
from matheval.irt import p_correct
from matheval.levels import level_of, prior_difficulty
from matheval.models import IRTParams, Status
from matheval.adaptive import PoolItem, build_design, MSTSession
from matheval.scoring import score_response


class TestEndToEnd(unittest.TestCase):
    def test_session_on_demo_bank(self):
        bank = ItemBank.load("data/bank_demo.jsonl")
        items = [i for i in bank.items.values() if i.status == Status.VERIFICADO]
        prm = {i.id: IRTParams(1.0, prior_difficulty(i.target_level), 0.25 if i.kind == "choice" else 0.0) for i in items}
        pool = [PoolItem(i.id, i.axis.value, prm[i.id]) for i in items]
        design = build_design(pool)
        rng = random.Random(1)
        results = {}
        for theta in (-2.5, -1.0, 0.5, 2.0):
            s = MSTSession(design, prm)
            while not s.done:
                for iid in s.next_items():
                    it = bank.items[iid]
                    ok = rng.random() < p_correct(theta, prm[iid].a, prm[iid].b, prm[iid].c)
                    if it.kind == "choice":
                        resp = it.correct if ok else next(o.id for o in it.options if o.id != it.correct)
                    elif it.kind == "numeric":
                        resp = str(it.correct if ok else it.correct + 1)
                    else:
                        resp = str(it.correct) if ok else "1+n"
                    sc = score_response(it, resp)
                    self.assertEqual(sc.score, 1.0 if ok else 0.0)
                    s.record(iid, int(sc.score))
            self.assertEqual(len(s.administered), 24)
            results[theta] = level_of(s.estimate()[0])
        levels = list(results.values())
        self.assertEqual(levels, sorted(levels))          # más habilidad -> nivel igual o mayor
        self.assertLess(levels[0], levels[-1])


if __name__ == "__main__":
    unittest.main()
