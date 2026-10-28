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
}
REQUIRED = [d for d, (_, req, _) in DESIGNS.items() if req]

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
