import random
from collections.abc import Callable, Iterable, Iterator

import pyrigi
from pyrigi.graph._general import min_degree

GraphPreprocessor = Callable[[Iterable[pyrigi.Graph]], Iterator[pyrigi.Graph]]


def preprocess(graphs: Iterable[pyrigi.Graph], *steps: GraphPreprocessor):
    """Applies preprocessing to input graphs."""
    for step in steps:
        graphs = step(graphs)
    return graphs


def has_no_zero_extension(graph: pyrigi.Graph) -> bool:
    """Return whether a graph contains a 0-extension."""
    return graph.number_of_nodes() > 2 and min_degree(graph) > 2


def shuffle_nodes(graph: pyrigi.Graph, rng: random.Random) -> pyrigi.Graph:
    """Shuffle node insertion order, keeping labels and edge insertion order.

    pyrigi numbers bigraph nodes by insertion order, so this changes the bigraph.
    """
    nodes = list(graph.nodes)
    graph = pyrigi.Graph()
    graph.add_nodes_from(rng.sample(nodes, len(nodes)))
    graph.add_edges_from(graph.edges)
    return graph
