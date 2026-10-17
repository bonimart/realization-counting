import itertools
import typing
from pathlib import Path

import networkx as nx
import pyrigi
from pyrigi.graph._general import min_degree


def read_graphs_from_nums(
    filepath: Path, node_count: int
) -> typing.Iterator[pyrigi.Graph]:
    """
    Lazily parses a text file in format as described in https://zenodo.org/records/1245517?preview_file=Description.txt.
    Takes path to the text file as the first argument.
    Requires the number of nodes of the graphs as the second argument.
    """
    num_upper_triangle_entries = (node_count * (node_count - 1)) // 2

    def _graph_from_num(num: int) -> pyrigi.Graph:
        # strip '0b' from beginning & left pad to size 'n'
        bin_str = bin(num)[2:].zfill(num_upper_triangle_entries)
        G_nx = nx.Graph()
        G_nx.add_nodes_from(range(node_count))
        # parse upper triangular part of adjacency matrix <=> every possible pair of vertices
        for idx, (i, j) in enumerate(itertools.combinations(range(node_count), 2)):
            if bin_str[idx] == "1":
                G_nx.add_edge(i, j)
        return pyrigi.Graph(G_nx)

    with open(filepath, encoding="utf-8") as f:
        for line in f:
            # remove Mathematica list syntax
            clean_line = line.strip("{}\n, ")
            if not clean_line:
                continue
            for item in clean_line.split(","):
                yield _graph_from_num(int(item))


def read_graphs_up_to(
    max_node_count: int, min_node_count: int = 3, dir: Path = Path("data")
) -> typing.Iterator[pyrigi.Graph]:
    for n in range(min_node_count, max_node_count + 1):
        yield from read_graphs_from_nums(dir / f"LamanGraphs{n}.txt", n)


def filter_zero_deletions(graphs: typing.Iterable[nx.Graph]) -> list[nx.Graph]:
    """Filters out minimally rigid graphs constructed solely by 0-expansion."""
    return [
        graph
        for graph in graphs
        if graph.number_of_nodes() > 2 and min_degree(graph) > 2
    ]
