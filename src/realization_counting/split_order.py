"""Strategies for the split enumeration in `_splits_without_loops`.

The enumeration assigns every non-selected biedge to M (contracted on the left) or N
(contracted on the right) and discards a partial split as soon as it contains a loop.
How early that happens depends on the order biedges are assigned in.

An enumerator takes a bigraph whose biedge 0 is selected and yields the same splits
as pyrigi, calling `check(M, N)` (pyrigi's `_has_loop_after_split` by default)
once per enumeration step, so tracking that function counts the work.
"""

import functools
import typing
from contextlib import contextmanager
from unittest.mock import patch

import networkx as nx
import pyrigi.graph._rigidity.realization_counting as rc

from realization_counting.bigraph import Bigraph
from realization_counting.canonical import biedge_ranks

Check = typing.Callable[[list, list], bool]
SplitEnumerator = typing.Callable[..., typing.Iterator[tuple[list, list]]]
# indices of bigraph[1:] (as indices into bigraph) in the order they are assigned
SplitOrder = typing.Callable[[Bigraph], list[int]]


def original(bigraph: Bigraph) -> list[int]:
    return list(range(1, len(bigraph)))


def bfs(bigraph: Bigraph) -> list[int]:
    """Breadth-first from the selected biedge, biedges sharing a vertex on either side are adjacent."""
    by_vertex: dict[tuple[int, int], list[int]] = {}
    for i, be in enumerate(bigraph):
        for s in (0, 1):
            for v in be[s]:
                by_vertex.setdefault((s, v), []).append(i)
    seen = {0}
    order = []
    frontier = [0]
    while frontier:
        nxt = []
        for i in frontier:
            for s in (0, 1):
                for v in bigraph[i][s]:
                    for j in by_vertex[(s, v)]:
                        if j not in seen:
                            seen.add(j)
                            nxt.append(j)
        nxt.sort()
        order += nxt
        frontier = nxt
    # biedges not connected to the selected one
    return order + [i for i in range(1, len(bigraph)) if i not in seen]


def greedy(bigraph: Bigraph, rank: list[int] | None = None) -> list[int]:
    """Next is the biedge with most endpoints already covered by placed biedges.

    Ties go to the lower `rank`, the index by default.
    """
    rank = rank or list(range(len(bigraph)))
    covered: tuple[set, set] = (set(bigraph[0][0]), set(bigraph[0][1]))
    remaining = list(range(1, len(bigraph)))
    order = []
    while remaining:
        best = max(
            remaining,
            key=lambda i: (
                sum(v in covered[s] for s in (0, 1) for v in bigraph[i][s]),
                -rank[i],
            ),
        )
        remaining.remove(best)
        order.append(best)
        for s in (0, 1):
            covered[s].update(bigraph[best][s])
    return order


def greedy_canonical(bigraph: Bigraph) -> list[int]:
    """`greedy` with ties broken by canonical rank, so the order depends only on the isomorphism class."""
    return greedy(bigraph, biedge_ranks(bigraph))


def greedy_reversed(bigraph: Bigraph) -> list[int]:
    return greedy(bigraph)[::-1]


def ordered(order: SplitOrder) -> SplitEnumerator:
    """pyrigi's enumeration with biedges assigned in a fixed order."""

    def enumerate_splits(bigraph: Bigraph, check: Check | None = None):
        check = check or rc._has_loop_after_split
        selected = bigraph[0]
        rest = [bigraph[i] for i in order(bigraph)]

        def extend(i: int, M: list, N: list):
            if check(M, N):
                return
            if i == len(rest):
                yield M, N
                return
            yield from extend(i + 1, [*M, rest[i]], N)
            yield from extend(i + 1, M, [*N, rest[i]])

        yield from extend(0, [selected], [selected])

    return enumerate_splits


def propagating(bigraph: Bigraph, check: Check | None = None):
    """Assign forced biedges before branching.

    A biedge whose left endpoints are joined by the left edges of M would be a loop in N,
    so it must go to M; symmetrically for N on the right. Both at once means no split extends
    the current one. Forced assignments do not change the joined pairs they were forced by,
    so one pass per step suffices; the next `check` validates the result.
    Branching takes the first unforced biedge.
    """
    check = check or rc._has_loop_after_split

    def extend(M: list, N: list, unassigned: list):
        if check(M, N):
            return
        if not unassigned:
            yield M, N
            return
        left, right = nx.utils.UnionFind(), nx.utils.UnionFind()
        for be in M:
            left.union(*be[0])
        for be in N:
            right.union(*be[1])
        to_M, to_N, free = [], [], []
        for be in unassigned:
            in_M = left[be[0][0]] == left[be[0][1]]
            in_N = right[be[1][0]] == right[be[1][1]]
            if in_M and in_N:
                return
            (to_M if in_M else to_N if in_N else free).append(be)
        if to_M or to_N:
            yield from extend([*M, *to_M], [*N, *to_N], free)
            return
        be, free = free[0], free[1:]
        yield from extend([*M, be], N, free)
        yield from extend(M, [*N, be], free)

    yield from extend([bigraph[0]], [bigraph[0]], bigraph[1:])


ENUMERATORS: dict[str, SplitEnumerator] = {
    "original": ordered(original),
    "bfs": ordered(bfs),
    "greedy": ordered(greedy),
    "greedy_canonical": ordered(greedy_canonical),
    "greedy_reversed": ordered(greedy_reversed),
    "propagating": propagating,
}


@contextmanager
def split_enumerator(enumerator: SplitEnumerator) -> typing.Generator[None]:
    """Make pyrigi's recursion enumerate splits with `enumerator`."""

    @functools.wraps(rc._splits_without_loops)
    def splits(bigraph: Bigraph):
        return enumerator(bigraph)

    with patch.object(rc, "_splits_without_loops", splits):
        yield
