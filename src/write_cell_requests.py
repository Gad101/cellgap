"""Step 8, part 1: one cell request per candidate (Option 2 handout, section 4).

    python3 src/write_cell_requests.py [--candidates results/candidates.json] [--out results/cell_requests]
Writes <out>/<cell name>.json with exactly the request fields of overview
Appendix A, in its order. Every request must pass request.check (expression and
truth table agree, at most 4 inputs); if any is refused, nothing is written.
Requests left in <out> from an earlier run are removed first.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import request                                 # noqa: E402
from designs import ROOT                       # noqa: E402

FIELDS = ("request_id", "name", "inputs", "output", "expression", "truth_table", "sizing",
          "estimated_area_um2")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default=os.path.join(ROOT, "results", "candidates.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "cell_requests"))
    a = ap.parse_args(argv)
    cands = json.load(open(a.candidates))["candidates"]
    reqs = [{k: c[k] for k in FIELDS} for c in cands]
    refused = [(r["name"], why) for r in reqs for ok, why in [request.check(r)] if not ok]
    if refused:
        for name, why in refused:
            print("REFUSED %s: %s" % (name, why))
        return 1
    os.makedirs(a.out, exist_ok=True)
    for old in glob.glob(os.path.join(a.out, "*.json")):   # no stale requests for dropped candidates
        os.remove(old)
    for r in reqs:
        with open(os.path.join(a.out, r["name"] + ".json"), "w") as f:
            json.dump(r, f, indent=1)
            f.write("\n")
    print("%d requests written to %s, all pass request.check" % (len(reqs), os.path.relpath(a.out, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
