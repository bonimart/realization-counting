import typing
from dataclasses import asdict, dataclass, field

import polars as pl

from realization_counting.measure.tracking import RecursionStats


@dataclass
class MeasurementResult:
    graph_id: int
    function_result: typing.Any
    execution_time_ms: float
    recursion_stats: RecursionStats
    counts: dict[str, int] = field(default_factory=dict)


def measurements_to_dataframe(measurements: list[MeasurementResult]) -> pl.DataFrame:
    rows = []
    for m in measurements:
        row = asdict(m)
        row.update(row.pop("recursion_stats"))
        row.update(row.pop("counts"))
        del row["_depth"]  # internal counter, always 0 after a call returns
        rows.append(row)
    return pl.DataFrame(rows)
