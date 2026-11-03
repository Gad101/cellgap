"""Steps 4 and 6 of the Option 2 handout: what a class would cost to build, and
its estimated area.

STEP 4, the cost of a function: stages, inverters and transistors.
One CMOS stage computes Y = !F where F is an AND/OR formula of signals (AND =
series nMOS, OR = parallel nMOS; the pull-up network is the dual). Every
literal of F is one nMOS and one pMOS, so a stage costs 2 x literals. An
inverter is a stage with one literal (2 transistors). At most 3 transistors in
series in any stage (cmos.py enforces it for one-stage forms; the two-term
stage below never exceeds 2).

best(f) is the cheapest of three constructions, each checked by simulation:
  1. literal       : f = x (a wire, 0 transistors) or f = !x (one inverter)
  2. one stage     : f (or !f, then an output inverter) is unate in every input.
                     Inputs on which it is positive-unate get an input inverter.
                     The stage itself is the smallest pull-down formula that
                     respects the series limit (cmos.one_stage_form).
  3. Shannon stage : pick an input b. With g1 = !f(b=1) and g0 = !f(b=0)
                         f = !( (b & g1) | (!b & g0) )
                     one AOI22-like stage, plus an inverter for b, plus the
                     cost of the signals g1 and g0 (computed recursively).
This is an UPPER BOUND on the cost: it shares no inverters between signals and
does not search every factoring. That is the model's limit (report section
"Limits").

STEP 6, the area model: sites = a + b x transistors, fitted to HD's own x1
cells, one-stage and multi-stage separately, with the error reported. One site
is 0.46 um x 2.72 um = 1.2512 um2.

    python3 src/costmodel.py cost 0x077F          # cost of one function
    python3 src/costmodel.py fit                  # fit the area model to HD
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import liberty                                          # noqa: E402
from boolexpr import Expr                               # noqa: E402
from cmos import is_one_stage, one_stage_form, series_of    # noqa: E402
from tt import (MASK, NAMES, VARS, flip_input, is_negative_unate,   # noqa: E402
                is_positive_unate, support, to_hex)

SITE_UM2 = 0.46 * 2.72      # one HD site: 1.2512 um2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LIB = os.environ.get("HD_LIB", os.path.join(ROOT, "build", "pdk", "sky130_fd_sc_hd__tt_025C_1v80.lib"))


@dataclass(frozen=True)
class Cost:
    transistors: int
    stages: int        # stage levels on the longest path, inverters included
    inverters: int     # single-input inverter stages (not shared: upper bound)
    expr: str          # a formula in A, B, C, D that computes the function

    @property
    def one_stage(self) -> bool:
        return self.stages == 1          # an inverter is one stage too


def cofactor(t: int, k: int, value: int) -> int:
    """Function t with input k fixed to `value`, still written over all 4 inputs."""
    v, s = VARS[k], 1 << k
    if value:
        part = t & v
        return (part | (part >> s)) & MASK
    part = t & ~v & MASK
    return (part | (part << s)) & MASK


def _unate_option(t: int, out_inv: bool):
    h = t ^ MASK if out_inv else t
    sup = support(h)
    pos = []
    for k in sup:
        neg_ok, pos_ok = is_negative_unate(h, k), is_positive_unate(h, k)
        if not neg_ok and not pos_ok:
            return None                      # binate input: no one-stage form
        if pos_ok and not neg_ok:
            pos.append(k)
    h2 = h
    for k in pos:
        h2 = flip_input(h2, k)
    if not is_one_stage(h2):
        return None
    form = one_stage_form(h2, max_series=3)
    if form is None:                         # needs more than 3 in series
        return None
    lits = series_of(form)[0]
    fsub = re.sub(r"\b([ABCD])\b", lambda m: ("!" + m.group(1)) if NAMES.index(m.group(1)) in pos else m.group(1), form)
    expr = "(%s)" % fsub if out_inv else "!(%s)" % fsub
    n_inv = len(pos) + (1 if out_inv else 0)
    stages = 1 + (1 if pos else 0) + (1 if out_inv else 0)
    return Cost(2 * lits + 2 * n_inv, stages, n_inv, expr)


def _shannon_option(t: int, b: int):
    """f = !F with F built from input b and the signals g1 = !f(b=1), g0 = !f(b=0).

    General case      F = (b & g1) | (!b & g0)     4 literals, an inverter for b
    Absorption cases, when a cofactor of f is a constant (g is then 0 or 1):
        g1 = 0 : F = !b & g0        g0 = 0 : F = b & g1
        g1 = 1 : F = b | g0         g0 = 1 : F = !b | g1
    """
    g1, g0 = cofactor(t, b, 1) ^ MASK, cofactor(t, b, 0) ^ MASK
    nb = NAMES[b]
    sig = lambda g: best(g)               # noqa: E731  the signal that computes g
    if g1 == MASK and g0 == MASK or g1 == 0 and g0 == 0:
        return None
    if g1 == 0:
        s0 = sig(g0)
        parts, lits, inv_b, subs = "(!%s & (%s))" % (nb, s0.expr), 2, 1, [s0]
    elif g0 == 0:
        s1 = sig(g1)
        parts, lits, inv_b, subs = "(%s & (%s))" % (nb, s1.expr), 2, 0, [s1]
    elif g1 == MASK:
        s0 = sig(g0)
        parts, lits, inv_b, subs = "%s | (%s)" % (nb, s0.expr), 2, 0, [s0]
    elif g0 == MASK:
        s1 = sig(g1)
        parts, lits, inv_b, subs = "!%s | (%s)" % (nb, s1.expr), 2, 1, [s1]
    else:
        s1, s0 = sig(g1), sig(g0)
        parts, lits, inv_b, subs = "(%s & (%s)) | (!%s & (%s))" % (nb, s1.expr, nb, s0.expr), 4, 1, [s1, s0]
    depth = max([inv_b] + [x.stages for x in subs]) + 1
    return Cost(2 * lits + 2 * inv_b + sum(x.transistors for x in subs), depth,
                inv_b + sum(x.inverters for x in subs), "!(%s)" % parts)


@lru_cache(maxsize=None)
def best(t: int) -> Cost:
    """Cheapest construction of the 16-bit function t (see the module docstring)."""
    if t == 0:
        return Cost(0, 0, 0, "0")
    if t == MASK:
        return Cost(0, 0, 0, "1")
    for k in range(4):
        if t == VARS[k]:
            return Cost(0, 0, 0, NAMES[k])
        if t == VARS[k] ^ MASK:
            return Cost(2, 1, 1, "!" + NAMES[k])
    options = [_unate_option(t, False), _unate_option(t, True)]
    options += [_shannon_option(t, b) for b in support(t)]
    options = [o for o in options if o is not None]
    return min(options, key=lambda c: (c.transistors, c.stages, c.inverters))


def verify(t: int, c: Cost) -> bool:
    """Independent check: the cost's formula, simulated on all 16 rows, equals t."""
    return Expr(c.expr).eval({n: VARS[i] for i, n in enumerate(NAMES)}) == t


def compact(t: int) -> tuple[int, int]:
    """Move the inputs a function uses to A, B, C... (keeping their order).

    Returns (table over all 4 inputs with the unused ones last, number of inputs).
    The canonical class name puts unused inputs first; a cell request wants the
    used inputs to be called A, B, C...
    """
    sup = support(t)
    out = 0
    for row in range(16):
        old = 0
        for j, k in enumerate(sup):
            if (row >> j) & 1:
                old |= 1 << k
        if (t >> old) & 1:
            out |= 1 << row
    return out, len(sup)


# ---- step 6: the area model -------------------------------------------------

def hd_fit_points(lib_path: str = DEFAULT_LIB) -> tuple[list[dict], list[str]]:
    """HD's x1 combinational cells of at most 4 inputs, with the model's transistor count.

    Returns (points, skipped). A cell that HD builds as ONE stage but that needs
    more than 3 transistors in series (nand4, nor4) breaks this project's rule,
    so the model cannot describe it and it is left out of the fit.
    """
    skip = ("buf", "dly", "clk", "lpflow", "probe", "decap", "tap", "diode", "fill", "conb", "einv", "ebuf")
    pts, skipped = [], []
    for c in liberty.single_output_combinational(liberty.cells(lib_path)):
        short = c["name"].replace("sky130_fd_sc_hd__", "")
        if not short.endswith("_1") or any(s in short for s in skip) or len(c["inputs"]) > 4:
            continue
        f = Expr(c["outputs"][0]["function"]).compile(c["inputs"])(*VARS[:len(c["inputs"])])
        if len(support(f)) < len(c["inputs"]):
            continue
        if is_one_stage(f) and one_stage_form(f, max_series=3) is None:
            skipped.append(short)
            continue
        k = best(f)
        pts.append({"cell": short, "inputs": len(c["inputs"]), "area_um2": c["area"],
                    "sites": c["area"] / SITE_UM2, "transistors": k.transistors,
                    "stages": k.stages, "inverters": k.inverters,
                    "kind": "one-stage" if k.one_stage else "multi-stage"})
    return pts, skipped


@dataclass
class AreaModel:
    """sites = a + b x transistors, one line per kind of cell."""
    lines: dict            # kind -> (a, b)

    def sites(self, c: Cost) -> int:
        a, b = self.lines["one-stage" if c.one_stage else "multi-stage"]
        return max(1, math.ceil(a + b * c.transistors - 1e-9))

    def area(self, c: Cost) -> float:
        return round(self.sites(c) * SITE_UM2, 4)


def fit(points: list[dict]) -> tuple[AreaModel, dict]:
    lines, report = {}, {}
    for kind in ("one-stage", "multi-stage"):
        p = [x for x in points if x["kind"] == kind]
        t = np.array([x["transistors"] for x in p], float)
        s = np.array([x["sites"] for x in p], float)
        b, a = np.polyfit(t, s, 1)
        lines[kind] = (float(a), float(b))
        m = AreaModel(lines)
        # the error that matters is the one after rounding up to whole sites
        pred = np.array([m.sites(Cost(x["transistors"], 1 if kind == "one-stage" else 2,
                                      0 if kind == "one-stage" else 1, "")) for x in p], float)
        err = pred - np.round(s)
        report[kind] = {"cells": len(p), "a": round(float(a), 4), "b": round(float(b), 4),
                        "mean_abs_error_sites": round(float(np.abs(err).mean()), 3),
                        "max_abs_error_sites": float(np.abs(err).max()),
                        "mean_abs_error_pct": round(float(np.mean(np.abs(err) / np.round(s)) * 100), 2),
                        "worst_cell": p[int(np.abs(err).argmax())]["cell"]}
    return AreaModel(lines), report


def main(argv):
    if len(argv) >= 3 and argv[1] == "cost":
        t = int(argv[2], 16)
        c = best(t)
        print("function %s  transistors %d  stages %d  inverters %d" % (to_hex(t), c.transistors, c.stages, c.inverters))
        print("expression", c.expr, "| verified:", verify(t, c))
        return 0
    if len(argv) >= 2 and argv[1] == "fit":
        pts, skipped = hd_fit_points()
        model, rep = fit(pts)
        os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
        with open(os.path.join(ROOT, "results", "area_model_fit.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(pts[0]))
            w.writeheader()
            w.writerows(pts)
        out = {"site_um2": SITE_UM2, "lines": {k: {"a": v[0], "b": v[1]} for k, v in model.lines.items()},
               "error": rep, "left_out_series_rule": skipped, "library": os.path.basename(os.path.realpath(DEFAULT_LIB))}
        with open(os.path.join(ROOT, "results", "area_model.json"), "w") as f:
            json.dump(out, f, indent=1)
        print(json.dumps(out, indent=1))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
