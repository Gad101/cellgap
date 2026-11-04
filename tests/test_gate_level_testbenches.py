"""make test (on the host): Tutorial 4's gate-level testbenches on a mapped netlist.

The multiplier netlist with new cells must pass mul_exhaustive_tb, and the same
netlist with one cell swapped must fail it (overview 4.3 rule 3).
Needs Icarus Verilog 13 (not in the student pack's image: the test skips there),
build/pdk/verilog and build/tut2 (make setup), results/netlists (make mapping)
and libs/new_cell_verilog_sims.v (make new-cell-verilog-sims).
"""
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import run_gate_level_testbenches as gls       # noqa: E402

NETLIST = os.path.join(ROOT, "results", "netlists", "mul_est_B.v")
# Broken case: the first nand2_1 of the netlist becomes a nor2_1 (same pins A, B, Y).
BROKEN_SWAP = ("sky130_fd_sc_hd__nand2_1 ", "sky130_fd_sc_hd__nor2_1 ")


@unittest.skipUnless(shutil.which(gls.IVERILOG) and os.path.exists(NETLIST) and os.path.exists(gls.NEW_CELLS),
                     "needs Icarus Verilog (host), results/netlists and libs/new_cell_verilog_sims.v")
class GateLevel(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.top, self.tb, self.flags = gls.TESTBENCHES["mul"][1]          # mul_exhaustive_tb

    def tearDown(self):
        self.tmp.cleanup()

    def test_mapped_netlist_passes(self):
        ok, out = gls.simulate(NETLIST, self.top, self.tb, self.flags, "test_mul_est_B")
        self.assertTrue(ok, out[-500:])

    def test_broken_swapped_cell_fails(self):
        with open(NETLIST) as f:
            text = f.read()
        broken = os.path.join(self.tmp.name, "mul_est_B_broken.v")
        with open(broken, "w") as f:
            f.write(text.replace(*BROKEN_SWAP, 1))
        ok, out = gls.simulate(broken, self.top, self.tb, self.flags, "test_mul_est_B_broken")
        self.assertFalse(ok, "the testbench must fail on a netlist with one nand2 swapped for a nor2")
        self.assertIn("MISMATCH", out)


if __name__ == "__main__":
    unittest.main()
