"""Exact recursion cost of pyrigi's plane realization counting, under a given or the optimal biedge selection.

The recursion is re-implemented here with pyrigi's own helpers, counting the same work
`measure_realization_counting` counts: recursion calls, steps of the split enumeration
and pseudo-Laman checks. `PolicyEvaluator` reproduces a selector's counts exactly;
`Oracle` picks the biedge minimising the total cost of the subtree in every call.
Splits are enumerated as in the bonimart/PyRigi fork (`greedy_canonical`) unless
another enumerator from `split_order` is passed; `original` is upstream pyrigi's order.

Subproblems are memoised on a relabelled copy of the bigraph by default. That key keeps the
biedge order, which is exact for any selector and enumerator. When both depend only on the
isomorphism class (the oracle with `greedy_canonical`), pass `key_of=canonical.canonical_key`
to share subproblems across orderings.
"""

import typing
from dataclasses import dataclass

import networkx as nx
import pyrigi.graph._rigidity.realization_counting as rc

from realization_counting.bigraph import Bigraph
from realization_counting.edge_selection import BiedgeSelector
from realization_counting.split_order import ENUMERATORS, SplitEnumerator

Key = tuple[bool, tuple]

# ms per unit fitted on graphs with at most 9 vertices (first selection, R^2 = 0.989)
DEFAULT_WEIGHTS = (0.0, 1.0, 4.5)


@dataclass(frozen=True, slots=True)
class Cost:
    calls: int = 0
    split_steps: int = 0
    laman_checks: int = 0

    def __add__(self, other: Cost) -> Cost:
        return Cost(
            self.calls + other.calls,
            self.split_steps + other.split_steps,
            self.laman_checks + other.laman_checks,
        )

    def scalar(self, weights: tuple[float, float, float] = DEFAULT_WEIGHTS) -> float:
        return (
            weights[0] * self.calls
            + weights[1] * self.split_steps
            + weights[2] * self.laman_checks
        )


@dataclass(frozen=True, slots=True)
class Expansion:
    """One recursion call on a bigraph whose biedge 0 is selected, without its subcalls.

    The result is `factor * value(first) + value(second) + sum(value(M) * value(N) for M, N in splits)`,
    `value(N)` is only computed when `value(M) != 0`.
    """

    local: Cost
    factor: int
    first: Bigraph
    second: Bigraph | None
    splits: list[tuple[Bigraph, Bigraph]]


def key(bigraph: Bigraph, first: bool = False) -> Key:
    """Bigraph with vertices of each side relabelled in order of appearance."""
    maps: tuple[dict, dict] = ({}, {})
    return first, tuple(
        tuple(tuple(maps[s].setdefault(v, len(maps[s])) for v in be[s]) for s in (0, 1))
        for be in bigraph
    )


def select(bigraph: Bigraph, i: int) -> Bigraph:
    """Move biedge `i` to the front, as `measure.select_first_with` does."""
    return [bigraph[i], *bigraph[:i], *bigraph[i + 1 :]]


def distinct_choices(bigraph: Bigraph) -> list[int]:
    """Indices of the first occurrence of each biedge, selecting equal biedges gives the same bigraph."""
    seen = set()
    choices = []
    for i, be in enumerate(bigraph):
        t = (tuple(be[0]), tuple(be[1]))
        if t not in seen:
            seen.add(t)
            choices.append(i)
    return choices


def is_terminal(bigraph: Bigraph) -> bool:
    return rc._biedges_have_loop(bigraph) or len(bigraph) == 1


def terminal_value(bigraph: Bigraph) -> int:
    return 0 if rc._biedges_have_loop(bigraph) else 1


def expand(
    bigraph: Bigraph,
    first: bool = False,
    splits_of: SplitEnumerator = ENUMERATORS["greedy_canonical"],
) -> Expansion:
    """Mirror of `_number_of_plane_realizations_min_rigid_dim_2_rec` for a non-terminal bigraph."""
    selected = bigraph[0]
    steps = 0

    def check(M: list, N: list) -> bool:
        nonlocal steps
        steps += 1
        return rc._has_loop_after_split(M, N)

    raw_splits = list(splits_of(bigraph, check))

    laman_checks = 0
    splits = []
    for M, N in raw_splits:
        if len(M) == 1 or len(N) == 1:
            continue
        big_M = rc._bigraph_contract_delete(bigraph, M)
        big_N = rc._bigraph_delete_contract(bigraph, N)
        laman_checks += 1
        if not rc._bigraph_is_pseudo_laman(big_N):
            continue
        laman_checks += 1
        if rc._bigraph_is_pseudo_laman(big_M):
            splits.append((big_M, big_N))

    return Expansion(
        local=Cost(1, steps, laman_checks),
        factor=2 if first else 1,
        first=rc._bigraph_contract_delete(bigraph, [selected]),
        second=None if first else rc._bigraph_delete_contract(bigraph, [selected]),
        splits=splits,
    )


class _Solver:
    """Shared evaluation of an expansion given a way to solve subproblems."""

    def __init__(
        self,
        weights: tuple[float, float, float] = DEFAULT_WEIGHTS,
        splits_of: SplitEnumerator = ENUMERATORS["greedy_canonical"],
        key_of: typing.Callable[[Bigraph, bool], typing.Hashable] = key,
    ) -> None:
        self.weights = weights
        self.splits_of = splits_of
        self.key_of = key_of
        self.memo: dict[typing.Hashable, tuple[int, Cost]] = {}

    def solve(self, bigraph: Bigraph, first: bool = False) -> tuple[int, Cost]:
        """Realization count of the bigraph and the cost of computing it."""
        raise NotImplementedError

    def evaluate(self, bigraph: Bigraph, first: bool = False) -> tuple[int, Cost]:
        """Count and cost when biedge 0 is selected here and `solve` is used below."""
        e = expand(bigraph, first, self.splits_of)
        value, cost = self.solve(e.first)
        value *= e.factor
        cost += e.local
        if e.second is not None:
            v, c = self.solve(e.second)
            value, cost = value + v, cost + c
        for big_M, big_N in e.splits:
            v, c = self.solve(big_M)
            cost += c
            if v != 0:
                w, c = self.solve(big_N)
                v *= w
                cost += c
            value += v
        return value, cost

    def q_values(
        self, bigraph: Bigraph, first: bool = False
    ) -> dict[int, tuple[int, Cost]]:
        """`evaluate` for every distinct choice of the selected biedge."""
        return {
            i: self.evaluate(select(bigraph, i), first)
            for i in distinct_choices(bigraph)
        }


class PolicyEvaluator(_Solver):
    """Cost of the recursion when `selector` picks the biedge in every call (deterministic selectors only)."""

    def __init__(
        self,
        selector: BiedgeSelector | None,
        weights=DEFAULT_WEIGHTS,
        splits_of: SplitEnumerator = ENUMERATORS["greedy_canonical"],
    ) -> None:
        super().__init__(weights, splits_of)
        self.selector = selector

    def solve(self, bigraph: Bigraph, first: bool = False) -> tuple[int, Cost]:
        k = self.key_of(bigraph, first)
        if (hit := self.memo.get(k)) is not None:
            return hit
        if is_terminal(bigraph):
            result = terminal_value(bigraph), Cost(calls=1)
        else:
            i = 0 if self.selector is None else self.selector(bigraph)
            result = self.evaluate(select(bigraph, i), first)
        self.memo[k] = result
        return result


class Oracle(_Solver):
    """Minimum cost over all biedge selections in every recursion call.

    `q[key]` holds the scalar cost of each distinct choice (by index into the memoised bigraph's order)
    with optimal selection below, for every non-terminal subproblem reached.
    """

    def __init__(
        self,
        weights=DEFAULT_WEIGHTS,
        splits_of: SplitEnumerator = ENUMERATORS["greedy_canonical"],
        key_of: typing.Callable[[Bigraph, bool], typing.Hashable] = key,
    ) -> None:
        super().__init__(weights, splits_of, key_of)
        self.q: dict[typing.Hashable, dict[int, float]] = {}
        # the bigraph each `q` entry indexes into, first one reached for its key
        self.states: dict[typing.Hashable, Bigraph] = {}

    def solve(self, bigraph: Bigraph, first: bool = False) -> tuple[int, Cost]:
        k = self.key_of(bigraph, first)
        if (hit := self.memo.get(k)) is not None:
            return hit
        if is_terminal(bigraph):
            result = terminal_value(bigraph), Cost(calls=1)
        else:
            qs = self.q_values(bigraph, first)
            values = {v for v, _ in qs.values()}
            assert len(values) == 1, f"selection changed the result: {values}"
            self.states[k] = bigraph
            self.q[k] = {i: c.scalar(self.weights) for i, (_, c) in qs.items()}
            result = min(qs.values(), key=lambda vc: vc[1].scalar(self.weights))
        self.memo[k] = result
        return result


def root_bigraph(graph: nx.Graph) -> Bigraph | None:
    """The bigraph pyrigi's recursion starts from, with `first=True`; None if it never recurses."""
    from realization_counting.measure import reduced_graph

    reduced = reduced_graph(graph)
    return None if reduced is None else rc._graph_to_bigraph(reduced)


def solve_root(solver: _Solver, graph: nx.Graph) -> tuple[int, Cost] | None:
    root = root_bigraph(graph)
    return None if root is None else solver.solve(root, first=True)


def root_q_values(
    solver: _Solver, graph: nx.Graph
) -> dict[int, tuple[int, Cost]] | None:
    root = root_bigraph(graph)
    return None if root is None else solver.q_values(root, first=True)


__all__: typing.Sequence[str] = [
    "Cost",
    "Oracle",
    "PolicyEvaluator",
    "root_q_values",
    "solve_root",
]
