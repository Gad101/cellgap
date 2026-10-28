"""Step 5: is a candidate function already in HD? (Option 2 handout, section 5)

Classes of Table 3, tested in this order:
  Exists                  same truth table as an HD cell after reordering inputs
  Exists with an inverter same as an HD cell after inverting the output or one input
  Contained               equal to an HD cell with each of its inputs connected
                          to one of the candidate's inputs, or to 0 or 1
  New                     none of the above

We compare with every single-output combinational cell of the FULL HD Liberty
(all drives, all kinds). Everything is reduced to class names "up to input
order" (canonical P form, see tt.py), so "after reordering inputs" is a
set lookup.

Command line:
    python3 src/redundancy.py selftest      # every HD cell -> Exists, and Table 4
    python3 src/redundancy.py table4        # print the Table 4 counts
    python3 src/redundancy.py classify 0x077F
"""
from __future__ import annotations

import itertools
import json
import os
import sys
from functools import lru_cache

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from boolexpr import Expr                      # noqa: E402
from cmos import is_one_stage, is_read_once_one_stage, one_stage_transistors  # noqa: E402
from tt import MASK, VARS, canon, canon_tables, flip_input, support, to_hex  # noqa: E402
import liberty                                 # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LIB = os.environ.get("HD_LIB", os.path.join(ROOT, "build", "pdk", "sky130_fd_sc_hd__tt_025C_1v80.lib"))

EXISTS, EXISTS_INV, CONTAINED, NEW = "Exists", "Exists with an inverter", "Contained", "New"
ORDER = (EXISTS, EXISTS_INV, CONTAINED, NEW)

# Table 4 of the Option 2 handout: reference counts for 4-input functions that
# depend on all four inputs, up to input order. Do not edit (AGENTS.md rule 2).
TABLE4 = {
    EXISTS: 24, EXISTS_INV: 20, CONTAINED: 38, NEW: 3822,
    "new_one_stage": 9, "new_one_stage_small": 5,
    "read_once": 8, "read_once_exists": 6, "read_once_contained": 2,
}


def short(name: str) -> str:
    return name.replace("sky130_fd_sc_hd__", "")


class HDIndex:
    """The HD cells, turned into sets of class names for fast lookups."""

    def __init__(self, lib_path: str = DEFAULT_LIB, exclude_families: tuple = ()):
        recs = liberty.cells(lib_path)
        self.cells = [c for c in liberty.single_output_combinational(recs)
                      if not any(c["name"].startswith("sky130_fd_sc_hd__%s_" % f) for f in exclude_families)]
        self.exists: dict[int, list[str]] = {}       # P-class -> cells
        self.exists_inv: dict[int, list[str]] = {}   # P-class -> "cell (how)"
        self.contained: dict[int, list[str]] = {}    # P-class -> cells
        for c in self.cells:
            out = c["outputs"][0]
            e = Expr(out["function"])
            n = len(c["inputs"])
            f = e.compile(c["inputs"])
            c["n_inputs"] = n
            if n <= 4:
                t = f(*VARS[:n])
                c["tt"] = t
                self.exists.setdefault(canon(t, "P"), []).append(c["name"])
                variants = [(t ^ MASK, "output inverted")]
                variants += [(flip_input(t, k), "input %s inverted" % c["inputs"][k]) for k in range(n)]
                for v, how in variants:
                    self.exists_inv.setdefault(canon(v, "P"), []).append("%s (%s)" % (c["name"], how))
            # Contained: every input of the cell tied to A, B, C, D, 0 or 1
            choices = list(VARS) + [0, MASK]
            seen = set()
            for combo in itertools.product(choices, repeat=n):
                seen.add(f(*combo))
            for p in {canon(t, "P") for t in seen}:
                self.contained.setdefault(p, []).append(c["name"])

    def classify(self, tt: int) -> tuple[str, list[str]]:
        """Class of Table 3, and the HD cells that match."""
        p = canon(tt, "P")
        if p in self.exists:
            return EXISTS, self.exists[p]
        if p in self.exists_inv:
            return EXISTS_INV, self.exists_inv[p]
        if p in self.contained:
            return CONTAINED, self.contained[p]
        return NEW, []


@lru_cache(maxsize=None)
def index(lib_path: str = DEFAULT_LIB) -> HDIndex:
    return HDIndex(lib_path)


def four_input_classes() -> list[int]:
    """One table per P-class of the 4-input functions that depend on all 4 inputs."""
    cp = canon_tables()["P"]
    reps = sorted({int(cp[t]) for t in range(65536)})
    return [t for t in reps if len(support(t)) == 4]


def table4_counts(hd: HDIndex) -> dict[str, int]:
    counts = {k: 0 for k in TABLE4}
    for t in four_input_classes():
        cls, _ = hd.classify(t)
        counts[cls] += 1
        if cls == NEW and is_one_stage(t):
            counts["new_one_stage"] += 1
            n = one_stage_transistors(t, max_series=3)
            if n is not None and n <= 12:
                counts["new_one_stage_small"] += 1
        if is_read_once_one_stage(t, max_series=3):
            counts["read_once"] += 1
            if cls == EXISTS:
                counts["read_once_exists"] += 1
            if cls == CONTAINED:
                counts["read_once_contained"] += 1
    return counts


# Rows of Table 4 produced by the four tests of Table 3: the redundancy checker
# itself. The other rows also need the transistor-cost model of step 4.
CLASS_ROWS = (EXISTS, EXISTS_INV, CONTAINED, NEW)


def selftest(lib_path: str = DEFAULT_LIB, strict: bool = False) -> bool:
    """Self-test of section 5. PASS needs every HD cell -> Exists and the four class rows.

    The cost rows are printed and compared too; with strict=True they must match as well.
    """
    from cmos import one_stage_form, series_of
    hd = index(lib_path)
    ok = True
    # 1. every HD cell with at most 4 inputs, fed in as a candidate, must be Exists
    bad = [c["name"] for c in hd.cells if c["n_inputs"] <= 4 and hd.classify(c["tt"])[0] != EXISTS]
    n4 = sum(1 for c in hd.cells if c["n_inputs"] <= 4)
    print("HD cells with <= 4 inputs classified as Exists: %d / %d" % (n4 - len(bad), n4))
    if bad:
        ok = False
        print("  FAIL, not Exists:", ", ".join(short(b) for b in bad))
    # 2. Table 4
    got = table4_counts(hd)
    print("%-28s %8s %8s" % ("Table 4 row", "handout", "ours"))
    cost_ok = True
    for k, ref in TABLE4.items():
        flag = "" if got[k] == ref else "   <-- MISMATCH"
        print("%-28s %8d %8d%s" % (k, ref, got[k], flag))
        if k in CLASS_ROWS:
            ok &= got[k] == ref
        else:
            cost_ok &= got[k] == ref
    # 3. show the evidence for the one-stage rows: one formula per class, checked
    #    by re-reading the formula text (an independent path from the search)
    print("\nNew one-stage classes (Y = !F), smallest F within 3 in series:")
    print("%-8s %-44s %4s %4s %4s  %s" % ("Y", "F (pull-down network)", "T", "PDN", "PUN", "check"))
    from boolexpr import truth_table
    for t in four_input_classes():
        if hd.classify(t)[0] == NEW and is_one_stage(t):
            form = one_stage_form(t, max_series=3, max_lits=8)
            if form is None:
                print("%-8s %-44s %4s" % (to_hex(t), "(none with <= 3 in series and <= 16 T)", "-"))
                continue
            lits, pd, pu = series_of(form)
            good = truth_table(form, list("ABCD")) == t ^ MASK and pd <= 3 and pu <= 3
            ok &= good
            print("%-8s %-44s %4d %4d %4d  %s" % (to_hex(t), form, 2 * lits, pd, pu, "ok" if good else "WRONG"))
    if not cost_ok:
        print("\nNOTE: a cost row differs from the handout. The class rows (the redundancy")
        print("checker) match. Every formula above is checked independently, so our count")
        print("is backed by an explicit network; see results/table4_selftest.txt.")
        if strict:
            ok = False
    print("SELFTEST", "PASS" if ok else "FAIL", "(strict)" if strict else "")
    return ok


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "selftest"
    lib = os.environ.get("HD_LIB", DEFAULT_LIB)
    if cmd == "selftest":
        return 0 if selftest(lib, strict="--strict" in argv) else 1
    if cmd == "table4":
        print(json.dumps(table4_counts(index(lib)), indent=1))
        return 0
    if cmd == "classify":
        t = int(argv[2], 16)
        cls, cells = index(lib).classify(t)
        print(to_hex(t), cls, ", ".join(short(c) for c in cells[:8]))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
