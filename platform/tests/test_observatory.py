import unittest
from dataclasses import replace
from matheval.observatory import analytics as A
from matheval.observatory.data import AVG_NAME, load_csv, validate

ROWS = load_csv("data/observatory/pisa_agregados.csv")


class TestObservatory(unittest.TestCase):
    def test_dataset_is_valid_and_has_provenance(self):
        self.assertEqual(validate(ROWS), [])
        self.assertTrue(all(o.source and o.url.startswith("http") for o in ROWS))
        self.assertTrue(any(o.quality == "secundaria" for o in ROWS))

    def test_validation_catches_problems(self):
        bad = ROWS + [replace(ROWS[0]), replace(ROWS[1], mean=900.0), replace(ROWS[2], cycle=1999), replace(ROWS[3], quality="rumor", url="")]
        errs = " | ".join(validate(bad))
        for expected in ("duplicado", "fuera de rango", "ciclo inválido", "calidad inválida", "falta fuente"):
            self.assertIn(expected, errs)

    def test_argentina_series_matches_oecd_snapshot(self):
        s = dict(A.series(ROWS, "Argentina", "matematica"))
        self.assertEqual((s[2006], s[2012], s[2018], s[2022], s[2025]), (381, 388, 379, 378, 367))
        self.assertNotIn(2015, s)                                    # Argentina no tiene dato nacional de 2015
        self.assertEqual(dict(A.series(ROWS, "Argentina", "lectura"))[2000], 418)

    def test_trend_stats(self):
        st = A.trend_stats(A.series(ROWS, "Argentina", "matematica"))
        self.assertEqual((st["first_cycle"], st["last_cycle"], st["total_change"]), (2006, 2025, -14))
        self.assertEqual((st["short_change"], st["short_from"]), (-11, 2022))
        self.assertIn((2012, 2018), st["gaps"])                       # el hueco de 2015 se informa
        self.assertLess(st["slope_per_year"], 0)
        self.assertIsNone(A.trend_stats([(2022, 400.0)]))

    def test_compare_gap_and_years(self):
        c = A.compare(ROWS, "matematica", 2022)
        self.assertEqual(c[0]["entity"], "Hong Kong (China)")
        arg = next(r for r in c if r["entity"] == "Argentina")
        self.assertEqual((arg["gap_vs_oecd"], arg["years_vs_oecd"]), (378 - 472, round((378 - 472) / 20, 1)))
        self.assertEqual([r["entity"] for r in A.compare(ROWS, "matematica", 2022, ["Chile"])], ["Chile"])
        self.assertEqual(A.compare(ROWS, "matematica", 2000), [])

    def test_region_average_needs_enough_entities(self):
        avg = dict(A.region_average(ROWS, "matematica"))
        self.assertAlmostEqual(avg[2022], (378 + 379 + 412 + 383 + 385) / 5, places=1)
        self.assertNotIn(2003, avg)                                  # solo Brasil tiene dato en 2003
        self.assertNotIn(2025, avg)

    def test_focus_argentina(self):
        f = A.focus(ROWS, "Argentina")
        self.assertEqual(set(f["domains"]), {"matematica", "lectura", "ciencias"})
        self.assertEqual(f["domains"]["matematica"]["last"], 367)
        self.assertEqual(f["domains"]["matematica"]["gap_vs_oecd"], 367 - 463)
        self.assertEqual([r["value"] for r in f["below_level2"]], [64, 64, 66, 69, 73, 76])
        self.assertTrue(all(r["quality"] == "secundaria" for r in f["below_level2"]))

    def test_oecd_average_series_present(self):
        s = dict(A.series(ROWS, AVG_NAME, "matematica"))
        self.assertEqual((s[2003], s[2022], s[2025]), (499, 472, 463))
        prov = A.provenance(ROWS, "matematica", ["Argentina", AVG_NAME])
        self.assertTrue(any(p["quality"] == "oficial_ocde" for p in prov) and any(p["quality"] == "secundaria" for p in prov))


if __name__ == "__main__":
    unittest.main()
