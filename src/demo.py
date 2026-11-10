"""make demo: the whole flow of handout section 4 (steps 1 to 10) on one design given on the day.

    python3 src/demo.py <design.v | folder of .v/.sv | "a.v b.v"> <top> [read_verilog flags]
Steps, each with the same code `make all` and `make final` use:
  1  AIG (Yosys), and the graph after ABC strash; dch
  2  cuts of up to 4 inputs, each checked by simulation (before and after ABC)
  3  classes up to input order and output inversion, and NPN classes
  4-7  cost, redundancy against HD (Table 3), area model, ranking (src/candidates.py),
     with the area per AND node taken from this design's own baseline mappings
  8  cell requests (Appendix A) and the Liberty file, which Yosys must import as 189 + N cells
  9  map with and without the new cells, scripts A and B, every netlist checked with ABC cec/dsec
  10 greedy final set for this design (src/select_final_set.py)
and the design mapped with the project's final set (estimated, and real when libs/ has it).
Everything is written under build/demo/<top>/; results/ is not touched.
Exits 1 if a cut check, the Liberty check or an equivalence check fails.
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aiger                                   # noqa: E402
import candidates                              # noqa: E402
import check_mapping_equivalence as ck         # noqa: E402
import design_stats                            # noqa: E402
import final_flow as ff                        # noqa: E402
import liberty                                 # noqa: E402
import select_final_set                        # noqa: E402
import write_cell_requests                     # noqa: E402
import write_liberty_with_new_cells as wl      # noqa: E402
from designs import ROOT, SCRIPTS, register    # noqa: E402
from map_with_and_without_new_cells import new_cell_counts   # noqa: E402
from table1 import map_design                  # noqa: E402

GROUP = os.environ.get("GROUP", "gb2")
PROJECT_LIBS = {"final_est": os.path.join(ROOT, "libs", "hd_reduced_plus_final_set_est.lib"),
                "final_real": os.path.join(ROOT, "libs", "hd_reduced_plus_final_set_real.lib")}


def verilog_files(arg: str) -> list[str]:
    if os.path.isdir(arg):
        fs = sorted(glob.glob(os.path.join(arg, "**", "*.v"), recursive=True)
                    + glob.glob(os.path.join(arg, "**", "*.sv"), recursive=True))
    else:
        fs = arg.split()
    missing = [f for f in fs if not os.path.isfile(f)]
    if not fs or missing:
        sys.exit("design files not found: %s" % (missing or arg))
    return [os.path.realpath(f) for f in fs]


def header(text: str) -> None:
    print("\n==== %s" % text, flush=True)


def map_both(name: str, lib: str, label: str, out: str) -> dict:
    """Scripts A and B with one library: {script: (area, {new cell: instances}, netlist)}."""
    res = {}
    for s in "AB":
        log = os.path.join(out, "logs", "%s_%s.log" % (label, s))
        net = os.path.join(out, "netlists", "%s_%s.v" % (label, s))
        os.makedirs(os.path.dirname(net), exist_ok=True)
        area, _ = map_design(name, lib, SCRIPTS[s], log, extra="write_verilog -noattr %s\n" % net)
        res[s] = (round(area, 1), new_cell_counts(log), net)
    return res


def equivalent(name: str, lib: str, label: str, net: str, out: str) -> tuple[str, str]:
    """(method, pass|FAIL) of one netlist against the RTL, with check_mapping_equivalence.check."""
    ck.LIBS[label] = lib
    method, ok, text = ck.check(name, net, label, os.path.basename(net)[:-2])
    with open(os.path.join(out, "logs", "equiv_%s.log" % os.path.basename(net)[:-2]), "w") as f:
        f.write(text)
    return method, "pass" if ok else "FAIL"


def pct(base: float, new: float) -> float:
    return round(100 * (base - new) / base, 2)


def main(argv) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    fs, top = verilog_files(argv[1]), argv[2]
    flags = argv[3] if len(argv) > 3 else ""
    name = "demo_" + top
    register(name, top, fs, flags)
    out = os.path.join(ROOT, "build", "demo", top)
    os.makedirs(out, exist_ok=True)
    for old in glob.glob(os.path.join(ck.WORK, name + "_*")):   # no stale RTL references
        os.remove(old)
    failed = []

    header("step 1: AIG of %s (top %s), and after ABC strash; dch" % (" ".join(map(os.path.basename, fs)), top))
    aag = os.path.join(out, name + ".aag")
    subprocess.run([os.path.join(ROOT, "src", "make_aig.sh"), " ".join(fs), top, aag, flags], check=True)
    subprocess.run([os.path.join(ROOT, "src", "abc_after.sh"), aag[:-4] + ".aig", aag[:-4] + "_abc.aig"], check=True)

    header("steps 2-3: cuts (checked by simulation) and classes")
    print("%-10s %7s %5s %7s %8s %7s %6s  %s" % ("graph", "inputs", "FFs", "ANDs", "cuts", "P-cls", "NPN", "cut check"))
    for p in (aag, aag[:-4] + "_abc.aig"):
        s = design_stats.stats(p)
        print("%-10s %7d %5d %7d %8d %7d %6d  %s" % (s["graph"], s["inputs"], s["latches"], s["ands"], s["cuts"],
                                                    s["p_classes"], s["npn_classes"], s["check"]))
        if s["check"] != "pass":
            failed.append("cut check on " + s["graph"])

    header("baseline: hd_reduced.lib, scripts A and B (the commands of handout section 2)")
    base = map_both(name, ff.BASE_LIB, "baseline", out)
    for s in "AB":
        print("script %s  %10.1f um2" % (s, base[s][0]))
    area = {c["name"]: (c["area"], c["sequential"]) for c in liberty.cells(ff.BASE_LIB)}
    n_ands = aiger.read(aag).A
    a_and = min(candidates.comb_area(os.path.join(out, "logs", "baseline_%s.log" % s), area) for s in "AB") / n_ands
    print("combinational area per AND node (best of A and B): %.3f um2" % a_and)

    header("steps 4-7: cost, redundancy against HD (Table 3), area model, ranking")
    candidates.main(["--group", GROUP, "--designs", name, "--aig-dir", out, "--out", out,
                     "--a-and", "%.6f" % a_and, "--top", "10"])
    n_cand = len(json.load(open(os.path.join(out, "candidates.json")))["candidates"])

    rows = []                                  # (label, script, area, instances, method, equivalence)
    for s in "AB":
        rows.append(("baseline", s, base[s][0], 0) + equivalent(name, ff.BASE_LIB, "baseline", base[s][2], out))
    libs = {}
    if n_cand:
        header("step 8: %d cell requests and the Liberty file" % n_cand)
        reqdir = os.path.join(out, "cell_requests")
        write_cell_requests.main(["--candidates", os.path.join(out, "candidates.json"), "--out", reqdir])
        libs["candidates"] = os.path.join(out, "hd_reduced_plus_demo_candidates_est.lib")
        if wl.main(["--requests", reqdir, "--out", libs["candidates"]]) != 0:
            failed.append("Liberty check")

        header("step 10: greedy final set for this design (keep a cell only if best of A and B drops)")
        g = select_final_set.greedy(ff.load_requests(reqdir), 10, 2, designs=[name])
        if g["kept"]:
            libs["greedy"] = os.path.join(out, "hd_reduced_plus_demo_greedy_est.lib")
            ff.build_lib(g["kept"], libs["greedy"])
        print("kept %d of %d: %s" % (len(g["kept"]), len(g["log"]), " ".join(r["name"] for r in g["kept"]) or "none"))
    else:
        print("no candidate is estimated to save area on this design: steps 8 and 10 have nothing to do")
    for label, p in PROJECT_LIBS.items():
        if os.path.exists(p):
            libs[label] = p

    header("step 9: map with each library, scripts A and B; every netlist checked against the RTL")
    for label, lib in libs.items():
        m = map_both(name, lib, label, out)
        for s in "AB":
            rows.append((label, s, m[s][0], sum(m[s][1].values())) + equivalent(name, lib, label, m[s][2], out))

    header("Table 5 for %s (um2; reduction against the baseline, same script)" % top)
    b = {r[1]: r[2] for r in rows if r[0] == "baseline"}
    lines = ["| Library | Script | Baseline | With new cells | Reduction | New-cell instances | Equivalence |",
             "|---|---|---:|---:|---:|---:|---|"]
    for label, s, a, n, method, eq in rows:
        lines.append("| %s | %s | %.1f | %.1f | %.2f%% | %d | %s (%s) |" % (label, s, b[s], a, pct(b[s], a), n, eq, method))
        if eq != "pass":
            failed.append("equivalence %s %s" % (label, s))
    lines += ["", "Best of both (smaller of A and B on each side):", ""]
    for label in dict.fromkeys(r[0] for r in rows if r[0] != "baseline"):
        new = min(r[2] for r in rows if r[0] == label)
        lines.append("- %s: %.1f -> %.1f um2, %.2f%%" % (label, min(b.values()), new, pct(min(b.values()), new)))
    text = "\n".join(lines)
    print(text)
    with open(os.path.join(out, "table5_demo.md"), "w") as f:
        f.write("# Demo: %s\n\n%s\n" % (top, text))
    print("\nwritten: %s" % os.path.relpath(out, ROOT))
    for x in failed:
        print("FAILED:", x)
    print("demo:", "PASS" if not failed else "FAIL")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
