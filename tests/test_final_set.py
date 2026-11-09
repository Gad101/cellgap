"""Tests of the checkpoint-3 scripts. They run without Yosys: the mapping is replaced by a table of areas.

Each check has its broken case written inline (AGENTS.md rule 1: nothing is added to tests/broken/).
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import final_flow as ff                       # noqa: E402
import final_table5 as ft                     # noqa: E402
import isa_compare as isa                     # noqa: E402
import make_curve as mc                       # noqa: E402
import real_lib as rl                         # noqa: E402
import run_cellweaver as rc                   # noqa: E402
import select_final_set as sel                # noqa: E402
import sensitivity as sens                    # noqa: E402

DESIGNS = ["d1", "d2"]


def fake_flow(gains):
    """Patch ff so a library is just the names of its cells; area = 100 - the gains of its cells (script A),
    script B is 5 larger. gains: {cell name: um2 saved in d1}."""
    def build_lib(cells, out):
        return "|".join(c["name"] for c in cells)

    def map_all(lib, sha, designs, logdir, netdir=None, jobs=None):
        names = [n for n in sha.split("|") if n]
        g = sum(gains[n] for n in names)
        return {(d, s): (100.0 - (g if d == "d1" else 0.0) + (5.0 if s == "B" else 0.0), {n: 1 for n in names})
                for d in designs for s in "AB"}
    return build_lib, map_all


class GreedyTest(unittest.TestCase):
    def run_greedy(self, gains, max_cells=10):
        reqs = [{"request_id": "C-%03d" % i, "name": n, "truth_table": "0x0", "estimated_area_um2": 1.0}
                for i, n in enumerate(gains, 1)]
        old = (ff.build_lib, ff.map_all, sel.WORK)
        ff.build_lib, ff.map_all = fake_flow(gains)
        sel.WORK = tempfile.mkdtemp()
        try:
            return sel.greedy(reqs, max_cells, None, designs=DESIGNS)
        finally:
            ff.build_lib, ff.map_all, sel.WORK = old

    def test_keeps_cells_that_help_in_order(self):
        r = self.run_greedy({"a": 10.0, "b": 4.0})
        self.assertEqual([c["name"] for c in r["kept"]], ["a", "b"])
        self.assertEqual(r["baseline_total_um2"], 200.0)
        self.assertEqual(r["final_total_um2"], 186.0)
        self.assertEqual([s["total_um2"] for s in r["kept_rows"]], [190.0, 186.0])

    def test_broken_cell_that_makes_area_larger_is_dropped(self):
        r = self.run_greedy({"a": 10.0, "worse": -3.0, "b": 4.0})
        self.assertEqual([c["name"] for c in r["kept"]], ["a", "b"])
        self.assertEqual([x["decision"] for x in r["log"]], ["keep", "drop", "keep"])

    def test_broken_gain_below_rounding_is_dropped(self):
        r = self.run_greedy({"tiny": 0.01})
        self.assertEqual(r["kept"], [])
        self.assertEqual(r["final_total_um2"], r["baseline_total_um2"])

    def test_stops_after_max_cells(self):
        r = self.run_greedy({"a": 5.0, "b": 4.0, "c": 3.0}, max_cells=2)
        self.assertEqual([c["name"] for c in r["kept"]], ["a", "b"])
        self.assertEqual(len(r["log"]), 2)          # c is never tried


class CurveTest(unittest.TestCase):
    FS = {"baseline_total_um2": 200.0, "steps": [
        {"order": 1, "name": "a", "total_um2": 190.0, "reduction_pct": 5.0},
        {"order": 2, "name": "b", "total_um2": 186.0, "reduction_pct": 7.0}]}

    def test_points_and_gains(self):
        p = mc.points(self.FS)
        self.assertEqual([x["cells"] for x in p], [0, 1, 2])
        self.assertEqual([x["step_gain_um2"] for x in p], [0.0, 10.0, 4.0])
        self.assertAlmostEqual(sum(x["step_gain_um2"] for x in p), p[0]["total_um2"] - p[-1]["total_um2"])

    def test_svg_has_one_marker_per_point(self):
        self.assertEqual(mc.svg(mc.points(self.FS)).count("<circle"), 3)

    def test_broken_no_cells_still_draws(self):
        p = mc.points({"baseline_total_um2": 50.0, "steps": []})
        self.assertEqual(mc.svg(p).count("<circle"), 1)


class RealLibTest(unittest.TestCase):
    LIB = 'library (x) {\n cell ("c1") { area : 1; pin ("A") { direction : "input"; } }\n cell ("c2") { area : 2; }\n}\n'

    def test_replaces_only_named_group(self):
        out = rl.replace_cells(self.LIB, {"c1": 'cell ("c1") { area : 9; pin ("A") { x : 1; } }'})
        self.assertIn("area : 9", out)
        self.assertIn('cell ("c2") { area : 2; }', out)
        self.assertNotIn("area : 1;", out)

    def test_broken_missing_cell_is_an_error(self):
        with self.assertRaises(ValueError):
            rl.replace_cells(self.LIB, {"nope": 'cell ("nope") { }'})

    def test_broken_unbalanced_group_is_an_error(self):
        with self.assertRaises(ValueError):
            rl.group('cell ("c1") { area : 1; ', "c1")


class CellweaverTest(unittest.TestCase):
    GEN = ('/* Measured */\nlibrary (c__tt) {\n  lu_table_template (del_1_7_7) { }\n  cell (c) {\n    area : 8.7584;\n'
           '    pin (Y) { function : "!A"; }\n  }\n}\n')

    def test_command_keeps_name_and_formula(self):
        cmd = rc.command("py", {"name": "dd2_gb2__f17_1", "expression": "!(A & B)"}, "out", "single", 2)
        self.assertEqual(cmd[cmd.index("--name") + 1], "dd2_gb2__f17_1")
        self.assertEqual(cmd[cmd.index("--function") + 1], "!(A & B)")
        self.assertIn("--verify", cmd)
        self.assertIn("--characterize", cmd)

    def test_generator_style_cell_group_is_found_and_swapped(self):
        s, e = rl.group(self.GEN, "c")
        self.assertTrue(self.GEN[s:e].startswith("cell (c)"))
        self.assertTrue(self.GEN[s:e].endswith("}"))
        out = rl.replace_cells('library (x) {\n  cell ("c") { area : 1; }\n}\n', {"c": self.GEN[s:e]})
        self.assertIn("area : 8.7584", out)
        self.assertNotIn("lu_table_template", out)       # the generator's header is not copied

    def test_broken_other_cell_name_is_not_matched(self):
        with self.assertRaises(ValueError):
            rl.group(self.GEN, "c2")


class SensitivityTest(unittest.TestCase):
    def test_scale_changes_only_area(self):
        r = {"name": "n", "estimated_area_um2": 10.0, "truth_table": "0x1"}
        s = ff.with_area_scale(r, 0.7)
        self.assertEqual(s["estimated_area_um2"], 7.0)
        self.assertEqual(r["estimated_area_um2"], 10.0)     # the original is untouched

    def test_most_used_cell(self):
        rows = [{"library": "est", "design": "cpu8", "new_cells": "a:1 b:5"},
                {"library": "est", "design": "dsp8", "new_cells": "a:2"},
                {"library": "est", "design": "spm", "new_cells": "a:50"},      # not a required design
                {"library": "real", "design": "cpu8", "new_cells": "a:99"}]    # not the estimated library
        self.assertEqual(sens.most_used(rows, ["a", "b"]), "b")

    def test_broken_no_instances_gives_first_cell(self):
        self.assertEqual(sens.most_used([], ["a", "b"]), "a")


class TableTest(unittest.TestCase):
    def rows(self, eq_new):
        base = {(d, s): 100.0 for d in ft.ANALYSED for s in "AB"}
        new = {(d, s): (90.0 if s == "A" else 95.0, {"x": 2}) for d in ft.ANALYSED for s in "AB"}
        eq = {(d, s): (eq_new, "cec") for d in ft.ANALYSED for s in "AB"}
        beq = {(d, s): "pass" for d in ft.ANALYSED for s in "AB"}
        return ft.build_rows(base, beq, new, eq, {}, "est")

    def test_reduction_best_of_both_and_total(self):
        rows, best, tot = self.rows("pass")
        self.assertEqual(rows[0]["reduction_pct"], 10.0)
        self.assertEqual(best[0]["with_new_cells_um2"], 90.0)
        n = len(ft.REQUIRED)
        self.assertEqual(tot, (100.0 * n, 90.0 * n))        # SPM and mul are not in the total
        self.assertEqual(rows[0]["worst_delay_new_ns"], "n/a")

    def test_broken_failed_equivalence_is_marked(self):
        rows, _, _ = self.rows("FAIL")
        self.assertTrue(all(r["equivalence"] == "FAIL" for r in rows))


class IsaTest(unittest.TestCase):
    def test_overlap(self):
        self.assertEqual(isa.overlap(["a", "b"], ["b", "c"]), (1, round(1 / 3, 3)))

    def test_broken_empty_lists(self):
        self.assertEqual(isa.overlap([], []), (0, 0.0))


if __name__ == "__main__":
    unittest.main()
