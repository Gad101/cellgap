"""Person A's part of checkpoint 2: find, check, cost and rank candidate cells.

    python3 src/candidates.py [--group g5] [--top 30] [--designs cpu8,dsp8]

For every design (build/aig/<design>.aag from `make aigs`):
  1. enumerate the cuts (cuts.py) and keep the real ones: a cut whose function
     uses every leaf and has at least 2 leaves;
  2. group them into P classes (input order only) and classify each class
     against HD (redundancy.py): Exists / Exists with an inverter / Contained / New;
  3. for the New classes, measure each occurrence: the "exclusive cone" is the
     set of AND nodes that would disappear if the occurrence became one cell,
     i.e. the nodes of the cone that nothing outside the cone uses;
  4. cost each New class (costmodel.py) and estimate its area from the model
     fitted to HD;
  5. pick, per design, occurrences whose cones do not overlap (a cell can only
     replace logic once) and whose saving is positive, then rank the classes.

Step 5 keeps a class that HD "almost" has only if it is cheaper (Table 3): Exists
with an inverter -> estimated area < the HD cell + inv_1; Contained -> estimated
area < the HD cell.

Estimated saving of one occurrence = m x a_and - area(new cell). a_and is the area
the baseline mapping spends per AND node of that design (Table 1 logs). m is the
number of AND nodes in the exclusive cone, but at most S, the smallest cone seen
for that function anywhere in the designs: the Yosys AIG is not optimized, and
ABC would not pay for redundant structure. It is a GUESS (handout step 7): ABC
does not map AND node by AND node. The real answer comes from re-mapping (step 9).

Writes in results/: candidates.json, redundancy_report.csv, candidate_stats.csv.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aiger                                        # noqa: E402
import costmodel                                    # noqa: E402
import cuts as cutlib                               # noqa: E402
import liberty                                      # noqa: E402
import redundancy                                   # noqa: E402
from designs import ANALYSED, GIVEN, ROOT           # noqa: E402
from tt import NAMES, canon, support, to_hex        # noqa: E402

RESULTS = os.path.join(ROOT, "results")


# ---- measuring one occurrence -------------------------------------------------

def fanout_counts(g: aiger.AIG) -> dict[int, int]:
    """How many times each node is used: by AND gates, outputs and latch inputs."""
    fo: dict[int, int] = defaultdict(int)
    for l0, l1 in g.ands.values():
        fo[l0 >> 1] += 1
        fo[l1 >> 1] += 1
    for lit in g.outputs:
        fo[lit >> 1] += 1
    for _, nxt in g.latches:
        fo[nxt >> 1] += 1
    return fo


def cone(g: aiger.AIG, root: int, leaves: tuple[int, ...]) -> set[int]:
    """AND nodes between the leaves and the root (root included)."""
    stop, seen, stack = set(leaves), set(), [root]
    while stack:
        v = stack.pop()
        if v in seen or v in stop or v not in g.ands:
            continue
        seen.add(v)
        stack.extend(lit >> 1 for lit in g.ands[v])
    return seen


def exclusive_cone(g: aiger.AIG, root: int, leaves: tuple[int, ...], fo: dict, pos: dict) -> frozenset:
    """Nodes of the cone that disappear when the cone becomes one cell.

    The root always stays (it is the cell's output). Any other cone node goes
    only if every use of it is inside the part that goes: we walk the cone from
    the root down and compare the number of uses inside with its total fanout.
    """
    nodes = cone(g, root, leaves)
    gone = {root}
    refs: Counter = Counter()
    for lit in g.ands[root]:
        refs[lit >> 1] += 1
    for v in sorted(nodes - {root}, key=lambda x: -pos[x]):
        if refs[v] == fo[v]:
            gone.add(v)
            for lit in g.ands[v]:
                refs[lit >> 1] += 1
    return frozenset(gone)


def pick_disjoint(occ: list[tuple[int, frozenset, int]], gain_of) -> list[tuple[int, frozenset]]:
    """Greedy: biggest cones first, skip overlaps and occurrences that lose area."""
    used: set[int] = set()
    chosen = []
    for root, gone, _ in sorted(occ, key=lambda o: (-len(o[1]), o[0])):
        if gain_of(len(gone)) <= 0:
            break
        if used.isdisjoint(gone):
            chosen.append((root, gone))
            used |= gone
    return chosen


# ---- baseline area per AND node ----------------------------------------------

def baseline_area_per_and(design: str, n_ands: int) -> tuple[float | None, str]:
    """Combinational area of the baseline mapping / AND nodes, best of scripts A and B.

    Read from the Table 1 logs (results/logs/table1/<design>_<script>_reduced.log), or for
    SPM and mul the baseline mapping logs (results/logs/mapping/<design>_baseline_<script>.log),
    so it comes from a file the flow wrote. Returns (None, reason) when there is no log:
    we never invent an area (AGENTS.md rule 3).
    """
    lib = os.path.join(GIVEN, "hd_reduced.lib")
    best = None
    if os.path.exists(lib):
        area = {c["name"]: (c["area"], c["sequential"]) for c in liberty.cells(lib)}
        for script in "AB":
            log = os.path.join(RESULTS, "logs", "table1", "%s_%s_reduced.log" % (design, script))
            if not os.path.exists(log):   # designs without a Table 1 row: make baseline-mapping-spm-mul
                log = os.path.join(RESULTS, "logs", "mapping", "%s_baseline_%s.log" % (design, script))
            if not os.path.exists(log):
                continue
            comb = comb_area(log, area)
            best = comb if best is None else min(best, comb)
    if best is None:
        return None, "no Table 1 log"
    return best / n_ands, "table1 logs"


def comb_area(log: str, area: dict) -> float:
    """Area of the combinational HD cells in the last stat of a mapping log (flip-flops left out)."""
    text = open(log).read()
    block = text[text.rindex("Number of cells"):]
    comb = 0.0
    for name, n in re.findall(r"^\s+(sky130_fd_sc_hd__\S+)\s+(\d+)\s*$", block, re.M):
        a, seq = area[name]
        if not seq:
            comb += a * int(n)
    return comb


# ---- one design ----------------------------------------------------------------

def collect(design: str, hd: redundancy.HDIndex, cache: dict, aig_dir: str) -> dict:
    """Cuts of one design, classified; occurrences of classes HD lacks, with their cones."""
    g = aiger.read(os.path.join(aig_dir, design + ".aag"))
    allcuts = cutlib.enumerate_cuts(g)
    fo, pos = fanout_counts(g), {v: i for i, v in enumerate(g.topo_ands())}
    counts: Counter = Counter()
    new_occ: dict[int, list] = defaultdict(list)
    n_real = 0
    for root in g.ands:
        for leaves, t in allcuts[root][1:]:
            if len(leaves) < 2 or len(support(t)) != len(leaves):
                continue
            n_real += 1
            c = canon(t, "P")
            counts[c] += 1
            if c not in cache:
                cache[c] = hd.classify(c)
            if cache[c][0] != redundancy.EXISTS:
                new_occ[c].append((root, exclusive_cone(g, root, leaves, fo, pos), len(cone(g, root, leaves))))
    return {"g": g, "real_cuts": n_real, "counts": counts, "new_occ": new_occ}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--group", default="gb2", help="group tag used in cell names: dd2_<group>__...")
    ap.add_argument("--top", type=int, default=30, help="candidates written to candidates.json")
    ap.add_argument("--designs", default=",".join(ANALYSED))
    ap.add_argument("--aig-dir", default=os.path.join(ROOT, "build", "aig"))
    ap.add_argument("--out", default=RESULTS, help="folder for the result files")
    ap.add_argument("--a-and", type=float, default=None,
                    help="um2 per AND node, only for designs without a Table 1 log (your choice, recorded in the output)")
    a = ap.parse_args(argv)
    designs = a.designs.split(",")
    out_dir = a.out
    os.makedirs(out_dir, exist_ok=True)

    hd = redundancy.index()
    pts, _ = costmodel.hd_fit_points()
    model, _ = costmodel.fit(pts)
    cache: dict = {}
    per: dict[str, dict] = {}
    a_and: dict[str, float] = {}
    stats_rows = []
    for d in designs:
        t0 = time.time()
        per[d] = collect(d, hd, cache, a.aig_dir)
        g = per[d]["g"]
        a_and[d], src = baseline_area_per_and(d, g.A)
        if a_and[d] is None:
            if a.a_and is None:
                sys.exit("no Table 1 log for %s: run `make table1` first, or pass --a-and <um2 per AND node>" % d)
            a_and[d], src = a.a_and, "--a-and %.3f given on the command line" % a.a_and
        by = Counter(cache[c][0] for c in per[d]["counts"])
        new_cuts = sum(n for c, n in per[d]["counts"].items() if cache[c][0] == redundancy.NEW)
        stats_rows.append({"design": d, "ands": g.A, "real_cuts": per[d]["real_cuts"],
                           "p_classes": len(per[d]["counts"]),
                           **{k.replace(" ", "_"): by.get(k, 0) for k in redundancy.ORDER},
                           "cuts_in_new_classes": new_cuts, "area_per_and_um2": round(a_and[d], 3),
                           "area_per_and_source": src, "seconds": round(time.time() - t0, 1)})
        print("%-10s %5d ANDs %7d real cuts %5d classes (%d New)  a_and=%.2f  %.1fs"
              % (d, g.A, per[d]["real_cuts"], len(per[d]["counts"]), by.get(redundancy.NEW, 0), a_and[d], time.time() - t0), flush=True)

    # every class seen in any design, with its Table 3 class: the redundancy report
    seen = Counter()
    for d in designs:
        seen.update(per[d]["counts"])
    with open(os.path.join(out_dir, "candidate_stats.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(stats_rows[0]))
        w.writeheader()
        w.writerows(stats_rows)

    # step 5: which classes become candidates (Table 3, "what to do")
    hd_area = {c["name"]: c["area"] for c in hd.cells}
    inv_area = hd_area["sky130_fd_sc_hd__inv_1"]
    cand, verdict = [], {}
    for c in seen:
        cls, cells = cache[c]
        low, n = costmodel.compact(c)
        cost = costmodel.best(low)
        assert costmodel.verify(low, cost), "cost formula does not compute the class %s" % to_hex(c)
        area = model.area(cost)
        if cls == redundancy.NEW:
            keep, thr = True, None
        elif cls == redundancy.EXISTS:
            keep, thr = False, None
        else:
            thr = min(hd_area[x.split(" ")[0]] for x in cells) + (inv_area if cls == redundancy.EXISTS_INV else 0.0)
            keep = area < thr
        verdict[c] = (keep, thr, area)
        if keep:
            cand.append((c, low, n, cost, area))
    for cls in redundancy.ORDER:
        mine = [c for c in seen if cache[c][0] == cls]
        print("%-24s %4d classes seen, %4d kept as candidates" % (cls, len(mine), sum(verdict[c][0] for c in mine)))

    from tt import sop
    with open(os.path.join(out_dir, "redundancy_report.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["class_table", "inputs", "table3_class", "matching_hd_cells", "function", "kept", "est_area_um2",
                    "hd_threshold_um2"] + ["cuts_" + d for d in designs])
        for c, _ in seen.most_common():
            cls, cells = cache[c]
            keep, thr, area = verdict[c]
            w.writerow([to_hex(c), len(support(c)), cls, "; ".join(redundancy.short(x) for x in cells[:3]), sop(c)[:80],
                        "yes" if keep else "no", area, "" if thr is None else round(thr, 4)]
                       + [per[d]["counts"].get(c, 0) for d in designs])

    # step 7: estimate and rank
    ranked = []
    for c, low, n, cost, area in cand:
        S = min((sz for d in designs for _, _, sz in per[d]["new_occ"].get(c, [])), default=1)
        per_design, total, replaced = {}, 0.0, 0
        for d in designs:
            occ = per[d]["new_occ"].get(c, [])
            chosen = pick_disjoint(occ, lambda m: min(m, S) * a_and[d] - area)
            gain = sum(min(len(gone), S) * a_and[d] - area for _, gone in chosen)
            per_design[d] = {"cuts": per[d]["counts"].get(c, 0), "used": len(chosen),
                             "and_nodes_replaced": sum(min(len(gone), S) for _, gone in chosen), "saving_um2": round(gain, 2)}
            total += gain
            replaced += per_design[d]["and_nodes_replaced"]
        ranked.append({"class": c, "low": low, "n": n, "cost": cost, "area": area, "saving": total, "S": S,
                       "cuts": sum(per_design[d]["cuts"] for d in designs), "replaced": replaced, "per_design": per_design})
    ranked.sort(key=lambda r: (-r["saving"], -r["cuts"], r["class"]))
    ranked = [r for r in ranked if r["saving"] > 0]   # only cells estimated to save area

    out = []
    for i, r in enumerate(ranked[:a.top], 1):
        out.append({
            "request_id": "C-%03d" % i,
            "name": "dd2_%s__f%s_1" % (a.group, to_hex(r["low"], r["n"])[2:].lower()),
            "inputs": list(NAMES[:r["n"]]), "output": "Y",
            "expression": r["cost"].expr,
            "truth_table": to_hex(r["low"], r["n"]),
            "sizing": "hd",
            "estimated_area_um2": r["area"],
            "rank": i, "class_table": to_hex(r["class"]),
            "cost": {"transistors": r["cost"].transistors, "stages": r["cost"].stages, "inverters": r["cost"].inverters},
            "estimated_saving_um2": round(r["saving"], 2),
            "cuts_in_designs": r["cuts"], "and_nodes_replaced": r["replaced"],
            "per_design": r["per_design"]})
    with open(os.path.join(out_dir, "candidates.json"), "w") as f:
        json.dump({"group": a.group, "designs": designs, "area_per_and_um2": {d: round(v, 3) for d, v in a_and.items()},
                   "area_per_and_source": {r["design"]: r["area_per_and_source"] for r in stats_rows},
                   "candidates": out}, f, indent=1)

    print("\nCandidate classes: %d. Ranked by estimated saving (um2); top %d:" % (len(ranked), min(a.top, 15)))
    print("%-4s %-8s %2s %3s %2s %5s %6s %7s %9s  %s" % ("rank", "class", "in", "T", "st", "area", "cuts", "used", "saving", "expression"))
    for r in out[:15]:
        used = sum(v["used"] for v in r["per_design"].values())
        print("%-4d %-8s %2d %3d %2d %5.1f %6d %7d %9.1f  %s" % (
            r["rank"], r["class_table"], len(r["inputs"]), r["cost"]["transistors"], r["cost"]["stages"],
            r["estimated_area_um2"], r["cuts_in_designs"], used, r["estimated_saving_um2"], r["expression"][:48]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
