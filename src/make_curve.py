"""Cell-by-cell curve (handout section 7): total best-of-both area after each final cell is added.

    python3 src/make_curve.py [--real] [--jobs N]
Reads results/final_set.json (written by select_final_set.py, cells in the order the tool chose
them). Writes results/curve.csv, results/curve.md and results/curve.svg (a plain SVG, no
plotting library). Every number is copied from final_set.json.
With --real it draws the same curve with the generator's real cells (handout section 7, "give
everything twice"): the cells are added in the same order the tool chose, but each point is a new
mapping of the required designs with a library in which those cells' estimated groups are replaced
by their real ones (libs/real/, src/real_lib.py). Writes results/curve_real.{csv,md,svg}.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from designs import ROOT                                       # noqa: E402

RES = os.path.join(ROOT, "results")


def points(fs: dict) -> list[dict]:
    """Step 0 (baseline) then one point per kept cell, with the saving that cell added."""
    pts = [{"cells": 0, "added_cell": "-", "total_um2": fs["baseline_total_um2"], "step_gain_um2": 0.0,
            "reduction_pct": 0.0}]
    for s in fs["steps"]:
        prev = pts[-1]["total_um2"]
        pts.append({"cells": s["order"], "added_cell": s["name"], "total_um2": s["total_um2"],
                    "step_gain_um2": round(prev - s["total_um2"], 1), "reduction_pct": s["reduction_pct"]})
    return pts


def real_points(fs: dict, jobs: int | None) -> list[dict]:
    """Baseline, then one remap per prefix of the final set with real cells in place of the estimates."""
    import final_flow as ff
    import real_lib
    work = os.path.join(ROOT, "build", "curve_real")
    os.makedirs(work, exist_ok=True)
    real = {}
    for name in fs["cells"]:
        path = os.path.join(ROOT, "libs", "real", name + ".lib")
        if not os.path.exists(path):
            sys.exit("missing %s: run `make real-cells` first" % path)
        text = open(path).read()
        a, b = real_lib.group(text, name)
        real[name] = text[a:b]
    pts = []
    for k in range(len(fs["requests"]) + 1):
        reqs = fs["requests"][:k]
        lib = os.path.join(work, "lib_%d.lib" % k)
        sha = ff.build_lib(reqs, lib)
        if k:
            text = real_lib.replace_cells(open(lib).read(), {r["name"]: real[r["name"]] for r in reqs})
            open(lib, "w").write(text)
            sha = hashlib.sha256(text.encode()).hexdigest()
        areas = ff.map_all(lib, sha, fs["designs"], os.path.join(work, "logs"), jobs=jobs)
        tot = round(ff.best_total(areas, fs["designs"]), 1)
        base = pts[0]["total_um2"] if pts else tot
        prev = pts[-1]["total_um2"] if pts else tot
        pts.append({"cells": k, "added_cell": fs["requests"][k - 1]["name"] if k else "-", "total_um2": tot,
                    "step_gain_um2": round(prev - tot, 1), "reduction_pct": round(100 * (base - tot) / base, 3)})
        print("%d cells: %.1f um2" % (k, tot), flush=True)
    return pts


def svg(pts: list[dict], w: int = 640, h: int = 360, label: str = "estimated areas") -> str:
    """Line chart of total area against number of cells, axis not forced to zero (said on the chart)."""
    lo, hi = min(p["total_um2"] for p in pts), max(p["total_um2"] for p in pts)
    pad = (hi - lo) * 0.15 or 1.0
    lo, hi = lo - pad, hi + pad
    L, R, T, B = 80, 20, 30, 50
    n = max(len(pts) - 1, 1)
    x = lambda i: L + (w - L - R) * i / n
    y = lambda v: T + (h - T - B) * (hi - v) / (hi - lo)
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" font-family="sans-serif" font-size="12">' % (w, h),
           '<rect width="100%" height="100%" fill="white"/>',
           '<text x="%d" y="18" font-size="14">Total best-of-both area of the required designs (um2), '
           '%s</text>' % (L, label)]
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        out.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#ddd"/>' % (L, w - R, y(v), y(v)))
        out.append('<text x="%d" y="%.1f" text-anchor="end">%.1f</text>' % (L - 6, y(v) + 4, v))
    for p in pts:
        out.append('<text x="%.1f" y="%d" text-anchor="middle">%d</text>' % (x(p["cells"]), h - B + 16, p["cells"]))
    out.append('<text x="%d" y="%d" text-anchor="middle">new cells added, in the order the tool chose them '
               '(vertical axis does not start at 0)</text>' % ((L + w - R) // 2, h - 8))
    out.append('<polyline fill="none" stroke="#1f6feb" stroke-width="2" points="%s"/>'
               % " ".join("%.1f,%.1f" % (x(p["cells"]), y(p["total_um2"])) for p in pts))
    for p in pts:
        out.append('<circle cx="%.1f" cy="%.1f" r="4" fill="#1f6feb"/>' % (x(p["cells"]), y(p["total_um2"])))
    return "\n".join(out) + "\n</svg>\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", action="store_true", help="the curve with the generator's real cells")
    ap.add_argument("--jobs", type=int, default=None)
    a = ap.parse_args(argv)
    fs = json.load(open(os.path.join(RES, "final_set.json")))
    tag, label = ("curve_real", "real cells") if a.real else ("curve", "estimated areas")
    pts = real_points(fs, a.jobs) if a.real else points(fs)
    with open(os.path.join(RES, tag + ".csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(pts[0]))
        w.writeheader()
        w.writerows(pts)
    md = ["# Cell-by-cell curve (%s)" % label, "",
          "| Cells added | Cell added | Total best-of-both area (um2) | Gain of this cell (um2) | Reduction vs baseline |",
          "|---|---|---|---|---|"]
    md += ["| %d | %s | %.1f | %.1f | %.3f%% |" % (p["cells"], p["added_cell"], p["total_um2"], p["step_gain_um2"],
                                                  p["reduction_pct"]) for p in pts]
    open(os.path.join(RES, tag + ".md"), "w").write("\n".join(md) + "\n")
    open(os.path.join(RES, tag + ".svg"), "w").write(svg(pts, label=label))
    print("results/%s.{csv,md,svg}: %d points, %.1f -> %.1f um2" % (tag, len(pts), pts[0]["total_um2"], pts[-1]["total_um2"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
