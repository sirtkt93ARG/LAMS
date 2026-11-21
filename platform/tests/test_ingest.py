import csv, os, tempfile, unittest
import numpy as np
import pandas as pd
from matheval.observatory import ingest as I
from matheval.observatory.analytics import significant_changes
from matheval.observatory.data import load_csv, load_gaps, validate
from tests.test_microdata import simulate


def fake_pisa_file(path, rng, country="ARG", mean_shift=0.0, n_reps=64):
    """CSV con las columnas de los microdatos de PISA (valores plausibles, pesos y réplicas, ESCS y género)."""
    pvs, w, reps, grp, _ = simulate(rng, pv_noise=25.0, M=10, group_effect=20.0)
    n = len(w)
    escs = rng.normal(-0.6, 1.0, n)
    pvs = pvs + 30 * escs[:, None] + mean_shift
    df = pd.DataFrame({"CNT": country, "W_FSTUWT": w, "ESCS": escs, "ST004D01T": np.where(grp, 1, 2)})
    for g in range(n_reps):
        df[f"W_FSTURWT{g + 1}"] = reps[:, g]
    for dom in ("MATH", "READ", "SCIE"):
        for m in range(10):
            df[f"PV{m + 1}{dom}"] = pvs[:, m] + {"MATH": 0, "READ": 15, "SCIE": 20}[dom]
    other = df.head(50).copy(); other["CNT"] = "CHL"
    pd.concat([df, other]).to_csv(path, index=False)
    return pvs


class TestIngest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.agg = os.path.join(self.tmp.name, "agg.csv"); self.gaps = os.path.join(self.tmp.name, "gaps.csv")
        self.spec = I.ColumnSpec(n_reps=64)
        self.rng = np.random.default_rng(5)

    def tearDown(self):
        self.tmp.cleanup()

    def test_pipeline_reconciles_and_writes_valid_files(self):
        src = os.path.join(self.tmp.name, "stu.csv")
        pvs = fake_pisa_file(src, self.rng)
        truth = float(pvs.mean())
        with open(self.agg, "w", newline="", encoding="utf-8") as f:                    # CSV previo con el valor «publicado»
            w = csv.DictWriter(f, fieldnames=I.AGG_FIELDS); w.writeheader()
            w.writerow(dict.fromkeys(I.AGG_FIELDS, "") | {"ciclo": 2022, "dominio": "matematica", "entidad": "Argentina", "grupo": "America Latina",
                                                          "media": round(truth), "fuente": "OCDE", "url": "http://x", "calidad": "oficial_ocde"})
        rep = I.run(src, 2022, "ARG", "Argentina", spec=self.spec, agg_path=self.agg, gaps_path=self.gaps)
        by = {r["dominio"]: r for r in rep}
        self.assertTrue(by["matematica"]["conciliada"])                                   # coincide con lo «publicado»
        self.assertIsNone(by["lectura"]["publicada"])                                     # no había dato publicado
        self.assertGreater(by["matematica"]["se"], 0)
        rows = load_csv(self.agg)
        self.assertEqual(validate(rows), [])
        mat = next(o for o in rows if o.domain == "matematica")
        self.assertEqual((mat.quality, mat.se is not None, mat.below_l2 is not None), ("oficial_ocde", True, True))   # conserva la calidad oficial
        new = next(o for o in rows if o.domain == "lectura")
        self.assertEqual(new.quality, "microdatos_propios")
        gaps = load_gaps(self.gaps)
        dims = {g.dimension for g in gaps}
        self.assertEqual(dims, {"genero", "genero_brecha", "escs_cuartil", "escs_brecha", "escs_pendiente"})
        gb = next(g for g in gaps if g.dimension == "genero_brecha" and g.domain == "matematica")
        self.assertGreater(gb.value, 5)                                                  # se simuló una ventaja de 20 puntos
        slope = next(g for g in gaps if g.dimension == "escs_pendiente" and g.domain == "matematica")
        self.assertAlmostEqual(slope.value, 30, delta=6)
        q = [g.value for g in gaps if g.dimension == "escs_cuartil" and g.domain == "matematica"]
        self.assertEqual(len(q), 4)
        self.assertEqual(q, sorted(q))                                                    # más ESCS, más puntaje

    def test_second_cycle_updates_without_duplicates_and_tests_change(self):
        for cycle, shift, seed in ((2018, 0.0, 6), (2022, -25.0, 7)):
            src = os.path.join(self.tmp.name, f"s{cycle}.csv")
            fake_pisa_file(src, np.random.default_rng(seed), mean_shift=shift)
            I.run(src, cycle, "ARG", "Argentina", domains=("matematica",), spec=self.spec, agg_path=self.agg, gaps_path=self.gaps)
        I.run(os.path.join(self.tmp.name, "s2022.csv"), 2022, "ARG", "Argentina", domains=("matematica",), spec=self.spec, agg_path=self.agg, gaps_path=self.gaps)
        rows = load_csv(self.agg)
        self.assertEqual(validate(rows), [])
        self.assertEqual(len(rows), 2)                                                    # la corrida repetida no duplica
        ch = significant_changes(rows, "Argentina", "matematica")
        self.assertEqual(len(ch), 1)
        self.assertTrue(ch[0]["significant"] and ch[0]["diff"] < -15)
        with_link = significant_changes(rows, "Argentina", "matematica", {(2018, 2022): 50.0})
        self.assertFalse(with_link[0]["significant"])                                     # un error de vinculación grande lo anula

    def test_missing_country_and_format_errors(self):
        src = os.path.join(self.tmp.name, "s.csv")
        fake_pisa_file(src, self.rng)
        with self.assertRaises(ValueError):
            I.run(src, 2022, "XXX", "Nada", spec=self.spec, agg_path=self.agg, gaps_path=self.gaps)
        with self.assertRaises(ValueError):
            I.load_table("datos.xlsx", ["CNT"], ["ARG"])


if __name__ == "__main__":
    unittest.main()
