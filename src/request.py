"""Cell requests (overview, Appendix A): check that expression and truth table agree.

    python3 src/request.py check <request.json>
The maker refuses a request whose expression and truth_table disagree, or that
has more than 4 inputs. Our tool runs the same check on every request it writes.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from boolexpr import truth_table   # noqa: E402
from tt import to_hex              # noqa: E402


def check(req: dict) -> tuple[bool, str]:
    ins = req["inputs"]
    if len(ins) > 4:
        return False, "unsupported: %d inputs (at most 4)" % len(ins)
    try:
        t = truth_table(req["expression"], ins)
    except ValueError as e:
        return False, "bad expression: %s" % e
    n = len(ins)
    want = int(req["truth_table"], 16)
    got = t & ((1 << (1 << n)) - 1)
    if got != want:
        return False, "expression gives %s, truth_table says %s" % (to_hex(t, n), req["truth_table"])
    return True, "ok"


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "check":
        print(__doc__)
        sys.exit(2)
    ok, why = check(json.load(open(sys.argv[2])))
    print("PASS" if ok else "REFUSED", why)
    sys.exit(0 if ok else 1)
