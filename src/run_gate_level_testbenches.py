"""Step 9: Tutorial 4's gate-level testbenches on the SPM and multiplier netlists.

    python3 src/run_gate_level_testbenches.py
Runs on the host with Icarus Verilog 13 (overview Table 1); the student pack's
image has no Icarus. Each mapped netlist of SPM and mul (baseline and with new
cells, scripts A and B, from make mapping; and the final est and real netlists from
make final-table5, when they exist) is simulated with
the iverilog command of Tutorial 4's Makefile (gls, mul-gls, mul-exh): the
testbench, the netlist, the PDK cell models, and libs/new_cell_verilog_sims.v
for the new cells. A run passes when vvp exits 0, prints PASS, and prints no
ERROR, MISMATCH or FAIL.

Writes results/gate_level_testbenches.csv and
results/logs/gate_level_testbenches/<netlist>_<testbench>.log. Exits 1 if any fails.
"""
from __future__ import annotations

import csv
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from designs import ROOT                       # noqa: E402

IVERILOG = os.environ.get("IVERILOG", "iverilog")
VVP = os.environ.get("VVP", "vvp")
CELLS = [os.path.join(ROOT, "build", "pdk", "verilog", f) for f in ("primitives.v", "sky130_fd_sc_hd.v")]
NEW_CELLS = os.path.join(ROOT, "libs", "new_cell_verilog_sims.v")
TCLK = "1.25"                                  # Tutorial 4's Makefile
# design: [(testbench top, testbench file, extra iverilog flags)]
TESTBENCHES = {
    "spm": [("SPM_tb", os.path.join(ROOT, "build", "tut4", "SPM_tb.v"), ["-DTCLK=%s" % TCLK])],
    "mul": [("mul_tb", os.path.join(ROOT, "build", "tut2", "mul_tb.v"), []),
            ("mul_exhaustive_tb", os.path.join(ROOT, "build", "tut2", "mul_exhaustive_tb.v"), [])],
}
# Tutorial 4's QUIET filter: Icarus warnings about the PDK models, one per line.
NOISE = re.compile(r"Choosing typ expression|Timing checks are not supported")
BAD = re.compile(r"\b(ERROR|MISMATCH|FAIL)\b")
WORK = os.path.join(ROOT, "build", "gate_level_testbenches")


def simulate(netlist: str, top: str, tb: str, flags: list[str], out: str) -> tuple[bool, str]:
    """(passed?, output) of one testbench on one netlist."""
    os.makedirs(WORK, exist_ok=True)
    exe = os.path.join(WORK, os.path.basename(out))
    c = subprocess.run([IVERILOG, *flags, "-s", top, "-o", exe, tb, netlist, *CELLS, NEW_CELLS],
                       capture_output=True, text=True)
    text = "\n".join(l for l in (c.stdout + c.stderr).splitlines() if not NOISE.search(l))
    if c.returncode != 0:
        return False, text + "\niverilog failed"
    r = subprocess.run([VVP, exe], capture_output=True, text=True, cwd=WORK)   # testbench .vcd files land in build/
    text += "\n" + r.stdout + r.stderr
    return r.returncode == 0 and "PASS" in r.stdout and not BAD.search(r.stdout), text


def main() -> int:
    logs = os.path.join(ROOT, "results", "logs", "gate_level_testbenches")
    os.makedirs(logs, exist_ok=True)
    rows = []
    for design, tbs in TESTBENCHES.items():
        for lib in ("baseline", "est", "final_est", "final_real"):
            for script in "AB":
                tag = "%s_%s_%s" % (design, lib, script)
                if lib.startswith("final"):      # make final-table5 writes these; skip if not made yet
                    net = os.path.join(ROOT, "results", "netlists", lib, "%s_%s.v" % (design, script))
                    if not os.path.exists(net):
                        continue
                else:
                    net = os.path.join(ROOT, "results", "netlists", tag + ".v")
                for top, tb, flags in tbs:
                    ok, text = simulate(net, top, tb, flags, "%s_%s" % (tag, top))
                    with open(os.path.join(logs, "%s_%s.log" % (tag, top)), "w") as f:
                        f.write(text)
                    verdict = next((l.strip() for l in text.splitlines() if l.startswith(("PASS", "FAIL"))), "")
                    rows.append({"design": design, "library": lib, "script": script, "testbench": top,
                                 "result": "pass" if ok else "FAIL", "message": verdict})
                    print("%-4s %-8s script %s  %-18s %s  %s" % (design, lib, script, top,
                                                                 "pass" if ok else "FAIL", verdict), flush=True)
    with open(os.path.join(ROOT, "results", "gate_level_testbenches.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    failed = sum(r["result"] != "pass" for r in rows)
    print("%d of %d gate-level testbench runs pass" % (len(rows) - failed, len(rows)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
