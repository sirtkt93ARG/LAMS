import unittest
import numpy as np
from scipy.linalg import hadamard
from matheval.observatory import microdata as MD


def simulate(rng, zones=64, per_psu=25, pv_noise=0.0, M=1, group_effect=0.0):
    """Diseño con 64 zonas de 2 unidades primarias y replicación balanceada con ajuste de Fay (como PISA)."""
    H = hadamard(64)
    n = zones * 2 * per_psu
    zone = np.repeat(np.arange(zones), 2 * per_psu)
    psu = np.tile(np.repeat([0, 1], per_psu), zones)
    base_w = rng.uniform(0.5, 2.0, n)
    zone_eff, psu_eff = rng.normal(0, 15, zones), rng.normal(0, 25, (zones, 2))
    grp = (rng.random(n) < 0.5)
    true = 400 + zone_eff[zone] + psu_eff[zone, psu] + rng.normal(0, 70, n) + group_effect * grp
    pvs = true[:, None] + (rng.normal(0, pv_noise, (n, M)) if pv_noise else 0.0)
    reps = np.empty((n, 64))
    for r in range(64):
        first = H[r, zone] == 1
        sel_first = (psu == 0)
        reps[:, r] = base_w * np.where(first == sel_first, 1.5, 0.5)
    return pvs, base_w, reps, grp, true


class TestMicrodata(unittest.TestCase):
    def test_equal_weights_equal_plain_mean(self):
        x = np.array([[400.0], [500.0], [600.0]]); w = np.ones(3); wr = np.ones((3, 4))
        self.assertAlmostEqual(MD.mean_estimate(x, w, wr)["estimate"], 500.0)

    def test_brr_standard_error_is_calibrated(self):
        """El error estándar por BRR debe coincidir con la dispersión real de la media entre muestras repetidas."""
        rng = np.random.default_rng(1)
        ests, ses = [], []
        for _ in range(150):
            pvs, w, reps, _, _ = simulate(rng)
            r = MD.mean_estimate(pvs, w, reps)
            ests.append(r["estimate"]); ses.append(r["se"])
        empirical, mean_se = float(np.std(ests, ddof=1)), float(np.mean(ses))
        self.assertLess(abs(mean_se / empirical - 1), 0.25, (mean_se, empirical))

    def test_plausible_values_add_imputation_variance(self):
        rng = np.random.default_rng(2)
        pvs, w, reps, _, _ = simulate(rng, pv_noise=40.0, M=10)
        full = MD.mean_estimate(pvs, w, reps)
        one = MD.mean_estimate(pvs[:, :1], w, reps)
        self.assertGreater(full["imputation_var"], 0)
        self.assertAlmostEqual(full["se"] ** 2, full["sampling_var"] + (1 + 1 / 10) * full["imputation_var"], places=8)
        self.assertEqual(one["imputation_var"], 0.0)                      # con un solo valor no hay variación entre valores

    def test_share_levels_sum_to_100_and_cuts(self):
        rng = np.random.default_rng(3)
        pvs, w, reps, _, _ = simulate(rng, pv_noise=20.0, M=5)
        lv = MD.level_shares(pvs, w, reps)
        self.assertEqual(len(lv), 9)
        self.assertAlmostEqual(sum(x["share"] for x in lv), 100.0, places=6)
        self.assertTrue(all(x["se"] >= 0 for x in lv))
        self.assertEqual(MD.MATH_CUTS_2022, (233, 295, 358, 420, 482, 545, 607, 669))
        below2 = MD.share_estimate(pvs, w, reps, lambda x: x < 420)["estimate"]
        self.assertAlmostEqual(below2, sum(x["share"] for x in lv[:4]), places=6)

    def test_gap_and_quartiles_and_slope(self):
        rng = np.random.default_rng(4)
        pvs, w, reps, grp, _ = simulate(rng, group_effect=30.0, pv_noise=10.0, M=5)
        g = MD.gap_estimate(pvs, w, reps, grp, ~grp)
        self.assertGreater(g["estimate"], 15)
        self.assertGreater(g["estimate"] / g["se"], 3)                    # la brecha de 30 puntos es detectable
        self.assertAlmostEqual(g["estimate"], MD.mean_estimate(pvs, w, reps, grp)["estimate"] - MD.mean_estimate(pvs, w, reps, ~grp)["estimate"], places=8)
        escs = rng.normal(0, 1, len(w))
        masks = MD.quartile_masks(escs, w)
        shares = [w[m].sum() / w.sum() for m in masks]
        for s in shares:
            self.assertAlmostEqual(s, 0.25, delta=0.02)
        self.assertTrue((np.sum(masks, axis=0) == 1).all())                # los cuartiles parten a todos
        y = 450 + 40 * escs[:, None] + rng.normal(0, 30, (len(w), 5))
        sl = MD.slope_estimate(y, escs, w, reps)
        self.assertAlmostEqual(sl["estimate"], 40, delta=3)
        self.assertGreater(sl["se"], 0)

    def test_significant_difference_with_link_error(self):
        a = MD.significant_difference(400, 2.0, 380, 2.0)
        self.assertTrue(a["significant"] and a["diff"] == -20)
        b = MD.significant_difference(400, 2.0, 395, 2.0, link_error=0.0)
        c = MD.significant_difference(400, 2.0, 395, 2.0, link_error=6.0)
        self.assertGreater(c["se"], b["se"])                               # el error de vinculación agranda la incertidumbre
        self.assertFalse(c["significant"])

    def test_weighted_quantiles(self):
        x = np.arange(1, 101, dtype=float)
        q = MD.weighted_quantiles(x, np.ones(100))
        self.assertAlmostEqual(q[1], 50.5, delta=0.6)


if __name__ == "__main__":
    unittest.main()
