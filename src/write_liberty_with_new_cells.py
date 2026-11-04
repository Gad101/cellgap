"""Step 8, part 2: the Liberty file of section 6 (Option 2 handout).

    python3 src/write_liberty_with_new_cells.py [--requests results/cell_requests] [--out libs/hd_reduced_plus_new_cells_est.lib]
Copies the student pack's hd_reduced.lib and adds one cell per request inside
its library group, in the format of given/examples/new_cell_example.lib:
area (the request's estimate), input pins with capacitance, the output with
its function and one timing arc per input. Capacitance and timing are the
example's placeholders (section 6 allows them; both scripts aim at area);
timing_sense comes from src/timing_sense_calc.py.

Checks, either failure exits 1:
  - every new cell's function, read back from the file, gives its request's truth table;
  - Yosys read_liberty -lib prints "Imported N cell types" with N = 189 + new cells.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import liberty                                 # noqa: E402
from boolexpr import truth_table               # noqa: E402
from designs import GIVEN, ROOT                # noqa: E402
from timing_sense_calc import timing_senses    # noqa: E402

YOSYS = os.environ.get("YOSYS", "yosys")
BASE = os.path.join(GIVEN, "hd_reduced.lib")
BASE_CELLS = 189                               # handout section 2

# Placeholders copied from given/examples/new_cell_example.lib.
CAPACITANCE = "0.0024"
TIMING = ('cell_rise (scalar) { values ("0.10"); }', 'cell_fall (scalar) { values ("0.08"); }',
          'rise_transition (scalar) { values ("0.10"); }', 'fall_transition (scalar) { values ("0.08"); }')


def read(path: str) -> str:
    with open(path) as f:
        return f.read()


def load_json(path: str):
    with open(path) as f:
        return json.load(f)


def cell_text(req: dict) -> str:
    ins, n = req["inputs"], len(req["inputs"])
    senses = timing_senses(int(req["truth_table"], 16), n)
    out = ['  cell ("%s") {' % req["name"], "    area : %s;" % req["estimated_area_um2"]]
    out += ['    pin ("%s") { direction : "input"; capacitance : %s; }' % (p, CAPACITANCE) for p in ins]
    out += ['    pin ("%s") {' % req["output"], '      direction : "output";',
            '      function : "%s";' % req["expression"]]
    for p, s in zip(ins, senses):
        out += ["      timing () {", '        related_pin : "%s";' % p, '        timing_sense : "%s";' % s]
        out += ["        " + t for t in TIMING]
        out += ["      }"]
    out += ["    }", "  }"]
    return "\n".join(out) + "\n"


def write(reqs: list[dict], base: str, out: str) -> None:
    text = read(base).rstrip()
    if not text.endswith("}"):
        raise SystemExit("%s does not end with the library's closing brace" % base)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(text[:-1].rstrip() + "\n\n  /* new cells, estimated areas (src/write_liberty_with_new_cells.py) */\n")
        f.writelines(cell_text(r) for r in reqs)
        f.write("}\n")


def check_functions(reqs: list[dict], path: str) -> list[str]:
    """Problems found when the new cells are read back from the written file."""
    got = {c["name"]: c for c in liberty.cells(path)}
    bad = []
    for r in reqs:
        c = got.get(r["name"])
        if c is None:
            bad.append("%s: missing" % r["name"])
            continue
        n = len(r["inputs"])
        try:
            t = truth_table(c["outputs"][0]["function"], c["inputs"]) & ((1 << (1 << n)) - 1)
        except ValueError as e:              # unreadable function, or a name that is not a pin
            bad.append("%s: %s" % (r["name"], e))
            continue
        if c["inputs"] != r["inputs"] or t != int(r["truth_table"], 16):
            bad.append("%s: function or pins differ from the request" % r["name"])
    return bad


def yosys_cell_count(path: str) -> int:
    """N of Yosys's "Imported N cell types"; raises if Yosys rejects the file."""
    r = subprocess.run([YOSYS, "-p", "read_liberty -lib %s" % path], capture_output=True, text=True)
    m = re.findall(r"Imported (\d+) cell types", r.stdout)
    if r.returncode != 0 or not m:
        raise RuntimeError("Yosys rejected %s:\n%s" % (path, (r.stdout + r.stderr)[-1500:]))
    return int(m[-1])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--requests", default=os.path.join(ROOT, "results", "cell_requests"))
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--out", default=os.path.join(ROOT, "libs", "hd_reduced_plus_new_cells_est.lib"))
    a = ap.parse_args(argv)
    reqs = sorted((load_json(p) for p in glob.glob(os.path.join(a.requests, "*.json"))),
                  key=lambda r: r["request_id"])
    write(reqs, a.base, a.out)
    bad = check_functions(reqs, a.out)
    for b in bad:
        print("FUNCTION CHECK FAILED", b)
    want = BASE_CELLS + len(reqs)
    got = yosys_cell_count(a.out)
    print("%s: %d new cells; Yosys imported %d cell types (want %d + %d = %d)"
          % (os.path.relpath(a.out, ROOT), len(reqs), got, BASE_CELLS, len(reqs), want))
    return 0 if not bad and got == want else 1


if __name__ == "__main__":
    sys.exit(main())
