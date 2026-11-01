"""Canonical forms of bigraphs via nauty.

A bigraph is encoded as a simple vertex-coloured graph: one vertex per biedge, joined to its
two left endpoints and its two right endpoints, with left and right vertices coloured apart.
Parallel biedges become distinct vertices, so multiedges need no special care.
"""

import pynauty

from realization_counting.bigraph import Bigraph


def to_nauty(bigraph: Bigraph, selected: int | None = None) -> pynauty.Graph:
    """Vertices are biedges `0..m-1`, then left vertices, then right vertices.

    The `selected` biedge, if any, gets a colour of its own.
    """
    m = len(bigraph)
    left = dict.fromkeys(v for be in bigraph for v in be[0])
    right = dict.fromkeys(v for be in bigraph for v in be[1])
    offset = m + len(left)
    ids = (
        {v: m + i for i, v in enumerate(left)},
        {v: offset + i for i, v in enumerate(right)},
    )
    adjacency = {
        i: {ids[s][v] for s in (0, 1) for v in be[s]} for i, be in enumerate(bigraph)
    }
    biedges = set(range(m))
    coloring = []
    if selected is not None:
        coloring.append({selected})
        biedges.discard(selected)
    coloring += [biedges, set(ids[0].values()), set(ids[1].values())]
    return pynauty.Graph(
        offset + len(ids[1]),
        adjacency_dict=adjacency,
        vertex_coloring=[c for c in coloring if c],
    )


def biedge_ranks(bigraph: Bigraph, selected: int = 0) -> list[int]:
    """Canonical rank of each biedge, relative to the selected one.

    Bigraphs isomorphic by a map sending the selected biedge to the selected biedge
    get ranks that agree up to an automorphism.
    """
    label = pynauty.canon_label(to_nauty(bigraph, selected))
    rank = [0] * len(bigraph)
    for position, vertex in enumerate(label):
        if vertex < len(bigraph):
            rank[vertex] = position
    return rank


def canonical_key(bigraph: Bigraph, first: bool = False) -> tuple:
    """Equal exactly for isomorphic bigraphs (with the same `first` flag)."""
    left = {v for be in bigraph for v in be[0]}
    right = {v for be in bigraph for v in be[1]}
    return (
        first,
        len(bigraph),
        len(left),
        len(right),
        pynauty.certificate(to_nauty(bigraph)),
    )
