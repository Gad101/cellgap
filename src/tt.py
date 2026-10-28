"""Truth tables of functions of up to 4 inputs, stored as 16-bit integers.

Convention (overview, Appendix A): bit i of the table is the output Y for the
input combination in which input k equals bit k of i. Input A (index 0) is the
least significant input. So the four inputs themselves have these tables:

    A = 0xAAAA   (1 in every odd row)
    B = 0xCCCC
    C = 0xF0F0
    D = 0xFF00

With this, AND is `&`, OR is `|`, XOR is `^` and NOT is `^ 0xFFFF` on the
whole table at once: one Python operation computes all 16 rows.

A function of fewer than 4 inputs is stored the same way; the unused inputs
simply do not change the table ("don't-care" inputs).

Classes. Two tables are in the same class when one becomes the other by
  P   : reordering the inputs                              (Table 4 counts)
  PO  : reordering the inputs and/or inverting the output  (handout step 3)
  NPN : the above plus inverting any inputs                (counted, not used)
The class is named by its smallest table ("canonical form"). There are only
65,536 tables, so we compute the canonical form of every table once (with
numpy, a few seconds) and afterwards a class lookup is one array index.
"""
from __future__ import annotations

import itertools
import os
from functools import lru_cache

import numpy as np

MASK = 0xFFFF
VARS = (0xAAAA, 0xCCCC, 0xF0F0, 0xFF00)
NAMES = "ABCD"
PERMS = list(itertools.permutations(range(4)))  # 24 input orders

_BUILD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build")


def bit(tt: int, row: int) -> int:
    """Output of the function for input combination `row` (0..15)."""
    return (tt >> row) & 1


def depends_on(tt: int, k: int) -> bool:
    """True if changing input k can change the output."""
    s = 1 << k                      # distance between rows that differ only in input k
    hi = (tt & VARS[k]) >> s        # rows where input k = 1, moved onto their partner rows
    lo = tt & ~VARS[k] & MASK       # rows where input k = 0
    return hi != lo


def support(tt: int) -> tuple[int, ...]:
    """The inputs the function really depends on."""
    return tuple(k for k in range(4) if depends_on(tt, k))


def flip_input(tt: int, k: int) -> int:
    """Table of f with input k inverted: g(..x_k..) = f(..!x_k..)."""
    s = 1 << k
    v = VARS[k]
    return (((tt & v) >> s) | ((tt & ~v & MASK) << s)) & MASK


def is_negative_unate(tt: int, k: int) -> bool:
    """Raising input k from 0 to 1 never raises the output (f(x_k=1) <= f(x_k=0))."""
    s = 1 << k
    hi = (tt & VARS[k]) >> s
    lo = tt & ~VARS[k] & MASK
    return hi & ~lo == 0


def is_positive_unate(tt: int, k: int) -> bool:
    s = 1 << k
    hi = (tt & VARS[k]) >> s
    lo = tt & ~VARS[k] & MASK
    return lo & ~hi == 0


def row_map(perm=(0, 1, 2, 3), neg: int = 0) -> list[int]:
    """For a transform of the inputs, the source row of every destination row.

    New input k is old input perm[k], inverted if bit k of `neg` is set.
    g(row m) = f(row idx[m]).
    """
    idx = []
    for m in range(16):
        old = 0
        for k in range(4):
            b = ((m >> k) & 1) ^ ((neg >> k) & 1)
            old |= b << perm[k]
        idx.append(old)
    return idx


def transform(tt: int, perm=(0, 1, 2, 3), neg: int = 0, out_neg: bool = False) -> int:
    """Apply an input permutation / input inversions / output inversion to one table."""
    idx = row_map(perm, neg)
    g = 0
    for m in range(16):
        g |= bit(tt, idx[m]) << m
    return g ^ MASK if out_neg else g


def _all_bits() -> np.ndarray:
    t = np.arange(65536, dtype=np.uint32)
    return ((t[:, None] >> np.arange(16, dtype=np.uint32)) & 1).astype(np.uint8)


def _pack(bits: np.ndarray) -> np.ndarray:
    weights = (1 << np.arange(16, dtype=np.uint32)).astype(np.uint32)
    return (bits.astype(np.uint32) * weights).sum(axis=1).astype(np.uint32)


def _compute_canon() -> dict[str, np.ndarray]:
    bits = _all_bits()
    allt = np.arange(65536, dtype=np.uint32)
    canon_p = allt.copy()
    canon_po = np.minimum(allt, allt ^ MASK)
    canon_npn = canon_po.copy()
    for perm in PERMS:
        g = _pack(bits[:, row_map(perm, 0)])
        canon_p = np.minimum(canon_p, g)
        canon_po = np.minimum(canon_po, np.minimum(g, g ^ MASK))
        for neg in range(16):
            h = _pack(bits[:, row_map(perm, neg)])
            canon_npn = np.minimum(canon_npn, np.minimum(h, h ^ MASK))
    return {"P": canon_p.astype(np.uint16), "PO": canon_po.astype(np.uint16),
            "NPN": canon_npn.astype(np.uint16)}


@lru_cache(maxsize=None)
def canon_tables() -> dict[str, np.ndarray]:
    """Canonical form of every 16-bit table, cached in build/canon.npz."""
    path = os.path.join(_BUILD, "canon.npz")
    if os.path.exists(path):
        data = np.load(path)
        return {k: data[k] for k in ("P", "PO", "NPN")}
    tabs = _compute_canon()
    os.makedirs(_BUILD, exist_ok=True)
    np.savez(path, **tabs)
    return tabs


def canon(tt: int, kind: str = "PO") -> int:
    """Class name (smallest equivalent table) of `tt` under P, PO or NPN."""
    return int(canon_tables()[kind][tt])


def to_hex(tt: int, n: int = 4) -> str:
    """Hex string; for n < 4 inputs only the first 2**n rows are printed."""
    rows = 1 << n
    return "0x%0*X" % (max(1, rows // 4), tt & ((1 << rows) - 1))


def sop(tt: int) -> str:
    """A readable (not minimal) sum of products over the support, for reports."""
    sup = support(tt)
    if tt == 0:
        return "0"
    if tt == MASK:
        return "1"
    terms = set()
    for m in range(16):
        if bit(tt, m):
            terms.add(tuple((k, (m >> k) & 1) for k in sup))
    out = []
    for t in sorted(terms):
        out.append("&".join(NAMES[k] if v else "!" + NAMES[k] for k, v in t) or "1")
    return " | ".join("(%s)" % s for s in out)
