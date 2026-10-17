import functools
import itertools
import time
import typing
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from types import ModuleType
from unittest.mock import patch

import polars as pl
import pyrigi


@dataclass
class RecursionStats:
    calls: int = 0
    weighted: int = 0
    max_depth: int = 0
    _depth: int = field(default=0, repr=False)

    def reset(self):
        self.calls = self.weighted = self.max_depth = self._depth = 0

    def export(self) -> typing.Self:
        return deepcopy(self)


class TrackedFunction[**P, R](typing.Protocol):
    """Typing helper for functions wrapped inside `track_recursion` decorator."""

    stats: RecursionStats

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R: ...


def track_recursion[**P, R](
    weight: typing.Callable[..., int] = lambda *args, **kwargs: 1,
) -> typing.Callable[[typing.Callable[P, R]], TrackedFunction[P, R]]:
    """Count calls to the decorated function and sum a per-call weight."""

    def decorator(func: typing.Callable[P, R]) -> TrackedFunction[P, R]:
        stats = RecursionStats()

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            stats.calls += 1
            stats.weighted += weight(*args, **kwargs)
            stats._depth += 1
            stats.max_depth = max(stats._depth, stats.max_depth)
            try:
                return func(*args, **kwargs)
            finally:
                stats._depth -= 1

        wrapper.stats = stats
        return typing.cast(TrackedFunction[P, R], wrapper)

    return decorator


@contextmanager
def tracked(
    module: ModuleType,
    name: str,
    weight: typing.Callable[..., int] = lambda *args, **kwargs: 1,
) -> typing.Iterator[RecursionStats]:
    """Patch `module.name` with a tracked version so recursive calls are counted too."""
    func = track_recursion(weight)(getattr(module, name))
    with patch.object(module, name, func):
        yield func.stats


@dataclass
class Measurement:
    graph_id: int
    function_result: typing.Any
    execution_time_ms: float
    recursion_stats: RecursionStats


def measure_graph_function(
    graphs: typing.Iterable[pyrigi.Graph],
    func: typing.Callable[[pyrigi.Graph], typing.Any],
    stats: RecursionStats,
    limit: int | None = None,
) -> list[Measurement]:
    """Time `func` on each graph and record the recursion stats it produced."""
    measurements = []
    for graph in itertools.islice(graphs, limit):
        stats.reset()
        start_time = time.perf_counter()
        func_result = func(graph)
        exec_time = time.perf_counter() - start_time
        measurements.append(
            Measurement(
                graph_id=graph.to_int(),
                function_result=func_result,
                execution_time_ms=exec_time * 1_000,
                recursion_stats=stats.export(),
            )
        )
    return measurements


def measurements_to_dataframe(measurements: list[Measurement]) -> pl.DataFrame:
    return (
        pl.DataFrame([asdict(m) for m in measurements])
        .unnest("recursion_stats")
        .drop("_depth")  # internal counter, always 0 after a call returns
    )
