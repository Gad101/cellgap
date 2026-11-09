"""Cell-by-cell curve (handout section 7): total best-of-both area after each final cell is added.

    python3 src/make_curve.py
Reads results/final_set.json (written by select_final_set.py, cells in the order the tool chose
them). Writes results/curve.csv, results/curve.md and results/curve.svg (a plain SVG, no
plotting library). Every number is copied from final_set.json.
"""
from __future__ import annotations

import csv
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


def svg(pts: list[dict], w: int = 640, h: int = 360) -> str:
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
           'estimated areas</text>' % L]
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


def main() -> int:
    fs = json.load(open(os.path.join(RES, "final_set.json")))
    pts = points(fs)
    with open(os.path.join(RES, "curve.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(pts[0]))
        w.writeheader()
        w.writerows(pts)
    md = ["# Cell-by-cell curve (estimated areas)", "",
          "| Cells added | Cell added | Total best-of-both area (um2) | Gain of this cell (um2) | Reduction vs baseline |",
          "|---|---|---|---|---|"]
    md += ["| %d | %s | %.1f | %.1f | %.3f%% |" % (p["cells"], p["added_cell"], p["total_um2"], p["step_gain_um2"],
                                                  p["reduction_pct"]) for p in pts]
    open(os.path.join(RES, "curve.md"), "w").write("\n".join(md) + "\n")
    open(os.path.join(RES, "curve.svg"), "w").write(svg(pts))
    print("results/curve.{csv,md,svg}: %d points, %.1f -> %.1f um2" % (len(pts), pts[0]["total_um2"], pts[-1]["total_um2"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
