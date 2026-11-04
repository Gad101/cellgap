"""make test: the Liberty writer (Option 2 handout, sections 4 step 8 and 6).

- timing_sense_calc agrees with the timing_sense HD itself gives every input of
  every single-output combinational cell in hd_reduced.lib (HD writes a non-unate
  input as two arcs, one positive_unate and one negative_unate);
- the written library loads in Yosys with 189 + N cell types and every new
  cell's function matches its request;
- broken cases, one per check (overview 4.3 rule 3):
    Yosys must reject a library with an unclosed quote (handout 9.1);
    the 189 + N count must fail on a library with a missing brace (Yosys
    0.33 reads it without error but imports only part of it);
    the function check must fail on a cell whose function uses a pin it lacks.
Needs build/given (make setup), results/cell_requests (make cell-requests) and Yosys.
"""
import glob
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import liberty                                  # noqa: E402
import write_liberty_with_new_cells                            # noqa: E402
from boolexpr import truth_table                # noqa: E402
from timing_sense_calc import timing_sense      # noqa: E402
from write_liberty_with_new_cells import load_json, read       # noqa: E402

REQUESTS = os.path.join(ROOT, "results", "cell_requests")

# Broken cases: (text to find after "/* new cells", replacement), applied once.
BROKEN_QUOTE = ('related_pin : "A";', 'related_pin : "A;')
BROKEN_BRACE = ("    }\n  }\n", "    }\n")
BROKEN_FUNCTION = ('function : "', 'function : "E & ')


def hd_senses():
    """{cell: {input: timing_sense}} as HD's own Liberty states it."""
    lib = liberty.parse(read(write_liberty_with_new_cells.BASE))
    lib = lib if lib.kind == "library" else next(c for c in lib.children if c.kind == "library")
    out = {}
    for cell in (c for c in lib.children if c.kind == "cell"):
        per_pin = {}
        for pin in (p for p in cell.children if p.kind == "pin"):
            for t in (x for x in pin.children if x.kind == "timing"):
                rp = t.attrs.get("related_pin", "").strip('"')
                per_pin.setdefault(rp, set()).add(t.attrs.get("timing_sense", "").strip('"'))
        out[cell.args.strip('"')] = {p: ("non_unate" if s >= {"positive_unate", "negative_unate"} else s.pop())
                                     for p, s in per_pin.items()}
    return out


class TimingSense(unittest.TestCase):
    def test_known_cells(self):
        self.assertEqual(timing_sense(0x7, 2, 0), "negative_unate")    # nand2
        self.assertEqual(timing_sense(0x8, 2, 0), "positive_unate")    # and2
        self.assertEqual(timing_sense(0x6, 2, 0), "non_unate")         # xor2

    def test_agrees_with_every_hd_cell(self):
        senses = hd_senses()
        checked = 0
        for c in liberty.single_output_combinational(liberty.cells(write_liberty_with_new_cells.BASE)):
            ins, n = c["inputs"], len(c["inputs"])
            if not 1 <= n <= 4:
                continue
            t = truth_table(c["outputs"][0]["function"], ins) & ((1 << (1 << n)) - 1)
            for k, p in enumerate(ins):
                self.assertEqual(timing_sense(t, n, k), senses[c["name"]][p], "%s pin %s" % (c["name"], p))
                checked += 1
        self.assertGreater(checked, 300)


@unittest.skipUnless(shutil.which(write_liberty_with_new_cells.YOSYS) and glob.glob(os.path.join(REQUESTS, "*.json")),
                     "needs Yosys and results/cell_requests (make cell-requests)")
class WrittenLibrary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.reqs = sorted((load_json(p) for p in glob.glob(os.path.join(REQUESTS, "*.json"))),
                           key=lambda r: r["request_id"])
        self.lib = os.path.join(self.tmp.name, "ext.lib")
        write_liberty_with_new_cells.write(self.reqs, write_liberty_with_new_cells.BASE, self.lib)

    def tearDown(self):
        self.tmp.cleanup()

    def test_loads_with_189_plus_new_cells(self):
        self.assertEqual(write_liberty_with_new_cells.yosys_cell_count(self.lib), 189 + len(self.reqs))

    def test_functions_match_requests(self):
        self.assertEqual(write_liberty_with_new_cells.check_functions(self.reqs, self.lib), [])

    def broken(self, find_replace):
        text = read(self.lib)
        j = text.index(find_replace[0], text.index("/* new cells"))
        path = os.path.join(self.tmp.name, "broken.lib")
        with open(path, "w") as f:
            f.write(text[:j] + find_replace[1] + text[j + len(find_replace[0]):])
        return path

    def test_broken_unclosed_quote_is_rejected_by_yosys(self):
        with self.assertRaises(RuntimeError):
            write_liberty_with_new_cells.yosys_cell_count(self.broken(BROKEN_QUOTE))

    def test_broken_missing_brace_fails_the_count(self):
        self.assertNotEqual(write_liberty_with_new_cells.yosys_cell_count(self.broken(BROKEN_BRACE)), 189 + len(self.reqs))

    def test_broken_function_fails_the_function_check(self):
        self.assertNotEqual(write_liberty_with_new_cells.check_functions(self.reqs, self.broken(BROKEN_FUNCTION)), [])

if __name__ == "__main__":
    unittest.main()
