"""Parse Boolean expressions (Liberty `function` strings and request expressions).

Operators, from strongest to weakest binding:
    !x   x'          NOT  (prefix ! or Liberty's postfix ')
    &  *  (space)    AND  (Liberty allows a space as AND: "A B")
    ^                XOR
    |  +             OR
Parentheses group; 0 and 1 are constants. This is C's order for & ^ |.

The expression is evaluated on whole truth tables at once: each input name is
given an integer table (for example A = 0xAAAA) and the operators act bitwise,
so one evaluation gives every row of the truth table.
"""
from __future__ import annotations

import re

_TOK = re.compile(r"\s*(?:([A-Za-z_][A-Za-z0-9_\[\]]*)|([01])|(.))")


def tokenize(s: str) -> list[str]:
    toks = []
    for name, const, op in _TOK.findall(s):
        if name:
            toks.append(name)
        elif const:
            toks.append(const)
        elif op.strip():
            toks.append(op)
    return toks


class Expr:
    """A parsed expression: a small tree of tuples.

    ("var", name) | ("const", 0/1) | ("not", e) | (op, e1, e2) with op in & ^ |
    """

    def __init__(self, text: str):
        self.text = text
        self.toks = tokenize(text)
        self.i = 0
        self.tree = self._or()
        if self.i != len(self.toks):
            raise ValueError("unexpected %r in %r" % (self.toks[self.i], text))

    # recursive descent, one level per precedence
    def _peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def _or(self):
        e = self._xor()
        while self._peek() in ("|", "+"):
            self.i += 1
            e = ("|", e, self._xor())
        return e

    def _xor(self):
        e = self._and()
        while self._peek() == "^":
            self.i += 1
            e = ("^", e, self._and())
        return e

    def _and(self):
        e = self._not()
        while True:
            p = self._peek()
            if p in ("&", "*"):
                self.i += 1
                e = ("&", e, self._not())
            elif p is not None and (p == "(" or p == "!" or p not in "|+^)&*'"):
                e = ("&", e, self._not())          # juxtaposition = AND
            else:
                return e

    def _not(self):
        if self._peek() == "!":
            self.i += 1
            return ("not", self._not())
        e = self._atom()
        while self._peek() == "'":
            self.i += 1
            e = ("not", e)
        return e

    def _atom(self):
        t = self._peek()
        if t is None:
            raise ValueError("expression ends early: %r" % self.text)
        self.i += 1
        if t == "(":
            e = self._or()
            if self._peek() != ")":
                raise ValueError("missing ) in %r" % self.text)
            self.i += 1
            return e
        if t in ("0", "1"):
            return ("const", int(t))
        if re.match(r"[A-Za-z_]", t):
            return ("var", t)
        raise ValueError("unexpected %r in %r" % (t, self.text))

    def names(self) -> list[str]:
        """Input names in order of first appearance."""
        out = []

        def walk(e):
            if e[0] == "var":
                if e[1] not in out:
                    out.append(e[1])
            elif e[0] == "not":
                walk(e[1])
            elif e[0] != "const":
                walk(e[1])
                walk(e[2])
        walk(self.tree)
        return out

    def eval(self, env: dict[str, int], mask: int = 0xFFFF) -> int:
        """Evaluate with every name bound to an integer table."""
        def ev(e):
            k = e[0]
            if k == "var":
                return env[e[1]]
            if k == "const":
                return mask if e[1] else 0
            if k == "not":
                return ev(e[1]) ^ mask
            a, b = ev(e[1]), ev(e[2])
            return a & b if k == "&" else (a | b if k == "|" else a ^ b)
        return ev(self.tree) & mask

    def compile(self, inputs: list[str]):
        """A fast Python function f(*tables) for the given input order."""
        def py(e):
            k = e[0]
            if k == "var":
                return "v%d" % inputs.index(e[1])
            if k == "const":
                return "M" if e[1] else "0"
            if k == "not":
                return "(%s ^ M)" % py(e[1])
            return "(%s %s %s)" % (py(e[1]), k, py(e[2]))
        args = ", ".join("v%d" % i for i in range(len(inputs)))
        src = "lambda %s: (%s) & M" % (args, py(self.tree))
        return eval(src, {"M": 0xFFFF})


def truth_table(text: str, inputs: list[str]) -> int:
    """16-bit table of `text`, input k of `inputs` taking VARS[k]."""
    from tt import VARS
    if len(inputs) > 4:
        raise ValueError("more than 4 inputs")
    e = Expr(text)
    unknown = set(e.names()) - set(inputs)
    if unknown:
        raise ValueError("names not in inputs: %s" % sorted(unknown))
    return e.eval({n: VARS[i] for i, n in enumerate(inputs)})
