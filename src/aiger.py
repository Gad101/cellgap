"""Read an and-inverter graph (AIG) in AIGER format, ASCII (.aag) or binary (.aig).

An AIG has only 2-input AND gates; inverters are a flag on the wires.
AIGER numbers every node with a variable v; a literal is 2*v, or 2*v + 1 for
the inverted wire. Variable 0 is the constant 0 (literal 1 = constant 1).

    header : aag M I L O A      M = max variable, I inputs, L latches,
                                O outputs, A AND gates
    inputs : one literal each
    latches: "lit next [init]"  (a latch output is a leaf for cuts, like an input)
    outputs: one literal each
    ands   : "lhs rhs0 rhs1"    node lhs = rhs0 AND rhs1
"""
from __future__ import annotations


class AIG:
    def __init__(self):
        self.M = self.I = self.L = self.O = self.A = 0
        self.inputs: list[int] = []        # variables
        self.latches: list[tuple[int, int]] = []   # (variable, next literal)
        self.outputs: list[int] = []       # literals
        self.ands: dict[int, tuple[int, int]] = {}  # variable -> (lit0, lit1)
        self.symbols: dict[str, str] = {}

    @property
    def leaves(self) -> set[int]:
        """Variables a cut may stop at: inputs, latch outputs and the constant."""
        return set(self.inputs) | {v for v, _ in self.latches} | {0}

    def topo_ands(self) -> list[int]:
        """AND variables, each after both of its fanins."""
        order, state = [], {}
        for root in self.ands:
            stack = [(root, False)]
            while stack:
                v, done = stack.pop()
                if v not in self.ands or state.get(v) == 2:
                    continue
                if done:
                    state[v] = 2
                    order.append(v)
                    continue
                if state.get(v) == 1:
                    raise ValueError("combinational loop at variable %d" % v)
                state[v] = 1
                stack.append((v, True))
                for lit in self.ands[v]:
                    stack.append((lit >> 1, False))
        return order


def _read_binary_uint(data: bytes, pos: int) -> tuple[int, int]:
    x, shift = 0, 0
    while True:
        b = data[pos]
        pos += 1
        x |= (b & 0x7F) << shift
        if not b & 0x80:
            return x, pos
        shift += 7


def read(path: str) -> AIG:
    with open(path, "rb") as f:
        data = f.read()
    nl = data.index(b"\n")
    head = data[:nl].split()
    fmt = head[0].decode()
    if fmt not in ("aag", "aig"):
        raise ValueError("%s: not an AIGER file" % path)
    g = AIG()
    g.M, g.I, g.L, g.O, g.A = (int(x) for x in head[1:6])
    if len(head) > 6 and any(int(x) for x in head[6:]):
        raise ValueError("AIGER 1.9 bad/constraint/justice/fairness sections are not supported")
    if fmt == "aag":
        lines = data[nl + 1:].decode().split("\n")
        i = 0
        for _ in range(g.I):
            g.inputs.append(int(lines[i].split()[0]) >> 1)
            i += 1
        for _ in range(g.L):
            p = lines[i].split()
            g.latches.append((int(p[0]) >> 1, int(p[1])))
            i += 1
        for _ in range(g.O):
            g.outputs.append(int(lines[i].split()[0]))
            i += 1
        for _ in range(g.A):
            lhs, r0, r1 = (int(x) for x in lines[i].split()[:3])
            g.ands[lhs >> 1] = (r0, r1)
            i += 1
        rest = lines[i:]
    else:
        # binary: inputs are 1..I, latches I+1..I+L, ANDs follow, deltas encoded
        text_end = nl + 1
        g.inputs = list(range(1, g.I + 1))
        pos = text_end
        for k in range(g.L):
            end = data.index(b"\n", pos)
            p = data[pos:end].split()
            g.latches.append((g.I + 1 + k, int(p[0])))
            pos = end + 1
        for _ in range(g.O):
            end = data.index(b"\n", pos)
            g.outputs.append(int(data[pos:end].split()[0]))
            pos = end + 1
        for k in range(g.A):
            lhs = 2 * (g.I + g.L + 1 + k)
            d0, pos = _read_binary_uint(data, pos)
            d1, pos = _read_binary_uint(data, pos)
            r0 = lhs - d0
            r1 = r0 - d1
            g.ands[lhs >> 1] = (r0, r1)
        rest = data[pos:].decode(errors="replace").split("\n")
    for line in rest:
        if line.startswith("c"):
            break
        if line[:1] in ("i", "l", "o") and " " in line:
            k, name = line.split(" ", 1)
            g.symbols[k] = name
    return g
