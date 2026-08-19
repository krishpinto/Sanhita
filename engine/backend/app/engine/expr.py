"""
Tiny JSON-Logic-style expression DSL.

Every gate condition, skip rule, derived tag, and terminal-table row in every
protocol is one of these expressions. Hand-rolled (not `eval`, not an external
dependency) because a bug here is a clinical-safety bug, not a UI bug.

Grammar (all nodes are plain JSON-compatible values):
    {"var": "dotted.path"}                  -> variable lookup
    {"==": [a, b]}  {"!=": [a, b]}
    {"in": [a, b]}                          -> a in b
    {">": [a, b]}  {"<": [a, b]}  {">=": [a, b]}  {"<=": [a, b]}
    {"and": [expr, ...]}  {"or": [expr, ...]}
    {"not": [expr]}
    {"count_true": [expr, ...]}              -> integer count of truthy sub-expressions
                                                 (e.g. Jones criteria major/minor counting)
    any other JSON value (str/number/bool/null/list) -> itself, a literal

`evaluate` assumes every referenced variable is present in the namespace and
raises if not. Callers that might be asked to evaluate before all inputs are
known (skip_when, fire_when, terminal-table rows) must check
`is_determinable` first — an expression referencing an unanswered field is
"not yet decidable", not false.

Determinability is short-circuit-aware: `{"or": [{"var": "a"}, {"var": "b"}]}`
is determinable as soon as `a` is true, even if `b` doesn't exist yet in the
namespace -- matters for fields like the valve-assessment skip rule, where
one branch of an `or` legitimately depends on a field that was itself
skipped (and so will never appear), while the other branch already settles
the question.
"""

from __future__ import annotations

from typing import Any

MISSING = object()

_BOOL_OPS = {"and", "or", "not"}
_COMPARATORS: dict[str, Any] = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "in": lambda a, b: a in b if b is not None else False,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
}
_LIST_OPS = {"count_true"}
_KNOWN_OPS = {"var"} | _BOOL_OPS | set(_COMPARATORS) | _LIST_OPS


def get_var(namespace: dict, path: str) -> Any:
    """Dotted-path lookup into a nested dict namespace. Returns MISSING if any
    segment of the path isn't present (rather than raising) -- callers decide
    what that means."""
    cur: Any = namespace
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return MISSING
    return cur


def _is_op_node(node: Any) -> bool:
    return isinstance(node, dict) and len(node) == 1 and next(iter(node)) in _KNOWN_OPS


def extract_var_paths(node: Any) -> set[str]:
    """Every {"var": "..."} path referenced anywhere inside `node`."""
    paths: set[str] = set()

    def walk(n: Any) -> None:
        if _is_op_node(n):
            (op, args) = next(iter(n.items()))
            if op == "var":
                paths.add(args)
                return
            for a in args if isinstance(args, list) else [args]:
                walk(a)
        elif isinstance(n, list):
            for item in n:
                walk(item)

    walk(node)
    return paths


def try_evaluate(node: Any, namespace: dict) -> Any:
    """Resolve `node` against `namespace`, short-circuit-aware: an `and` with
    a determinably-false branch is `False` even if a later branch references
    a variable that isn't present; an `or` with a determinably-true branch is
    `True` the same way. Returns MISSING if the result genuinely can't be
    determined yet from what's in the namespace."""
    if _is_op_node(node):
        (op, args) = next(iter(node.items()))

        if op == "var":
            return get_var(namespace, args)

        if op == "and":
            saw_missing = False
            for a in args:
                v = try_evaluate(a, namespace)
                if v is MISSING:
                    saw_missing = True
                    continue
                if not bool(v):
                    return False
            return MISSING if saw_missing else True

        if op == "or":
            saw_missing = False
            for a in args:
                v = try_evaluate(a, namespace)
                if v is MISSING:
                    saw_missing = True
                    continue
                if bool(v):
                    return True
            return MISSING if saw_missing else False

        if op == "not":
            inner = args[0] if isinstance(args, list) else args
            v = try_evaluate(inner, namespace)
            return MISSING if v is MISSING else not bool(v)

        if op == "count_true":
            # No meaningful partial count -- every term must be known.
            total = 0
            for a in args:
                v = try_evaluate(a, namespace)
                if v is MISSING:
                    return MISSING
                if bool(v):
                    total += 1
            return total

        if op in _COMPARATORS:
            a, b = args
            va = try_evaluate(a, namespace)
            vb = try_evaluate(b, namespace)
            if va is MISSING or vb is MISSING:
                return MISSING
            return _COMPARATORS[op](va, vb)

        raise ValueError(f"Unknown operator: {op}")  # pragma: no cover — guarded by _KNOWN_OPS

    if isinstance(node, list):
        values = [try_evaluate(item, namespace) for item in node]
        return MISSING if any(v is MISSING for v in values) else values

    return node  # literal: str, number, bool, None


def is_determinable(node: Any, namespace: dict) -> bool:
    """True iff `node` can be resolved right now -- either every variable it
    touches is present, or a short-circuit (a false `and` branch, a true `or`
    branch) already settles it regardless of the rest."""
    return try_evaluate(node, namespace) is not MISSING


def evaluate(node: Any, namespace: dict) -> Any:
    """Resolve `node` against `namespace`. Works for both boolean expressions
    (and/or/not/comparators) and plain literals/lists -- callers that need a
    bool should wrap the top-level call in bool(), though every boolean
    operator here already returns a real bool. Raises if the result isn't yet
    determinable -- callers that might be asked to evaluate early should check
    `is_determinable` first."""
    result = try_evaluate(node, namespace)
    if result is MISSING:
        raise KeyError(
            f"Expression not yet determinable from current namespace: {node!r}. "
            "Caller should have checked is_determinable() before evaluating."
        )
    return result
