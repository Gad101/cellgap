"""make demo: the flow so far on one design (checkpoint 1 version).

    python3 src/demo.py <design.v> <top> [read_verilog flags]
Writes the AIG, enumerates and checks its cuts, then lists the most frequent
functions (up to input order) and what HD already has for each.
"""
from __future__ import annotations

import os
import subprocess
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aiger                                   # noqa: E402
import cuts                                    # noqa: E402
import redundancy                              # noqa: E402
from designs import ROOT                       # noqa: E402
from tt import canon, sop, support, to_hex     # noqa: E402


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    v, top = os.path.realpath(argv[1]), argv[2]   # realpath: see designs.GIVEN
    flags = argv[3] if len(argv) > 3 else ""
    out = os.path.join(ROOT, "build", "demo", top + ".aag")
    subprocess.run([os.path.join(ROOT, "src", "make_aig.sh"), v, top, out, flags], check=True)
    g = aiger.read(out)
    c = cuts.enumerate_cuts(g)
    errs = cuts.check_cuts(g, c)
    s = cuts.summarize(g, c)
    print("\nAIG: %d inputs, %d latches, %d ANDs; %d cuts; cut check %s"
          % (g.I, g.L, g.A, s["cuts"], "PASS" if not errs else "FAIL (%d)" % len(errs)))
    # a cut whose function ignores one of its leaves (even a constant) is not a
    # real 4-input candidate: the same function is a smaller cut too
    real = [t for n in g.ands for k, t in c[n][1:] if len(support(t)) == len(k)]
    print("cuts whose function uses every leaf: %d of %d" % (len(real), s["cuts"]))
    freq = Counter(canon(t, "P") for t in real)
    hd = redundancy.index()
    print("\nMost frequent functions (up to input order):")
    print("%-8s %6s %3s  %-24s %s" % ("table", "count", "in", "HD", "function"))
    for t, n in freq.most_common(15):
        cls, cells = hd.classify(t)
        x1 = [x for x in cells if x.split(" ")[0].endswith("_1")]
        cell = redundancy.short((x1 or cells)[0]) if cells else ""
        print("%-8s %6d %3d  %-24s %s" % (to_hex(t), n, len(support(t)), (cls + " " + cell)[:24], sop(t)[:60]))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
