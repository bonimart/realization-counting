from abc import ABC, abstractmethod

from realization_counting.bigraph import BiedgeId, Bigraph


class BiedgeSelector(ABC):
    @abstractmethod
    def __call__(self, bigraph: Bigraph) -> BiedgeId: ...


class TrivialBiedgeSelector(BiedgeSelector):
    def __call__(self, bigraph: Bigraph) -> BiedgeId:
        return 0
