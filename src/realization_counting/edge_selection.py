import random
from abc import ABC, abstractmethod

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
