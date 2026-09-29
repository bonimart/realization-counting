from copy import deepcopy
from dataclasses import dataclass

import more_itertools
import networkx as nx
from pyrigi.graph._general import min_degree
from pyrigi.graph._rigidity.realization_counting import (
    _biedges_have_loop,
    _bigraph_contract_delete,
    _bigraph_delete_contract,
    _bigraph_is_pseudo_laman,
    _graph_to_bigraph,
)

from diploma_thesis.bigraph import Bigraph
from diploma_thesis.edge_selection import BiedgeSelector


@dataclass
class TotalCost:
    weighted: int = 0
    unweighted: int = 0

    def __add__(self, bigraph: Bigraph) -> TotalCost:
        return TotalCost(
            weighted=self.weighted + len(bigraph), unweighted=self.unweighted + 1
        )


class RealizationCountingEnvironment:
    """
    Reimplements `number_of_realizations` from PyRigi to measure the performance of a given edge selection strategy.
    Performance is measured as the number of recursion steps.
    """

    def __init__(self, graph: nx.Graph, biedge_selector: BiedgeSelector) -> None:
        self._result: int = 0
        self._selector = biedge_selector
        self._total_cost = TotalCost()
        G = deepcopy(graph)
        deg_2 = 0
        # use :prf:ref:`lem-realization-0-extension`
        while G.number_of_nodes() > 2 and min_degree(G) == 2:
            min_v = [v for v in G.nodes if G.degree(v) == 2]
            G.remove_nodes_from(min_v)
            deg_2 += len(min_v)
        self._node_count = G.number_of_nodes()
        self._deg_2_exp = deg_2
        if self._node_count < 2:
            root = []
        else:
            root = _graph_to_bigraph(G)
        self._root = root

    def evaluate(self) -> TotalCost:
        self._total_cost = TotalCost()
        if self._node_count == 0:
            # self._result = 2 ** (self._deg_2_exp - 2)
            return self._total_cost
        elif self._node_count == 2:
            # self._result = 2**self._deg_2_exp
            return self._total_cost
        self._evaluate_rec(self._root, first=True)
        return self._total_cost

    def _evaluate_rec(self, bigraph: Bigraph, first: bool = False):
        self._total_cost += bigraph
        if _biedges_have_loop(bigraph):
            return 0
        if len(bigraph) == 1:
            return 1
        selected_edge_idx = self._selector(bigraph)
        selected_edge = bigraph[selected_edge_idx]
        self._evaluate_rec(_bigraph_contract_delete(bigraph, [selected_edge]))
        if not first:
            self._evaluate_rec(_bigraph_delete_contract(bigraph, [selected_edge]))
        subsets = more_itertools.powerset(
            bigraph[:selected_edge_idx] + bigraph[selected_edge_idx + 1 :]
        )
        for sub in subsets:
            if len(sub) == 0 or len(sub) == len(bigraph) - 1:
                continue
            sub_M = list(sub)
            sub_M.append(selected_edge)
            sub_N = [be for be in bigraph if be not in sub_M]
            sub_N.append(selected_edge)

            sub_big_M = _bigraph_contract_delete(bigraph, sub_M)
            sub_big_N = _bigraph_delete_contract(bigraph, sub_N)
            if _bigraph_is_pseudo_laman(sub_big_N) and _bigraph_is_pseudo_laman(
                sub_big_M
            ):
                self._evaluate_rec(sub_big_M)
                self._evaluate_rec(sub_big_N)
