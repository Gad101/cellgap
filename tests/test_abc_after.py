"""make test: the AIG after ABC restructuring (handout section 4, step 1).

The restructured graph must be equivalent to the one it came from, and the
equivalence check must reject a wrong graph (the broken case, overview 4.3).
Needs yosys-abc, which the student pack's Docker image has.
"""
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ABC = os.environ.get("ABC", "yosys-abc")
CSA8 = os.path.join(ROOT, "tests", "aig", "csa8.aag")

# Broken case: AND number 40 of csa8 gets its first input inverted.
BROKEN_AND, BROKEN_DESIGN = 40, "csa8"


def run(script, *args):
    return subprocess.run([os.path.join(ROOT, "src", script), *args], capture_output=True, text=True)


def write_binary(aag: str, out: str, flip_and: int = -1) -> None:
    """Re-encode an ASCII AIGER as binary (ABC reads no .aag); optionally invert
    the first input of one AND. Needs the canonical numbering Yosys writes."""
    lines = open(aag).read().split("\n")
    M, I, L, O, A = map(int, lines[0].split()[1:])
    latches = lines[1 + I:1 + I + L]
    outputs = lines[1 + I + L:1 + I + L + O]
    ands = [list(map(int, x.split())) for x in lines[1 + I + L + O:1 + I + L + O + A]]
    if flip_and >= 0:
        lhs, r0, r1 = ands[flip_and]
        r0 ^= 1
        ands[flip_and] = [lhs] + sorted((r0, r1), reverse=True)
    body = bytearray()
    for lhs, r0, r1 in ands:
        for d in (lhs - r0, r0 - r1):       # deltas, 7 bits per byte (AIGER spec)
            while d >= 0x80:
                body.append(d & 0x7F | 0x80)
                d >>= 7
            body.append(d)
    with open(out, "wb") as f:
        f.write(("aig %d %d %d %d %d\n" % (M, I, L, O, A)).encode())
        for x in latches:                   # binary latches omit their own literal
            f.write((" ".join(x.split()[1:]) + "\n").encode())
        f.write(("\n".join(outputs) + "\n").encode())
        f.write(bytes(body))


@unittest.skipUnless(shutil.which(ABC), "needs %s (run in the student pack's Docker image)" % ABC)
class AbcAfter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.before = os.path.join(self.tmp.name, "csa8.aig")
        write_binary(CSA8, self.before)

    def tearDown(self):
        self.tmp.cleanup()

    def test_reencoded_graph_is_equivalent_to_itself(self):
        r = run("aig_equiv.sh", self.before, self.before)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_restructured_graph_is_equivalent(self):
        after = os.path.join(self.tmp.name, "csa8_abc.aig")
        r = run("abc_after.sh", self.before, after)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.getsize(after) > 0)

    def test_broken_wrong_graph_is_rejected(self):
        wrong = os.path.join(self.tmp.name, "csa8_wrong.aig")
        write_binary(CSA8, wrong, flip_and=BROKEN_AND)
        r = run("aig_equiv.sh", self.before, wrong)
        self.assertNotEqual(r.returncode, 0, "cec must reject a graph with one AND input inverted")


if __name__ == "__main__":
    unittest.main()
