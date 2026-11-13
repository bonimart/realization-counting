"""
Parsing module that implements conversion of graphs in Mathematica format to pyrigi graphs.
"""

import logging
import typing
from pathlib import Path

import pyrigi

from realization_counting.min_rigid_graphs.paths import (
    DATA_DIR,
    min_rigid_graphs_filename,
)

_logger = logging.getLogger(__name__)


def read_graphs_from_mathematica(filepath: Path) -> typing.Iterator[pyrigi.Graph]:
    """
    Lazily parses graphs from a text file in format described in https://zenodo.org/records/1245517?preview_file=Description.txt.
    """
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            # remove Mathematica list syntax
            clean_line = line.strip("{}\n, ")
            if not clean_line:
                continue
            for item in clean_line.split(","):
                yield pyrigi.Graph.from_int(int(item))


def read_min_rigid_graphs(
    max_node_count: int, min_node_count: int = 3, dir: Path = DATA_DIR
) -> typing.Iterator[pyrigi.Graph]:
    """
    Reads minimally rigid graphs up to a maximum node count.
    Expects graphs to be downloaded using the Zenodo download utility from this repository.
    """
    for n in range(min_node_count, max_node_count + 1):
        file = dir / min_rigid_graphs_filename(n)
        if not file.exists():
            _logger.warning(f"File {file} doesn't exist")
            continue
        yield from read_graphs_from_mathematica(file)


if __name__ == "__main__":
    if not DATA_DIR.exists():
        print(
            f"{DATA_DIR} doesn't exist, make sure to download minimally rigid graphs first."
        )
    N = 6
    print(f"Reading minimally rigid graphs of size <={N}.")
    graphs = list(read_min_rigid_graphs(N, 2))
    print(f"Read {len(graphs)} graphs")
    for graph in graphs:
        print(graph.nodes)
        print(graph.edges)
