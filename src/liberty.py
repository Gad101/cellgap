"""A small Liberty reader: enough to get each cell's area, pins and functions.

Liberty is nested groups:   name (args) { attribute : value ; ... group ... }
We read the whole file with one regular expression that recognises four kinds
of token, and keep a stack of open groups. Big timing tables (`values (...)`)
are complex attributes; we skip their contents.

Command line:
    python3 src/liberty.py <file.lib> [out.json]
writes one JSON record per cell (name, area, inputs, outputs with functions,
and whether the cell is sequential or tri-state).
"""
from __future__ import annotations

import json
import re
import sys

_TOKEN = re.compile(
    r"""\s*(?:
      (?P<comment>/\*.*?\*/)                                  # /* comment */
    | (?P<cont>\\\r?\n)                                       # line continuation
    | (?P<gname>[A-Za-z_][\w.]*)\s*\((?P<gargs>[^)]*)\)\s*(?P<gend>\{|;)  # group { or complex attr ;
    | (?P<aname>[A-Za-z_][\w.]*)\s*:\s*(?P<aval>"(?:[^"\\]|\\.)*"|[^;{}]*?)\s*;   # simple attr
    | (?P<close>\})
    )""",
    re.S | re.X,
)


class Group:
    __slots__ = ("kind", "args", "attrs", "children")

    def __init__(self, kind, args):
        self.kind = kind
        self.args = args
        self.attrs = {}
        self.children = []

    def find(self, kind):
        return [c for c in self.children if c.kind == kind]

    @property
    def name(self):
        return self.args.strip().strip('"')


def parse(text: str) -> Group:
    root = Group("<root>", "")
    stack = [root]
    pos, n = 0, len(text)
    while pos < n:
        m = _TOKEN.match(text, pos)
        if not m:
            if text[pos:].strip() == "":
                break
            line = text.count("\n", 0, pos) + 1
            raise ValueError("Liberty syntax error near line %d: %r" % (line, text[pos:pos + 60]))
        pos = m.end()
        if m.group("gname"):
            if m.group("gend") == "{":
                g = Group(m.group("gname"), m.group("gargs"))
                stack[-1].children.append(g)
                stack.append(g)
            # complex attribute (values(...); define(...);) is ignored
        elif m.group("aname"):
            v = m.group("aval").strip()
            if v.startswith('"'):
                v = v[1:-1]
            stack[-1].attrs[m.group("aname")] = v
        elif m.group("close"):
            stack.pop()
            if not stack:
                raise ValueError("unbalanced }")
    if len(stack) != 1:
        raise ValueError("unclosed group: %s" % stack[-1].kind)
    return root


def cells(path: str) -> list[dict]:
    """One record per cell of the (first) library group in `path`."""
    with open(path) as f:
        root = parse(f.read())
    lib = root.find("library")[0]
    out = []
    for c in lib.find("cell"):
        pins = c.find("pin")
        rec = {
            "name": c.name,
            "area": float(c.attrs.get("area", "nan")),
            "inputs": [p.name for p in pins if p.attrs.get("direction") == "input"],
            "outputs": [
                {"name": p.name, "function": p.attrs.get("function"),
                 "three_state": "three_state" in p.attrs}
                for p in pins if p.attrs.get("direction") == "output"
            ],
            "sequential": any(c.find(k) for k in ("ff", "latch", "statetable", "ff_bank", "latch_bank")),
            "dont_use": c.attrs.get("dont_use", "false") == "true",
        }
        out.append(rec)
    return out


def single_output_combinational(recs: list[dict]) -> list[dict]:
    """Cells that compute one output from their inputs: what step 5 compares with."""
    keep = []
    for r in recs:
        outs = [o for o in r["outputs"] if o["function"]]
        if r["sequential"] or len(r["outputs"]) != 1 or len(outs) != 1:
            continue
        if outs[0]["three_state"]:
            continue
        keep.append(r)
    return keep


if __name__ == "__main__":
    recs = cells(sys.argv[1])
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w") as f:
            json.dump(recs, f, indent=1)
    print("%d cells, %d single-output combinational" % (len(recs), len(single_output_combinational(recs))))
