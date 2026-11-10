"""Worst delay of a mapped netlist with OpenSTA (Option 2 handout, section 7).

    python3 src/worst_delay.py <library.lib> <netlist.v> <top>
One clock of 10 ns on the port that drives the flip-flops' CLK pins (a virtual clock when there is
none), every other input and every output at 0 ns against it, no wire load and no output load.
The worst delay is the data arrival time of the path with the least setup slack (reset recovery
checks, OpenSTA's "asynchronous" path group, are left out): the same
constraints for every library, so only the cells change. The new cells' timing is a placeholder
until real cells replace them (handout section 6), so their delays are placeholders too.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter

STA = os.environ.get("STA", "sta")
CLK_PIN = re.compile(r"\.CLK(?:_N)?\(\s*(\\?\S+?)\s*\)")


def available() -> bool:
    return shutil.which(STA) is not None


def clock_port(netlist: str) -> str | None:
    """The net most flip-flop clock pins connect to, if it is a port of the netlist."""
    text = open(netlist).read()
    nets = Counter(n.lstrip("\\") for n in CLK_PIN.findall(text))
    if not nets:
        return None
    net = nets.most_common(1)[0][0]
    return net if re.search(r"^\s*input\s+(\[[^\]]*\]\s*)?\\?%s\s*;" % re.escape(net), text, re.M) else None


def worst_delay(lib: str, netlist: str, top: str) -> float:
    clk = clock_port(netlist)
    src = "[get_ports {%s}]" % clk if clk else ""
    tcl = f"""read_liberty {lib}
read_verilog {netlist}
link_design {top}
create_clock -name clk -period 10 {src}
set_input_delay 0 -clock clk [all_inputs -no_clocks]
set_output_delay 0 -clock clk [all_outputs]
report_checks -path_delay max -digits 4
"""
    with tempfile.NamedTemporaryFile("w", suffix=".tcl", delete=False) as f:
        f.write(tcl)
    try:
        r = subprocess.run([STA, "-no_init", "-no_splash", "-exit", f.name], capture_output=True, text=True)
    finally:
        os.remove(f.name)
    # one path per path group; the "asynchronous" group (reset recovery/removal) is not logic delay
    arr = [float(t) for g, t in re.findall(r"^Path Group: (\S+).*?^\s*(-?[0-9.]+)\s+data arrival time",
                                           r.stdout, re.M | re.S) if g != "asynchronous"]
    if not arr:
        raise RuntimeError("OpenSTA gave no arrival time for %s:\n%s" % (netlist, (r.stdout + r.stderr)[-1500:]))
    return max(arr)


def measure(lib: str, netlists: dict, label: str) -> dict:
    """{(design, label, script): worst delay in ns} for {(design, script): netlist}."""
    from designs import DESIGNS
    return {(d, label, s): "%.4f" % worst_delay(lib, net, DESIGNS[d][0]) for (d, s), net in netlists.items()}


def write_csv(path: str, dl: dict) -> None:
    with open(path, "w") as f:
        f.write("design,library,script,worst_delay_ns\n")
        for (d, label, s), v in sorted(dl.items()):
            f.write("%s,%s,%s,%s\n" % (d, label, s, v))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    print("%.4f ns" % worst_delay(*sys.argv[1:]))
