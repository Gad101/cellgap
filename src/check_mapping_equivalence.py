"""Step 9: check every mapped netlist against the RTL with ABC (Option 2 handout, section 4).

    python3 src/check_mapping_equivalence.py [--designs cpu8,spm]
Reference: the RTL through the commands of section 2 up to dfflibmap (same
flip-flop cells as the netlist), so the check covers what ABC mapped, where the
new cells are used. Both sides are flattened with the Liberty cell functions and
written as AIGs. A design without flip-flops is checked with ABC's cec; one with
flip-flops with ABC's dsec (sequential), because cec pairs flip-flops by their
order in the file and the netlist may list them in another order.

Reads results/mapping_areas.csv (make mapping); writes results/mapping_equivalence.csv and
results/logs/mapping_equivalence/<design>_<library>_<script>.log. Exits 1 if any check fails.
"""
from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from designs import DESIGNS, GIVEN, ROOT, files              # noqa: E402

YOSYS = os.environ.get("YOSYS", "yosys")
ABC = os.environ.get("ABC", "yosys-abc")
LIBS = {"baseline": os.path.join(GIVEN, "hd_reduced.lib"),
        "est": os.path.join(ROOT, "libs", "hd_reduced_plus_new_cells_est.lib")}
WORK = os.path.join(ROOT, "build", "mapping_equivalence")


def yosys(script: str) -> None:
    r = subprocess.run([YOSYS, "-q", "-p", script], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("yosys failed:\n%s" % (r.stdout + r.stderr)[-1500:])


def reference(design: str, lib: str, out: str) -> None:
    """RTL -> synth -> dfflibmap, as in section 2 but without abc."""
    top, _, flags = DESIGNS[design]
    reads = "; ".join("read_verilog %s %s" % (flags, f) for f in files(design))
    yosys("%s; synth -flatten -top %s; dfflibmap -liberty %s; write_verilog -noattr %s" % (reads, top, lib, out))


def to_aig(netlist: str, top: str, lib: str, out: str) -> int:
    """Flatten a cell netlist with the Liberty functions into an AIG; return its latch count."""
    yosys("read_liberty -ignore_miss_func %s; read_verilog %s; hierarchy -top %s; flatten; "
          "async2sync; dffunmap; aigmap; write_aiger %s" % (lib, netlist, top, out))
    with open(out, "rb") as f:
        return int(f.readline().split()[3])          # header: aig M I L O A


def abc_equal(ref: str, gate: str, latches: int) -> tuple[str, bool, str]:
    """(method, equivalent?, ABC output). dsec starts both from the all-zero state."""
    if latches == 0:
        method, cmd = "cec", "cec %s %s" % (ref, gate)
    else:
        z0, z1 = ref[:-4] + "_0.aig", gate[:-4] + "_0.aig"
        method = "dsec"
        cmd = ("read_aiger %s; zero; write_aiger %s; read_aiger %s; zero; write_aiger %s; dsec %s %s"
               % (ref, z0, gate, z1, z0, z1))
    r = subprocess.run([ABC, "-c", cmd], capture_output=True, text=True)
    out = r.stdout + r.stderr
    return method, "Networks are equivalent" in out, out


def check(design: str, netlist: str, library: str, tag: str) -> tuple[str, bool, str]:
    """Equivalence of one mapped netlist with its RTL reference."""
    os.makedirs(WORK, exist_ok=True)
    top, lib = DESIGNS[design][0], LIBS[library]
    ref_v = os.path.join(WORK, "%s_%s_ref.v" % (design, library))
    if not os.path.exists(ref_v):
        reference(design, lib, ref_v)
    ref_aig = os.path.join(WORK, "%s_%s_ref.aig" % (design, library))
    latches = to_aig(ref_v, top, lib, ref_aig)
    gate_aig = os.path.join(WORK, tag + ".aig")
    to_aig(netlist, top, lib, gate_aig)
    return abc_equal(ref_aig, gate_aig, latches)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--designs", default="")
    a = ap.parse_args(argv)
    want = set(a.designs.split(",")) if a.designs else None
    with open(os.path.join(ROOT, "results", "mapping_areas.csv")) as f:
        maps = [r for r in csv.DictReader(f) if want is None or r["design"] in want]
    logs = os.path.join(ROOT, "results", "logs", "mapping_equivalence")
    os.makedirs(logs, exist_ok=True)
    for old in os.listdir(WORK) if os.path.isdir(WORK) else []:   # references follow the current libraries
        os.remove(os.path.join(WORK, old))
    rows = []
    for m in maps:
        tag = "%s_%s_%s" % (m["design"], m["library"], m["script"])
        method, ok, out = check(m["design"], os.path.join(ROOT, m["netlist"]), m["library"], tag)
        with open(os.path.join(logs, tag + ".log"), "w") as f:
            f.write(out)
        rows.append({"design": m["design"], "library": m["library"], "script": m["script"],
                     "method": method, "equivalence": "pass" if ok else "FAIL"})
        print("%-10s %-8s script %s  %-4s %s" % (m["design"], m["library"], m["script"], method,
                                                  "pass" if ok else "FAIL"), flush=True)
    with open(os.path.join(ROOT, "results", "mapping_equivalence.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    failed = sum(r["equivalence"] != "pass" for r in rows)
    print("%d of %d mappings equivalent to the RTL" % (len(rows) - failed, len(rows)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
