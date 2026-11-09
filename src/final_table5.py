"""Final Table 5 (handout section 7): the final set, mapped, checked, tabulated.

    python3 src/final_table5.py [--jobs N]
For each library label that exists  -- est: libs/hd_reduced_plus_final_set_est.lib,
real: libs/hd_reduced_plus_final_set_real.lib (src/real_lib.py) -- it maps every analysed design with
scripts A and B, checks every netlist against the RTL with ABC (check_mapping_equivalence.check),
and writes results/final/mapping_areas_final.csv, results/final/mapping_equivalence_final.csv and
results/table5_final_<label>.{md,csv}.
Baseline areas and their equivalence results are read from results/mapping_areas.csv and
results/mapping_equivalence.csv (make mapping-equivalence).
Optional worst delay: results/worst_delay.csv with columns design,library,script,worst_delay_ns
(library = baseline, est or real), from OpenSTA. Without it the column says "n/a".
Exits 1 if any equivalence check fails.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import check_mapping_equivalence as ck                         # noqa: E402
import final_flow as ff                                        # noqa: E402
from designs import ANALYSED, REQUIRED, ROOT                   # noqa: E402

RES = os.path.join(ROOT, "results")
OUT = os.path.join(RES, "final")
LABELS = {"est": os.path.join(ROOT, "libs", "hd_reduced_plus_final_set_est.lib"),
          "real": os.path.join(ROOT, "libs", "hd_reduced_plus_final_set_real.lib")}


def pct(base: float, new: float) -> float:
    return round(100 * (base - new) / base, 2)


def read_csv(path: str) -> list[dict]:
    with open(path) as f:
        return list(csv.DictReader(f))


def delays() -> dict:
    p = os.path.join(RES, "worst_delay.csv")
    return {(r["design"], r["library"], r["script"]): r["worst_delay_ns"] for r in read_csv(p)} if os.path.exists(p) else {}


def build_rows(base_area: dict, base_eq: dict, new_area: dict, new_eq: dict, dl: dict, label: str) -> tuple[list, list, tuple]:
    """Per-(design,script) rows, per-design best-of-both rows, and (total base, total new)."""
    rows, best = [], []
    for d in ANALYSED:
        for s in "AB":
            b, (n, cells) = base_area[d, s], new_area[d, s]
            ok = base_eq[d, s] == "pass" and new_eq[d, s][0] == "pass"
            rows.append({"design": d, "script": s, "baseline_um2": b, "with_new_cells_um2": n,
                         "reduction_pct": pct(b, n), "new_cell_instances": sum(cells.values()),
                         "equivalence": "pass" if ok else "FAIL", "method": new_eq[d, s][1],
                         "worst_delay_base_ns": dl.get((d, "baseline", s), "n/a"),
                         "worst_delay_new_ns": dl.get((d, label, s), "n/a")})
        bb = min(base_area[d, s] for s in "AB")
        bn = min(new_area[d, s][0] for s in "AB")
        best.append({"design": d, "baseline_um2": bb, "with_new_cells_um2": bn, "reduction_pct": pct(bb, bn)})
    req = [r for r in best if r["design"] in REQUIRED]
    return rows, best, (sum(r["baseline_um2"] for r in req), sum(r["with_new_cells_um2"] for r in req))


def write_table(rows: list, best: list, tot: tuple, label: str) -> None:
    with open(os.path.join(RES, "table5_final_%s.csv" % label), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    md = ["# Table 5, final set, %s areas" % label, "",
          "| Design | Script | Baseline (um2) | With new cells (um2) | Reduction | New-cell instances | Equivalence | "
          "Worst delay base / new (ns) |", "|---|---|---|---|---|---|---|---|"]
    md += ["| %s | %s | %.1f | %.1f | %.2f%% | %d | %s | %s / %s |" % (
        r["design"], r["script"], r["baseline_um2"], r["with_new_cells_um2"], r["reduction_pct"],
        r["new_cell_instances"], r["equivalence"], r["worst_delay_base_ns"], r["worst_delay_new_ns"]) for r in rows]
    md += ["", "Best of both (the smaller of scripts A and B on each side):", "",
           "| Design | Baseline (um2) | With new cells (um2) | Reduction |", "|---|---|---|---|"]
    md += ["| %s | %.1f | %.1f | %.2f%% |" % (r["design"], r["baseline_um2"], r["with_new_cells_um2"], r["reduction_pct"])
           for r in best]
    md += ["| **Total, required designs** | **%.1f** | **%.1f** | **%.2f%%** |" % (tot[0], tot[1], pct(*tot)), "",
           "Reduction = (baseline - with new cells) / baseline; positive means smaller. Baseline: hd_reduced.lib; "
           "with new cells: %s. Equivalence: ABC cec against the RTL (dsec with flip-flops), "
           "results/final/mapping_equivalence_final.csv." % os.path.relpath(LABELS[label], ROOT)]
    open(os.path.join(RES, "table5_final_%s.md" % label), "w").write("\n".join(md) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=None)
    a = ap.parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    base_area = {(r["design"], r["script"]): float(r["area_um2"]) for r in read_csv(os.path.join(RES, "mapping_areas.csv"))
                 if r["library"] == "baseline"}
    base_eq = {(r["design"], r["script"]): r["equivalence"] for r in read_csv(os.path.join(RES, "mapping_equivalence.csv"))
               if r["library"] == "baseline"}
    dl, bad, area_rows, eq_rows = delays(), 0, [], []
    for label, lib in LABELS.items():
        if not os.path.exists(lib):
            print("%s: %s not found, skipped" % (label, os.path.relpath(lib, ROOT)))
            continue
        sha = hashlib.sha256(open(lib, "rb").read()).hexdigest()
        netdir = os.path.join(ROOT, "results", "netlists", "final_" + label)
        areas = ff.map_all(lib, sha, ANALYSED, os.path.join(ROOT, "results", "logs", "final_mapping_" + label),
                           netdir=netdir, jobs=a.jobs)
        ck.LIBS["final_" + label] = lib
        eq = {}
        for (d, s), (area, cells) in areas.items():
            tag = "%s_final_%s_%s" % (d, label, s)
            method, ok, out = ck.check(d, os.path.join(netdir, "%s_%s.v" % (d, s)), "final_" + label, tag)
            lg = os.path.join(ROOT, "results", "logs", "final_equivalence")
            os.makedirs(lg, exist_ok=True)
            open(os.path.join(lg, tag + ".log"), "w").write(out)
            eq[d, s] = ("pass" if ok else "FAIL", method)
            bad += not ok
            area_rows.append({"design": d, "library": label, "script": s, "area_um2": round(area, 1),
                              "new_cell_instances": sum(cells.values()),
                              "new_cells": " ".join("%s:%d" % kv for kv in sorted(cells.items()))})
            eq_rows.append({"design": d, "library": label, "script": s, "method": method, "equivalence": eq[d, s][0]})
            print("%-10s %-5s script %s %10.1f um2  %s %s" % (d, label, s, area, method, eq[d, s][0]), flush=True)
        rows, best, tot = build_rows(base_area, base_eq, {k: (round(v[0], 1), v[1]) for k, v in areas.items()},
                                     eq, dl, label)
        write_table(rows, best, tot, label)
        print("results/table5_final_%s.md: total over the required designs %.1f -> %.1f um2 (%.2f%%)"
              % (label, tot[0], tot[1], pct(*tot)))
    for name, rows in (("mapping_areas_final.csv", area_rows), ("mapping_equivalence_final.csv", eq_rows)):
        if rows:
            with open(os.path.join(OUT, name), "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
