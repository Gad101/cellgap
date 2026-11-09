"""Checkpoint 2 tests, Person A: cost model, area model, cones and the candidate flow.

    python3 -m unittest -v tests/test_candidates.py

Each check has a broken case that it must reject (overview, section 4.3, rule 3).
The flow test needs the HD Liberty (make setup), like the redundancy tests.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import aiger                                            # noqa: E402
import candidates                                       # noqa: E402
import costmodel                                        # noqa: E402
import request                                          # noqa: E402
from cmos import is_one_stage, one_stage_transistors   # noqa: E402
from tt import MASK, VARS, canon_tables                 # noqa: E402


def p_classes():
    cp = canon_tables()["P"]
    return sorted({int(cp[t]) for t in range(65536)})


class CostModel(unittest.TestCase):
    def test_every_class_formula_computes_its_function(self):
        """All 3,984 four-input classes: the formula, simulated, equals the class."""
        for t in p_classes():
            self.assertTrue(costmodel.verify(t, costmodel.best(t)), hex(t))

    def test_known_costs(self):
        """Costs checked by hand: transistors, stages, inverters."""
        a, b, c, d = VARS
        known = {
            "nand2": ((a & b) ^ MASK, (4, 1, 0)),
            "and2": (a & b, (6, 2, 1)),                      # nand2 + inverter
            "a21oi": (((a & b) | c) ^ MASK, (6, 1, 0)),
            "maj4n (Appendix A)": (0x077F, (12, 1, 0)),      # handout: 12 transistors, 1 stage
            "and4": (a & b & c & d, (12, 2, 1)),             # nand3 + nor2 + inverter: 4 in series is not allowed
        }
        for name, (t, (tr, st, inv)) in known.items():
            k = costmodel.best(t)
            self.assertEqual((k.transistors, k.stages, k.inverters), (tr, st, inv), name)

    def test_agrees_with_cmos_for_one_stage_functions(self):
        """Whenever cmos.py finds a one-stage form, the model uses exactly that cost."""
        for t in p_classes():
            if is_one_stage(t):
                n = one_stage_transistors(t, max_series=3)
                if n is not None:
                    k = costmodel.best(t)
                    self.assertTrue(k.one_stage and k.transistors == n, hex(t))

    def test_broken_wrong_formula_is_rejected(self):
        """Broken case: a formula for a different function must fail the check."""
        bad = {"truth_table": "0x0707", "expression": "!(A & B)"}   # a formula for a different function
        t = int(bad["truth_table"], 16)
        fake = costmodel.Cost(4, 1, 0, bad["expression"])
        self.assertFalse(costmodel.verify(t, fake))
        self.assertTrue(costmodel.verify(t, costmodel.best(t)))      # the real one passes

    def test_compact_moves_used_inputs_first(self):
        """a21oi's class 0x003F uses B, C, D; a request must call them A, B, C."""
        low, n = costmodel.compact(0x003F)
        self.assertEqual((low, n), (0x0707, 3))


class AreaModel(unittest.TestCase):
    def test_sites_round_up(self):
        m = costmodel.AreaModel({"one-stage": (0.0, 0.7), "multi-stage": (2.0, 0.5)})
        one = costmodel.Cost(12, 1, 0, "")
        multi = costmodel.Cost(10, 2, 1, "")
        self.assertEqual(m.sites(one), 9)            # 8.4 -> 9 sites
        self.assertEqual(m.sites(multi), 7)          # 7.0 stays 7
        self.assertAlmostEqual(m.area(multi), 7 * costmodel.SITE_UM2, places=3)

    def test_fit_reports_its_error(self):
        pts, skipped = costmodel.hd_fit_points()
        _, rep = costmodel.fit(pts)
        for kind in ("one-stage", "multi-stage"):
            self.assertGreaterEqual(rep[kind]["cells"], 5)
            self.assertLess(rep[kind]["mean_abs_error_sites"], 2.0)
        self.assertIn("nand4_1", skipped)            # 4 in series: outside this project's rule


def tiny_aig(shared: bool) -> aiger.AIG:
    """n4 = A & B, n5 = n4 & C, and (if shared) n6 = n4 & !C also uses n4."""
    g = aiger.AIG()
    g.inputs = [1, 2, 3]
    g.ands = {4: (2, 4), 5: (8, 6)}
    g.outputs = [10]
    if shared:
        g.ands[6] = (8, 7)
        g.outputs.append(12)
    return g


class Cones(unittest.TestCase):
    def setUp(self):
        self.pos = lambda g: {v: i for i, v in enumerate(g.topo_ands())}

    def test_unshared_node_disappears(self):
        g = tiny_aig(False)
        e = candidates.exclusive_cone(g, 5, (1, 2, 3), candidates.fanout_counts(g), self.pos(g))
        self.assertEqual(e, frozenset({4, 5}))

    def test_shared_node_stays(self):
        """Broken case for the cone: n4 is also used outside, so it must NOT be counted."""
        g = tiny_aig(True)
        e = candidates.exclusive_cone(g, 5, (1, 2, 3), candidates.fanout_counts(g), self.pos(g))
        self.assertEqual(e, frozenset({5}))

    def test_overlapping_occurrences_are_not_both_used(self):
        occ = [(10, frozenset({1, 2, 3}), 3), (11, frozenset({3, 4}), 2), (12, frozenset({7, 8}), 2)]
        chosen = candidates.pick_disjoint(occ, lambda m: m * 1.0 - 0.5)
        roots = [r for r, _ in chosen]
        self.assertEqual(roots, [10, 12])             # 11 overlaps 10 at node 3

    def test_occurrences_that_lose_area_are_skipped(self):
        occ = [(10, frozenset({1, 2}), 2)]
        self.assertEqual(candidates.pick_disjoint(occ, lambda m: m * 1.0 - 5.0), [])


class Flow(unittest.TestCase):
    def test_requests_and_ranking_on_the_test_designs(self):
        """Run the whole of Person A's flow on our own small designs."""
        with tempfile.TemporaryDirectory() as out:
            r = subprocess.run([sys.executable, os.path.join(ROOT, "src", "candidates.py"),
                                "--designs", "csa8,mux_alu4", "--aig-dir", os.path.join(HERE, "aig"),
                                "--out", out, "--a-and", "2.5", "--group", "g0", "--top", "20"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr[-800:])
            with open(os.path.join(out, "candidates.json")) as fh:
                data = json.load(fh)
            cands = data["candidates"]
            self.assertTrue(cands)
            savings = [c["estimated_saving_um2"] for c in cands]
            self.assertEqual(savings, sorted(savings, reverse=True))
            for c in cands:
                ok, why = request.check(c)           # expression and truth table agree (Appendix A)
                self.assertTrue(ok, "%s: %s" % (c["name"], why))
                self.assertTrue(c["name"].startswith("dd2_g0__"))
                self.assertLessEqual(len(c["inputs"]), 4)
            self.assertIn("--a-and", data["area_per_and_source"]["csa8"])

    def test_missing_baseline_log_is_an_error_not_a_guess(self):
        """Broken case: no Table 1 log and no --a-and must stop, never invent an area."""
        r = subprocess.run([sys.executable, os.path.join(ROOT, "src", "candidates.py"),
                            "--designs", "csa8", "--aig-dir", os.path.join(HERE, "aig"), "--out", tempfile.mkdtemp()],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Table 1 log", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
