"""make test: the equivalence check of every mapping (Option 2 handout, section 4 step 9).

A mapped netlist must pass, and the same netlist with one cell swapped must be
rejected (handout 9.1: "a netlist cec must reject"), on both paths of
src/check_mapping_equivalence.py: cec (mul, no flip-flops) and dsec (cpu8, with flip-flops).
Needs results/netlists (make mapping), Yosys and yosys-abc.
"""
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import check_mapping_equivalence                              # noqa: E402

NETLISTS = os.path.join(ROOT, "results", "netlists")
# Broken case: the first nand2_1 of the netlist becomes a nor2_1 (same pins A, B, Y).
BROKEN_SWAP = ("sky130_fd_sc_hd__nand2_1 ", "sky130_fd_sc_hd__nor2_1 ")
CASES = {"cec": ("mul", "mul_est_B", "est"), "dsec": ("cpu8", "cpu8_baseline_A", "baseline")}


@unittest.skipUnless(shutil.which(check_mapping_equivalence.YOSYS) and shutil.which(check_mapping_equivalence.ABC)
                     and os.path.exists(os.path.join(NETLISTS, "mul_est_B.v")),
                     "needs Yosys, yosys-abc and results/netlists (make mapping)")
class Equivalence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def run_case(self, method, broken):
        design, tag, library = CASES[method]
        net = os.path.join(NETLISTS, tag + ".v")
        if broken:
            with open(net) as f:
                text = f.read()
            net = os.path.join(self.tmp.name, tag + "_broken.v")
            with open(net, "w") as f:
                f.write(text.replace(*BROKEN_SWAP, 1))
        used, ok, out = check_mapping_equivalence.check(design, net, library, "test_" + tag + ("_broken" if broken else ""))
        self.assertEqual(used, method)
        return ok, out

    def test_cec_passes_a_mapped_netlist(self):
        ok, out = self.run_case("cec", broken=False)
        self.assertTrue(ok, out[-500:])

    def test_broken_cec_rejects_a_swapped_cell(self):
        ok, _ = self.run_case("cec", broken=True)
        self.assertFalse(ok, "cec must reject a netlist with one nand2 swapped for a nor2")

    def test_dsec_passes_a_mapped_netlist(self):
        ok, out = self.run_case("dsec", broken=False)
        self.assertTrue(ok, out[-500:])

    def test_broken_dsec_rejects_a_swapped_cell(self):
        ok, _ = self.run_case("dsec", broken=True)
        self.assertFalse(ok, "dsec must reject a netlist with one nand2 swapped for a nor2")


if __name__ == "__main__":
    unittest.main()
