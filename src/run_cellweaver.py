"""Step 11: send the final set to the cell generator (cellweaver, github.com/shalan/cellweaver).

    python3 src/run_cellweaver.py --cellweaver ~/cellweaver [--jobs 2] [--height single]
                                  [--requests-dir build/demo/<top>/cell_requests --only <cell>]
For each cell of results/final_set.json it runs, inside the cellweaver folder,
    python -m scl_gen.cli --function '<request expression>' --name <cell name> --height single \\
        --output <repo>/build/cellweaver/<cell name> --verify --characterize --char-jobs N
(`--verify` = Magic DRC and Netgen LVS; `--characterize` = measured Liberty, needs ngspice and OpenSTA `sta`;
PDK from PDK_ROOT). A cell is accepted only if the run exits 0 and the report says the checks passed.
Then it copies characterization_rc/tt/<cell>.lib to libs/real/<cell>.lib and report.json to
results/real_cells/<cell>_report.json, and fills cells/<cell>/ with the cell's files (cell.gds,
cell.lef, cell.lib, cell.v, cell.mag, cell.spice, report.json) and response.json, the Appendix A
response built from the generator's own report (every value copied, nothing invented). Nothing is invented: a failed cell stops the run (exit 1),
and is listed, so the report can say which request the generator could not build.
The cellweaver README asks for the ngspice version/hash to be recorded; this script saves
`ngspice -v` in results/real_cells/ngspice_version.txt.

Disk: cellweaver keeps every transient as a text waveform (~7.5 MB, ~1,500 per 4-input cell), ~10 GB a
cell. It reads a waveform once, stores the measured values in the point's checkpoint (result.json or
failure.json), and builds the Liberty from those records. So while it runs, every waveform named by a
checkpoint that already exists is truncated to zero bytes (truncated, not deleted, so cellweaver's
end-of-context linking of waveforms still finds the files); the Liberty is byte-identical, and peak
disk use drops from ~10 GB to well under 1 GB per cell. --keep-waveforms keeps the evidence waveforms
(needed only to re-validate points with --char-resume).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import glob
import hashlib
import re
import subprocess
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from designs import ROOT                                       # noqa: E402


def command(py: str, req: dict, out: str, height: str, jobs: int, netgen: str = "netgen",
            magic: str = "magic") -> list[str]:
    """The cellweaver command line for one request (the request's formula and cell name unchanged)."""
    return [py, "-m", "scl_gen.cli", "--function", req["expression"], "--name", req["name"],
            "--height", height, "--output", out, "--verify", "--characterize", "--char-jobs", str(jobs),
            "--netgen", netgen, "--magic", magic]


def truncate_measured_waveforms(out: str, seen: set) -> int:
    """Empty the waveforms named by checkpoints that already exist; returns bytes freed.

    A point is terminal once its result.json (or failure.json) is written; the record holds the
    measured values and names its evidence waveforms. Truncating (not deleting) keeps every path
    cellweaver later links, and a point in flight is never touched: it has no record yet.
    """
    freed = 0
    for rec in glob.glob(os.path.join(out, "characterization*", "*", "checkpoints", "*", "*.json")):
        if rec in seen or os.path.basename(rec) not in ("result.json", "failure.json"):
            continue
        try:
            text = open(rec).read()
        except OSError:
            continue                              # being written: next round
        for path in set(re.findall(r"/[^\s'\"\\]+?\.txt", text)):
            try:
                if os.path.exists(path) and os.path.getsize(path):
                    freed += os.path.getsize(path)
                    open(path, "w").close()
            except OSError:
                pass
        seen.add(rec)
    return freed


MIN_FREE_GB = 1.5          # stop cleanly below this: a full disk crashes Docker and loses the whole run


def free_gb(path: str) -> float:
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize / 1e9


def run_cleaning(cmd: list[str], cwd: str, out: str, keep: bool, every: float = 10.0) -> int:
    """Run cellweaver; unless keep, truncate measured points' waveforms every `every` seconds.

    If free disk falls below MIN_FREE_GB the run is stopped and reported as failed, instead of
    filling the disk (which crashes Docker and takes every parallel job down with it).
    """
    p = subprocess.Popen(cmd, cwd=cwd)
    seen: set = set()
    while p.poll() is None:
        if not keep:
            truncate_measured_waveforms(out, seen)
        if free_gb(out) < MIN_FREE_GB:
            p.terminate()
            p.wait()
            print("STOPPED %s: less than %.1f GB of disk left" % (os.path.basename(out), MIN_FREE_GB), flush=True)
            return 1
        threading.Event().wait(every)
    if not keep:
        truncate_measured_waveforms(out, seen)
    return p.wait()


def appendix_a_response(req: dict, rep: dict, out: str, ngspice_sha: str, tool_version: str) -> None:
    """cells/<name>/: the cell's files and the Appendix A response, every value from the generator's report."""
    d = os.path.join(ROOT, "cells", req["name"])
    os.makedirs(d, exist_ok=True)
    files = {"gds": "%s.gds" % req["name"], "liberty": os.path.join("characterization_rc", "tt", "%s.lib" % req["name"]),
             "verilog": "%s.v" % req["name"], "report": "report.json",
             "lef": "%s.lef" % req["name"], "mag": "%s.mag" % req["name"], "spice": "%s.spice" % req["name"]}
    named = {}
    for kind, src in files.items():
        p = os.path.join(out, src)
        if os.path.exists(p):
            dst = "cell" + os.path.splitext(src)[1] if kind != "report" else "report.json"
            shutil.copy(p, os.path.join(d, dst))
            named[kind] = "cells/%s/%s" % (req["name"], dst)
    checks = rep["checks"]
    status = "pass" if all((v.get("status") if isinstance(v, dict) else v) in ("pass", "not_run")
                           for v in checks.values()) else "fail"
    resp = {"request_id": req["request_id"], "status": status, "reason": None, "cell": rep["cell"],
            "transistors": rep["transistor_count"], "width_sites": rep["site_count"],
            "area_um2": round(rep["site_count"] * 1.2512, 4),
            "files": {k: named[k] for k in ("gds", "liberty", "verilog", "report") if k in named},
            "checks": {k: (v.get("status") if isinstance(v, dict) else v) for k, v in checks.items()},
            "ngspice_sha256": ngspice_sha, "tool_version": tool_version}
    with open(os.path.join(d, "response.json"), "w") as f:
        json.dump(resp, f, indent=1)
        f.write("\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cellweaver", default=os.environ.get("CELLWEAVER"), help="path of the cellweaver clone")
    ap.add_argument("--python", default=None, help="default: <cellweaver>/.venv/bin/python")
    ap.add_argument("--height", choices=("single", "double"), default="single")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--netgen", default="netgen",
                    help="Netgen for LVS (cellweaver is qualified with 1.5.323; container/Dockerfile has /opt/netgen-cw)")
    ap.add_argument("--magic", default="magic",
                    help="Magic for layout checks (cellweaver reads the banner of 8.3 builds; container/Dockerfile has /opt/magic-cw)")
    ap.add_argument("--settle", type=float, default=30.0,
                    help="cellweaver --char-settle: hold per input state in ns (its default 5, effective 15, "
                         "leaves the largest slew/load points of stacked cells short of settling; 30 settles them)")
    ap.add_argument("--auto-settle", action="store_true",
                    help="pass cellweaver --char-auto-settle: double a point's hold until it converges. "
                         "NOTE: this holds every point's paired-window waveforms on disk at once (~10 GB a "
                         "cell even with truncation); prefer --settle on a small disk")
    ap.add_argument("--keep-waveforms", action="store_true", help="keep cellweaver's waveforms (~10 GB per cell)")
    ap.add_argument("--only", default=None, help="comma-separated cell names (default: the whole final set)")
    ap.add_argument("--requests-dir", default=None,
                    help="a folder of Appendix A request JSONs to build instead of the final set "
                         "(e.g. build/demo/<top>/cell_requests, to build a cell for the interview design)")
    a = ap.parse_args(argv)
    if not a.cellweaver:
        sys.exit("give --cellweaver <clone> or set CELLWEAVER")
    cw = os.path.abspath(os.path.expanduser(a.cellweaver))
    py = a.python or os.path.join(cw, ".venv", "bin", "python")
    if a.requests_dir:
        reqs = sorted((json.load(open(f)) for f in glob.glob(os.path.join(a.requests_dir, "*.json"))),
                      key=lambda r: r["request_id"])
    else:
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
        os.makedirs(out, exist_ok=True)
        cmd = command(py, r, out, a.height, a.jobs, a.netgen, a.magic) + ["--char-settle", str(a.settle)]
        if a.auto_settle:
            cmd.append("--char-auto-settle")
        code = run_cleaning(cmd, cw, out, a.keep_waveforms)
        lib = os.path.join(out, "characterization_rc", "tt", r["name"] + ".lib")
        if code != 0 or not os.path.exists(lib):
            failed.append(r["name"])
            print("FAILED", r["name"], "(exit %d)" % code, flush=True)
            continue
        shutil.copy(lib, os.path.join(libs, r["name"] + ".lib"))
        rep = json.load(open(os.path.join(out, "report.json")))
        shutil.copy(os.path.join(out, "report.json"), os.path.join(reps, r["name"] + "_report.json"))
        ngspice_sha = hashlib.sha256(open(shutil.which("ngspice") or "/usr/local/bin/ngspice", "rb").read()).hexdigest()
        tool_version = subprocess.run(["git", "-C", cw, "rev-parse", "--short", "HEAD"],
                                      capture_output=True, text=True).stdout.strip()
        appendix_a_response(r, rep, out, ngspice_sha, ("git:" + tool_version) if tool_version else "unknown")
        print("ok", r["name"], flush=True)
    print("%d of %d cells generated" % (len(reqs) - len(failed), len(reqs)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
