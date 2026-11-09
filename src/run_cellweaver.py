"""Step 11: send the final set to the cell generator (cellweaver, github.com/shalan/cellweaver).

    python3 src/run_cellweaver.py --cellweaver ~/cellweaver [--jobs 2] [--height single]
For each cell of results/final_set.json it runs, inside the cellweaver folder,
    python -m scl_gen.cli --function '<request expression>' --name <cell name> --height single \\
        --output <repo>/build/cellweaver/<cell name> --verify --characterize --char-jobs N
(`--verify` = Magic DRC and Netgen LVS; `--characterize` = measured Liberty, needs ngspice and OpenSTA `sta`;
PDK from PDK_ROOT). A cell is accepted only if the run exits 0 and the report says the checks passed.
Then it copies characterization_rc/tt/<cell>.lib to libs/real/<cell>.lib and report.json to
results/real_cells/<cell>_report.json. Nothing is invented: a failed cell stops the run (exit 1),
and is listed, so the report can say which request the generator could not build.
The cellweaver README asks for the ngspice version/hash to be recorded; this script saves
`ngspice -v` in results/real_cells/ngspice_version.txt.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from designs import ROOT                                       # noqa: E402


def command(py: str, req: dict, out: str, height: str, jobs: int) -> list[str]:
    """The cellweaver command line for one request (the request's formula and cell name unchanged)."""
    return [py, "-m", "scl_gen.cli", "--function", req["expression"], "--name", req["name"],
            "--height", height, "--output", out, "--verify", "--characterize", "--char-jobs", str(jobs)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cellweaver", default=os.environ.get("CELLWEAVER"), help="path of the cellweaver clone")
    ap.add_argument("--python", default=None, help="default: <cellweaver>/.venv/bin/python")
    ap.add_argument("--height", choices=("single", "double"), default="single")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--only", default=None, help="comma-separated cell names (default: the whole final set)")
    a = ap.parse_args(argv)
    if not a.cellweaver:
        sys.exit("give --cellweaver <clone> or set CELLWEAVER")
    cw = os.path.abspath(os.path.expanduser(a.cellweaver))
    py = a.python or os.path.join(cw, ".venv", "bin", "python")
    reqs = json.load(open(os.path.join(ROOT, "results", "final_set.json")))["requests"]
    if a.only:
        reqs = [r for r in reqs if r["name"] in a.only.split(",")]
    libs, reps = os.path.join(ROOT, "libs", "real"), os.path.join(ROOT, "results", "real_cells")
    os.makedirs(libs, exist_ok=True)
    os.makedirs(reps, exist_ok=True)
    v = subprocess.run(["ngspice", "-v"], capture_output=True, text=True)
    open(os.path.join(reps, "ngspice_version.txt"), "w").write(v.stdout + v.stderr)
    failed = []
    for r in reqs:
        out = os.path.join(ROOT, "build", "cellweaver", r["name"])
        p = subprocess.run(command(py, r, out, a.height, a.jobs), cwd=cw)
        lib = os.path.join(out, "characterization_rc", "tt", r["name"] + ".lib")
        if p.returncode != 0 or not os.path.exists(lib):
            failed.append(r["name"])
            print("FAILED", r["name"], "(exit %d)" % p.returncode, flush=True)
            continue
        shutil.copy(lib, os.path.join(libs, r["name"] + ".lib"))
        if os.path.exists(os.path.join(out, "report.json")):
            shutil.copy(os.path.join(out, "report.json"), os.path.join(reps, r["name"] + "_report.json"))
        print("ok", r["name"], flush=True)
    print("%d of %d cells generated" % (len(reqs) - len(failed), len(reqs)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
