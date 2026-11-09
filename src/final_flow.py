"""Shared helpers of checkpoint 3: build a library with chosen new cells, map designs with it.

Nothing here invents a number: areas come from Yosys `stat -liberty` (through
table1.map_design, the handout's commands) and from the requests' estimated areas.

A mapping is deterministic, so its result is cached by the SHA-256 of the library text, the
design and the script (build/final_cache.json, not committed). A cache hit gives the same
number a new run would give.
"""
from __future__ import annotations

import concurrent.futures as cf
import glob
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from designs import GIVEN, REQUIRED, ROOT, SCRIPTS            # noqa: E402
from map_with_and_without_new_cells import new_cell_counts    # noqa: E402
from table1 import map_design                                  # noqa: E402
import write_liberty_with_new_cells as wl                      # noqa: E402

CACHE = os.path.join(ROOT, "build", "final_cache.json")
BASE_LIB = os.path.join(GIVEN, "hd_reduced.lib")
EPS = 0.05          # um2: a drop smaller than this is rounding in Yosys's printout, not a saving


def load_requests(dir_: str | None = None) -> list[dict]:
    """All cell requests, in candidate rank order (C-001 first)."""
    dir_ = dir_ or os.path.join(ROOT, "results", "cell_requests")
    reqs = [json.load(open(p)) for p in glob.glob(os.path.join(dir_, "*.json"))]
    return sorted(reqs, key=lambda r: r["request_id"])


def with_area_scale(req: dict, factor: float) -> dict:
    """Copy of a request whose estimated area is scaled (the 30% experiment)."""
    r = dict(req)
    r["estimated_area_um2"] = round(req["estimated_area_um2"] * factor, 4)
    return r


def build_lib(reqs: list[dict], out: str) -> str:
    """hd_reduced.lib plus the given cells; returns the SHA-256 of the text written."""
    wl.write(reqs, BASE_LIB, out)
    return hashlib.sha256(open(out, "rb").read()).hexdigest()


def _load_cache() -> dict:
    try:
        return json.load(open(CACHE))
    except (OSError, ValueError):
        return {}


def _one(job):
    d, script, lib, log, net = job
    area, _ = map_design(d, lib, SCRIPTS[script], log,
                         extra="write_verilog -noattr %s\n" % net if net else "")
    return d, script, area, new_cell_counts(log)


def map_all(lib: str, sha: str, designs: list[str], logdir: str, netdir: str | None = None,
            jobs: int | None = None) -> dict:
    """{(design, script): (area, {new cell: instances})} for scripts A and B on each design."""
    cache = _load_cache()
    out, todo = {}, []
    for d in designs:
        for s in "AB":
            hit = cache.get("%s|%s|%s" % (sha, d, s))
            if hit and not netdir:
                out[d, s] = (hit["area"], hit["cells"])
            else:
                tag = "%s_%s_%s" % (sha[:8], d, s)
                net = os.path.join(netdir, "%s_%s.v" % (d, s)) if netdir else None
                if net:
                    os.makedirs(netdir, exist_ok=True)
                todo.append((d, s, lib, os.path.join(logdir, tag + ".log"), net))
    todo.sort(key=lambda j: j[0] not in ("risc8", "fir10"))        # big designs first
    with cf.ProcessPoolExecutor(max_workers=jobs or int(os.environ.get("JOBS", os.cpu_count() or 1))) as ex:
        for d, s, area, cells in ex.map(_one, todo):
            out[d, s] = (area, cells)
            cache["%s|%s|%s" % (sha, d, s)] = {"area": area, "cells": cells}
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(cache, open(CACHE, "w"))
    return out


def best_total(areas: dict, designs: list[str] = REQUIRED) -> float:
    """Sum over designs of the smaller of scripts A and B (the handout's best of both)."""
    return sum(min(areas[d, "A"][0], areas[d, "B"][0]) for d in designs)
