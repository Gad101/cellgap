"""make test: every check, and the broken case that shows each check works.

Run:  python3 -m unittest -v tests/test_all.py   (or: make test)
Needs: build/pdk/<HD Liberty> (make setup) and tests/aig/*.aag (committed;
regenerate with make test-aigs).
"""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import aiger                                    # noqa: E402
import cuts                                     # noqa: E402
import redundancy                               # noqa: E402
import request                                  # noqa: E402
from boolexpr import truth_table                # noqa: E402
from tt import MASK, VARS, canon_tables, flip_input, support  # noqa: E402

BROKEN = os.path.join(ROOT, "tests", "broken")
AIGS = os.path.join(ROOT, "tests", "aig")


def broken(name):
    with open(os.path.join(BROKEN, name)) as f:
        return json.load(f)


class TruthTables(unittest.TestCase):
    def test_appendix_a_example(self):
        # overview, Appendix A: this expression has truth table 0x077F
        t = truth_table("!((C & D) | (A & B & (C | D)))", list("ABCD"))
        self.assertEqual(t, 0x077F)

    def test_input_patterns(self):
        self.assertEqual(truth_table("A", list("ABCD")), 0xAAAA)
        self.assertEqual(truth_table("D", list("ABCD")), 0xFF00)
        self.assertEqual(truth_table("!A", list("A")), 0x5555)

    def test_known_class_counts(self):
        # textbook counts of 4-input function classes: 3984 under input
        # permutation, 222 NPN classes
        import numpy as np
        c = canon_tables()
        self.assertEqual(len(np.unique(c["P"])), 3984)
        self.assertEqual(len(np.unique(c["NPN"])), 222)

    def test_flip_and_support(self):
        self.assertEqual(flip_input(VARS[0], 0), VARS[0] ^ MASK)
        self.assertEqual(support(VARS[0] & VARS[2]), (0, 2))


class Requests(unittest.TestCase):
    def test_good_request(self):
        ok, _ = request.check({"inputs": list("ABCD"), "truth_table": "0x077F",
                               "expression": "!((C & D) | (A & B & (C | D)))"})
        self.assertTrue(ok)

    def test_broken_request_is_refused(self):
        b = broken("wrong_expression.json")
        ok, why = request.check(b)
        self.assertFalse(ok, "a wrong truth table must be refused")


class Cuts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = {d: aiger.read(os.path.join(AIGS, d + ".aag")) for d in ("csa8", "mux_alu4")}
        cls.cuts = {d: cuts.enumerate_cuts(g) for d, g in cls.g.items()}

    def test_every_cut_checks(self):
        for d in self.g:
            errs = cuts.check_cuts(self.g[d], self.cuts[d])
            self.assertEqual(errs, [], "%s: %s" % (d, errs[:3]))

    def test_binary_and_ascii_aiger_agree(self):
        b = os.path.join(AIGS, "csa8.aig")
        if not os.path.exists(b):
            self.skipTest("no binary AIG")
        gb = aiger.read(b)
        sb = cuts.summarize(gb, cuts.enumerate_cuts(gb))
        sa = cuts.summarize(self.g["csa8"], self.cuts["csa8"])
        for k in ("ands", "cuts", "po_classes", "cuts_by_leaves"):
            self.assertEqual(sa[k], sb[k], k)

    def test_at_most_four_leaves(self):
        for d, c in self.cuts.items():
            self.assertTrue(all(len(k) <= 4 for v in c for k, _ in c[v]))

    def _all_cuts(self, d):
        g = self.g[d]
        return [(v, k, t) for v in g.topo_ands() for k, t in self.cuts[d][v][1:]]

    def test_broken_wrong_table_is_caught(self):
        b = broken("wrong_cut_table.json")
        d = b["design"]
        root, leaves, t = self._all_cuts(d)[b["cut_index"]]
        bad = dict(self.cuts[d])
        bad[root] = [c if c[0] != leaves else (leaves, t ^ (1 << b["flip_row"])) for c in bad[root]]
        self.assertNotEqual(cuts.check_cuts(self.g[d], bad), [], "flipped row not caught")

    def test_broken_not_a_cut_is_caught(self):
        b = broken("not_a_cut.json")
        d = b["design"]
        root, leaves, t = next(x for x in self._all_cuts(d) if len(x[1]) >= b["min_leaves"])
        short_leaves = tuple(x for i, x in enumerate(leaves) if i != b["drop_leaf"])
        bad = dict(self.cuts[d])
        bad[root] = [self.cuts[d][root][0], (short_leaves, t)]
        self.assertNotEqual(cuts.check_cuts(self.g[d], bad), [], "missing leaf not caught")


class Redundancy(unittest.TestCase):
    def test_selftest_passes(self):
        self.assertTrue(redundancy.selftest())

    def test_known_examples(self):
        hd = redundancy.index()
        cls = lambda e: hd.classify(truth_table(e, list("ABCD")))[0]   # noqa: E731
        self.assertEqual(cls("!((A & B) | C)"), redundancy.EXISTS)                 # a21oi
        self.assertEqual(cls("!(A & (B | (C & D)))"), redundancy.CONTAINED)        # a32oi, tied
        self.assertEqual(cls("!((C & D) | (A & B & (C | D)))"), redundancy.NEW)   # Appendix A

    def test_broken_missing_cells_fails_table4(self):
        b = broken("hd_missing_cells.json")
        reduced = redundancy.HDIndex(redundancy.DEFAULT_LIB, exclude_families=tuple(b["remove_families"]))
        counts = redundancy.table4_counts(reduced)
        self.assertNotEqual(counts[b["expect_row"]], b["expect_not"],
                            "Table 4 comparison did not notice missing cells")


if __name__ == "__main__":
    unittest.main(verbosity=2)
