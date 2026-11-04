"""The designs of the Option 2 handout (Table 2), and where to find their files.

The Verilog comes from the student pack (given/designs/), linked by make setup
into build/given/. A design is either <name>.v (or .sv) or a folder <name>/
holding several files.
"""
from __future__ import annotations

import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# realpath: yowasp-yosys (WASI) cannot follow the build/given symlink
GIVEN = os.path.realpath(os.environ.get("GIVEN", os.path.join(ROOT, "build", "given")))

# name: (top module, required?, extra read_verilog flags)   -- handout Table 2
DESIGNS = {
    "cpu8":      ("cpu8", True, ""),
    "dsp8":      ("dsp8", True, ""),
    "arlet6502": ("cpu", True, ""),
    "uart_apb":  ("uart_apb_master", True, ""),
    "risc8":     ("cpu", True, ""),
    "fir10":     ("fir10", True, ""),
    "p16c5x":    ("P16C5x", False, ""),
    "pic16":     ("PIC16C5x", False, ""),
    "x18":       ("x18", False, ""),
    "pic1826":   ("cpu", False, "-sv"),
    "xfir":      ("xfir", False, ""),
    "chacha":    ("chacha", False, ""),
    # handout section 3: SPM from Tutorial 4 and the multiplier from Tutorial 2
    "spm":       ("SPM", False, ""),
    "mul":       ("mul", False, ""),
}
# Tutorial files, linked by make setup into build/tut2 and build/tut4.
TUTORIAL = {
    "spm": ("tut4", ["SPM.v", "CSADD.v", "TCMP.v"]),
    "mul": ("tut2", ["mul.v"]),
}
REQUIRED = [d for d, (_, req, _) in DESIGNS.items() if req]
# Every design the flow analyses, maps and ranks on: the required ones plus SPM and mul (section 3).
ANALYSED = REQUIRED + ["spm", "mul"]

# Handout Table 1: area in um2 with Yosys 0.33. Do not edit (AGENTS.md rule 2).
TABLE1 = {  # design: (A usable, A reduced, B usable, B reduced)
    "cpu8":      (4186.5, 4186.5, 4367.9, 4359.2),
    "dsp8":      (5928.2, 5928.2, 6217.2, 6214.7),
    "arlet6502": (9654.3, 9701.8, 9954.5, 9995.8),
    "uart_apb":  (12948.7, 12948.7, 13180.1, 13180.1),
    "risc8":     (28265.9, 28263.4, 27501.4, 27511.4),
    "fir10":     (25968.7, 25968.7, 29055.4, 29055.4),
}

SCRIPTS = {
    "A": "+strash;dch,-f;amap;topo",
    "B": "+strash;&get,-n;&dch,-f;&nf,-R,1000;&put",
}


def files(name: str) -> list[str]:
    """Verilog files of a design."""
    if name in TUTORIAL:
        tut, names = TUTORIAL[name]
        d = os.path.realpath(os.path.join(ROOT, "build", tut))
        fs = [os.path.join(d, f) for f in names]
        missing = [f for f in fs if not os.path.exists(f)]
        if missing:
            raise FileNotFoundError("%s not found (run make setup TUT2=... TUT4=...)" % missing)
        return fs
    base = os.path.join(GIVEN, "designs")
    for ext in (".v", ".sv"):
        p = os.path.join(base, name + ext)
        if os.path.exists(p):
            return [p]
    d = os.path.join(base, name)
    if os.path.isdir(d):
        fs = sorted(glob.glob(os.path.join(d, "**", "*.v"), recursive=True)
                    + glob.glob(os.path.join(d, "**", "*.sv"), recursive=True))
        if fs:
            return fs
    raise FileNotFoundError("design %s not found under %s (run make setup PACK=...)" % (name, base))
