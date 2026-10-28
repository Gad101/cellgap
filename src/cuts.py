"""Step 2: enumerate the cuts of up to 4 inputs of an AIG, with a truth table each.

A cut of node n is a set of nodes ("leaves", at most K = 4) such that every
path from an input to n passes through a leaf. The logic between the leaves
and n is a small function of <= 4 inputs: a candidate cell.

How the cuts are built (references 10 and 11 of the handout), in topological
order, for an AND node n = a AND b (each fanin possibly inverted):
    cuts(n) = { {n} }  U  { u U v : u in cuts(a), v in cuts(b), |u U v| <= K }
Inputs and latch outputs only have their trivial cut {itself}. The truth table
of u U v is the AND of the two fanin tables, each first re-expressed over the
merged leaf list ("stretched") and inverted if the wire is inverted. A cut
whose leaves include all the leaves of a smaller cut of the same node is
dominated and dropped.

The check (`check_cuts`) recomputes every truth table a different way: it walks
the AIG from the cut's root down to its leaves and evaluates it once per input
combination, with 0/1 values. It also checks that the leaves really cut the
node off from the inputs.

    python3 src/cuts.py <design.aag|.aig> [--max-cuts N] [--check] [--out results/cuts/x.json]
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aiger                                     # noqa: E402
from tt import MASK, VARS, canon, to_hex         # noqa: E402

K = 4


def _stretch_table(positions: tuple[int, ...]) -> list[int]:
    """Row map that moves old input i to new position positions[i]."""
    rows = []
    for m in range(16):                      # new row
        old = 0
        for i, p in enumerate(positions):
            old |= ((m >> p) & 1) << i
        rows.append(old)
    return rows


_ROWMAPS: dict[tuple[int, ...], list[int]] = {}


def stretch(tt: int, old: tuple[int, ...], new: tuple[int, ...]) -> int:
    """Re-express a table over leaves `old` as a table over leaves `new` (old is a subset)."""
    if old == new:
        return tt
    pos = tuple(new.index(x) for x in old)
    rows = _ROWMAPS.get(pos)
    if rows is None:
        rows = _ROWMAPS[pos] = _stretch_table(pos)
    g = 0
    for m in range(16):
        g |= ((tt >> rows[m]) & 1) << m
    return g


def enumerate_cuts(g: aiger.AIG, max_cuts: int | None = None) -> dict[int, list[tuple[tuple[int, ...], int]]]:
    """cuts[v] = list of (leaves, truth table); the first entry is the trivial cut (v,)."""
    cuts: dict[int, list] = {}
    for v in g.leaves:
        cuts[v] = [((), 0)] if v == 0 else [((v,), VARS[0])]
    for n in g.topo_ands():
        l0, l1 = g.ands[n]
        c0, c1 = cuts[l0 >> 1], cuts[l1 >> 1]
        inv0, inv1 = MASK if l0 & 1 else 0, MASK if l1 & 1 else 0
        found: dict[tuple[int, ...], int] = {}
        for (u, tu), (w, tw) in itertools.product(c0, c1):
            leaves = tuple(sorted(set(u) | set(w)))
            if len(leaves) > K or leaves in found:
                continue
            t = (stretch(tu, u, leaves) ^ inv0) & (stretch(tw, w, leaves) ^ inv1)
            found[leaves] = t
        # drop dominated cuts (a superset of another cut's leaves)
        keys = sorted(found, key=len)
        kept = []
        for k in keys:
            ks = set(k)
            if not any(set(j) <= ks for j in kept):
                kept.append(k)
        if max_cuts is not None:
            kept = kept[:max_cuts]           # priority: fewest leaves first
        cuts[n] = [((n,), VARS[0])] + [(k, found[k]) for k in kept]
    return cuts


def simulate_cut(g: aiger.AIG, root: int, leaves: tuple[int, ...]) -> int:
    """Truth table of `root` over `leaves`, by evaluating the AIG per input combination."""
    leaf_pos = {v: i for i, v in enumerate(leaves)}
    allowed_stops = set(leaves)
    tt = 0
    for m in range(16):
        memo: dict[int, int] = {}

        def val(v):
            if v in memo:
                return memo[v]
            if v in allowed_stops:
                r = (m >> leaf_pos[v]) & 1
            elif v == 0:
                r = 0
            elif v in g.ands:
                a, b = g.ands[v]
                r = (val(a >> 1) ^ (a & 1)) & (val(b >> 1) ^ (b & 1))
            else:
                raise ValueError("leaves %s do not cut node %d: reached input/latch %d" % (leaves, root, v))
            memo[v] = r
            return r
        tt |= val(root) << m
    return tt


def check_cuts(g: aiger.AIG, cuts: dict, limit: int | None = None) -> list[str]:
    """Return a list of errors (empty = pass). `limit` checks only the first N cuts."""
    sys.setrecursionlimit(max(10000, 4 * len(g.ands)))
    errors, n = [], 0
    for root in g.topo_ands():
        for leaves, tt in cuts[root][1:]:
            if limit is not None and n >= limit:
                return errors
            n += 1
            try:
                ref = simulate_cut(g, root, leaves)
            except ValueError as e:
                errors.append(str(e))
                continue
            if ref != tt:
                errors.append("node %d leaves %s: table %s, simulation gives %s"
                              % (root, leaves, to_hex(tt), to_hex(ref)))
    return errors


def summarize(g: aiger.AIG, cuts: dict) -> dict:
    """Counts for the report: AIG size, cuts, distinct functions and classes."""
    n_cuts = sum(len(c) - 1 for v, c in cuts.items() if v in g.ands)
    by_size = Counter(len(k) for v, c in cuts.items() if v in g.ands for k, _ in c[1:])
    po = Counter()
    for v, c in cuts.items():
        if v in g.ands:
            for k, t in c[1:]:
                po[canon(t, "PO")] += 1
    return {
        "inputs": g.I, "latches": g.L, "outputs": g.O, "ands": g.A,
        "cuts": n_cuts, "cuts_by_leaves": dict(sorted(by_size.items())),
        "po_classes": len(po),
        "top_po_classes": [[to_hex(t), n] for t, n in po.most_common(20)],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("aig")
    ap.add_argument("--max-cuts", type=int, default=None, help="keep at most N cuts per node")
    ap.add_argument("--check", action="store_true", help="re-simulate every cut")
    ap.add_argument("--check-limit", type=int, default=None)
    ap.add_argument("--out", help="write a JSON summary here")
    a = ap.parse_args(argv)
    t0 = time.time()
    g = aiger.read(a.aig)
    cuts = enumerate_cuts(g, a.max_cuts)
    s = summarize(g, cuts)
    s["design"] = os.path.basename(a.aig)
    s["max_cuts"] = a.max_cuts
    s["seconds"] = round(time.time() - t0, 2)
    print("%s: %d ANDs, %d cuts, %d PO classes (%.1fs)" % (s["design"], g.A, s["cuts"], s["po_classes"], s["seconds"]))
    ok = True
    if a.check:
        errs = check_cuts(g, cuts, a.check_limit)
        s["check"] = "pass" if not errs else "fail"
        s["check_errors"] = errs[:20]
        print("cut check: %s (%d errors)" % (s["check"].upper(), len(errs)))
        for e in errs[:5]:
            print("  " + e)
        ok = not errs
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(a.out, "w") as f:
            json.dump(s, f, indent=1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
