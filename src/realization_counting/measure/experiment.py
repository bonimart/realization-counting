import itertools
import time
import typing
from contextlib import ExitStack

import polars as pl
import pyrigi
import pyrigi.graph._rigidity.realization_counting as rc

from realization_counting.edge_selection import BiedgeSelector
from realization_counting.measure.pyrigi_hooks import (
    LAMAN_CHECK,
    REALIZATION_COUNTING_REC,
    select_first_with,
)
from realization_counting.measure.results import (
    MeasurementResult,
    measurements_to_dataframe,
)
from realization_counting.measure.tracking import RecursionStats, patched, tracked


def measure_graph_function(
    graphs: typing.Iterable[pyrigi.Graph],
    func: typing.Callable[[pyrigi.Graph], typing.Any],
    stats: RecursionStats,
    limit: int | None = None,
    counters: dict[str, RecursionStats] | None = None,
) -> list[MeasurementResult]:
    """Time `func` on each graph and record the recursion stats it produced.

    `counters` are stats of helper functions; only their call counts are recorded.
    """
    counters = counters or {}
    measurements = []
    for graph in itertools.islice(graphs, limit):
        stats.reset()
        for counter in counters.values():
            counter.reset()
        start_time = time.perf_counter()
        func_result = func(graph)
        exec_time = time.perf_counter() - start_time
        measurements.append(
            MeasurementResult(
                graph_id=graph.to_int(),
                function_result=func_result,
                execution_time_ms=exec_time * 1_000,
                recursion_stats=stats.export(),
                counts={name: c.calls for name, c in counters.items()},
            )
        )
    return measurements


def measure_realization_counting(
    graphs: typing.Iterable[pyrigi.Graph], selector: BiedgeSelector | None = None
) -> pl.DataFrame:
    """Measure pyrigi's `number_of_realizations`, optionally overriding its biedge selection.

    Recursion calls are weighted by the number of biedges on input.
    `split_steps` counts steps of the split enumeration, `laman_checks` pseudo-Laman checks.
    """
    with ExitStack() as stack:
        stats = stack.enter_context(
            tracked(
                rc,
                REALIZATION_COUNTING_REC,
                weight=lambda bigraph, *_, **__: len(bigraph),
            )
        )
        counters = {
            "laman_checks": stack.enter_context(tracked(rc, LAMAN_CHECK)),
        }
        if selector is not None:
            stack.enter_context(
                patched(rc, REALIZATION_COUNTING_REC, select_first_with(selector))
            )
        return measurements_to_dataframe(
            measure_graph_function(
                graphs, rc.number_of_realizations, stats, counters=counters
            )
        )
