"""Verilog simulation models of the new cells, for the gate-level testbenches.

    python3 src/write_new_cell_verilog_sims.py [--requests results/cell_requests] [--out libs/new_cell_verilog_sims.v]
The PDK ships a Verilog model of every HD cell (sky130_fd_sc_hd.v); the new
cells exist only in our Liberty file, which a simulator cannot read. Each model
is one assign of the cell's function, the same expression the Liberty file uses.
Real cells from the generator come with their own Verilog (overview Appendix A).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from designs import ROOT                       # noqa: E402


def model(req: dict) -> str:
    ports = ", ".join(req["inputs"])
    return ("module %s (input %s, output %s);\n  assign %s = %s;\nendmodule\n"
            % (req["name"], ports, req["output"], req["output"], req["expression"]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--requests", default=os.path.join(ROOT, "results", "cell_requests"))
    ap.add_argument("--out", default=os.path.join(ROOT, "libs", "new_cell_verilog_sims.v"))
    a = ap.parse_args(argv)
    reqs = []
    for p in sorted(glob.glob(os.path.join(a.requests, "*.json"))):
        with open(p) as f:
            reqs.append(json.load(f))
    reqs.sort(key=lambda r: r["request_id"])
    with open(a.out, "w") as f:
        f.write("// Simulation models of the new cells (src/write_new_cell_verilog_sims.py)\n`timescale 1ns/1ps\n\n")
        f.write("\n".join(model(r) for r in reqs))
    print("%d new-cell models written to %s" % (len(reqs), os.path.relpath(a.out, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
