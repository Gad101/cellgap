"""Liberty timing_sense of each input of a cell, from its truth table.

For input k: raise it from 0 to 1 with the other inputs fixed, for every
combination of the other inputs, and see which way the output moves.
  only ever falls -> negative_unate      (e.g. both inputs of nand2)
  only ever rises -> positive_unate      (e.g. both inputs of and2)
  both            -> non_unate           (e.g. both inputs of xor2)
Truth tables follow overview Appendix A: bit i is Y for the input combination
in which input k equals bit k of i.
"""
from __future__ import annotations


def timing_sense(tt: int, n: int, k: int) -> str:
    """timing_sense of input k of an n-input function with truth table tt."""
    rises = falls = False
    for i in range(1 << n):
        if i >> k & 1:
            continue                       # visit each pair once, from the row with input k = 0
        y0 = tt >> i & 1                   # output with input k = 0
        y1 = tt >> (i | 1 << k) & 1        # same row with input k = 1
        rises |= y1 > y0
        falls |= y1 < y0
    if rises and falls:
        return "non_unate"
    if rises:
        return "positive_unate"
    if falls:
        return "negative_unate"
    raise ValueError("input %d does not affect the output" % k)


def timing_senses(tt: int, n: int) -> list[str]:
    return [timing_sense(tt, n, k) for k in range(n)]
