"""How many transistors one static CMOS stage needs for a function.

One stage computes Y = !F. The pull-down network (PDN) is F built from nMOS:
AND = series, OR = parallel. The pull-up network (PUN) is the dual from pMOS:
AND = parallel, OR = series (Lecture 7-8; Option 1 handout, step 2).
So a single stage exists only when Y is negative unate in every input
(F is then positive unate, i.e. monotone, and has a factored form).

Each literal of the factored form of F is one nMOS and one pMOS, so
    transistors = 2 x literals.
The longest series chain in each network follows the formula tree:
    literal : PDN 1,             PUN 1
    a & b   : PDN a + b,         PUN max(a, b)
    a | b   : PDN max(a, b),     PUN a + b
A cell may have at most 3 transistors in series in either network.

We find, for every monotone function of 4 inputs, the factored forms with the
fewest literals that respect the series limit, by building all formulas
bottom up: formulas with L literals = (formula with i) op (formula with L - i).
There are only 168 monotone functions of 4 inputs, so this is quick.
"""
from __future__ import annotations

from functools import lru_cache

from tt import MASK, VARS, is_negative_unate, support


def _pareto(forms: dict) -> dict:
    """Keep (pdn, pun) series pairs that no other pair beats in both, with one formula each."""
    return {p: e for p, e in forms.items()
            if not any(q != p and q[0] <= p[0] and q[1] <= p[1] for q in forms)}


@lru_cache(maxsize=None)
def formulas(max_lits: int = 8, max_series: int = 3) -> dict[int, dict[int, dict]]:
    """by_lits[L][F] = {(pdn_series, pun_series): formula text} for L-literal forms of F."""
    by_lits = {1: {v: {(1, 1): "ABCD"[k]} for k, v in enumerate(VARS)}}
    for L in range(2, max_lits + 1):
        cur: dict[int, dict] = {}
        for i in range(1, L // 2 + 1):
            for fa, sa in by_lits[i].items():
                for fb, sb in by_lits[L - i].items():
                    for (pa, ua), ea in sa.items():
                        for (pb, ub), eb in sb.items():
                            # AND: nMOS in series, pMOS in parallel
                            pd, pu = pa + pb, max(ua, ub)
                            if pd <= max_series and pu <= max_series:
                                cur.setdefault(fa & fb, {}).setdefault((pd, pu), "(%s & %s)" % (ea, eb))
                            # OR: nMOS in parallel, pMOS in series
                            pd, pu = max(pa, pb), ua + ub
                            if pd <= max_series and pu <= max_series:
                                cur.setdefault(fa | fb, {}).setdefault((pd, pu), "(%s | %s)" % (ea, eb))
        by_lits[L] = {f: _pareto(s) for f, s in cur.items()}
    return by_lits


def series_of(text: str) -> tuple[int, int, int]:
    """(literals, PDN series, PUN series) of a positive formula, computed from its text.

    Independent of `formulas`, so it can check the formulas that search returns.
    """
    from boolexpr import Expr

    def walk(e):
        if e[0] == "var":
            return 1, 1, 1
        if e[0] in ("&", "|"):
            la, pa, ua = walk(e[1])
            lb, pb, ub = walk(e[2])
            if e[0] == "&":
                return la + lb, pa + pb, max(ua, ub)
            return la + lb, max(pa, pb), ua + ub
        raise ValueError("not a positive AND/OR formula: %r" % (text,))
    return walk(Expr(text).tree)


def one_stage_form(y: int, max_series: int = 3, max_lits: int = 8):
    """A smallest pull-down formula F (Y = !F) within the series limit, or None."""
    if not is_one_stage(y):
        return None
    f = y ^ MASK
    table = formulas(max_lits, max_series)
    for L in range(1, max_lits + 1):
        if f in table.get(L, {}):
            pairs = table[L][f]
            best = min(pairs, key=lambda p: (max(p), p))
            return pairs[best]
    return None


def is_one_stage(y: int) -> bool:
    """Y can be one static CMOS stage (no series limit): negative unate in every input."""
    if y in (0, MASK):
        return False
    return all(is_negative_unate(y, k) for k in range(4))


def one_stage_transistors(y: int, max_series: int = 3, max_lits: int = 8):
    """Fewest transistors of one stage computing Y within the series limit, or None."""
    if not is_one_stage(y):
        return None
    f = y ^ MASK
    table = formulas(max_lits, max_series)
    for L in range(1, max_lits + 1):
        if f in table.get(L, {}):
            return 2 * L
    return None


def is_read_once_one_stage(y: int, max_series: int = 3) -> bool:
    """One stage in which every input in the support appears exactly once."""
    n = len(support(y))
    return one_stage_transistors(y, max_series, max_lits=n) == 2 * n
