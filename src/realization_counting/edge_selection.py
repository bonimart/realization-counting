import random
from abc import ABC, abstractmethod
from collections import Counter, defaultdict

from realization_counting.bigraph import BiedgeId, Bigraph


class BiedgeSelector(ABC):
    @abstractmethod
    def __call__(self, bigraph: Bigraph) -> BiedgeId: ...


class RandomBiedgeSelector(BiedgeSelector):
    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def __call__(self, bigraph: Bigraph) -> BiedgeId:
        return self._rng.randint(0, len(bigraph) - 1)


class FirstBiedgeSelector(BiedgeSelector):
    def __call__(self, bigraph: Bigraph) -> BiedgeId:
        return 0


class LastBiedgeSelector(BiedgeSelector):
    def __call__(self, bigraph: Bigraph) -> BiedgeId:
        return len(bigraph) - 1


class ScoredBiedgeSelector(BiedgeSelector):
    """Select the biedge with the lowest score, ties go to the lower index.

    Bigraphs with fewer than `min_biedges` biedges keep the first biedge,
    since scoring may not pay off on small inputs.
    """

    def __init__(self, min_biedges: int = 0) -> None:
        self._min_biedges = min_biedges

    def __call__(self, bigraph: Bigraph) -> BiedgeId:
        if len(bigraph) < self._min_biedges:
            return 0
        sides = [_Side([biedge[s] for biedge in bigraph]) for s in (0, 1)]
        return min(range(len(bigraph)), key=lambda i: self._score(bigraph[i], sides))

    @abstractmethod
    def _score(self, biedge, sides: list[_Side]) -> tuple[int, ...]: ...


class _Side:
    """Degrees (with multiplicity) and neighbourhoods of one side of a bigraph."""

    def __init__(self, edges) -> None:
        self.degree = Counter()
        self.neighbours = defaultdict(set)
        for u, v in edges:
            self.degree[u] += 1
            self.degree[v] += 1
            self.neighbours[u].add(v)
            self.neighbours[v].add(u)

    def triangles(self, u, v) -> int:
        return len(self.neighbours[u] & self.neighbours[v])


def _triangles(biedge, sides: list[_Side]) -> int:
    return sum(side.triangles(*edge) for edge, side in zip(biedge, sides))


class FewestTrianglesBiedgeSelector(ScoredBiedgeSelector):
    """Fewest triangles containing the biedge, summed over both sides."""

    def _score(self, biedge, sides):
        return (_triangles(biedge, sides),)


class LowestDegreeBiedgeSelector(ScoredBiedgeSelector):
    """Lowest endpoint degree over both sides, then fewest triangles."""

    def _score(self, biedge, sides):
        min_degree = min(
            side.degree[node] for edge, side in zip(biedge, sides) for node in edge
        )
        return (min_degree, _triangles(biedge, sides))
