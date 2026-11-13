import functools
import typing

from realization_counting.bigraph import Bigraph
from realization_counting.edge_selection import BiedgeSelector

REALIZATION_COUNTING_REC = "_number_of_plane_realizations_min_rigid_dim_2_rec"
LAMAN_CHECK = "_bigraph_is_pseudo_laman"


def select_first_with(selector: BiedgeSelector):
    """Move the selected biedge to index 0, where pyrigi's recursion branches on it."""

    def decorator[**P, R](
        func: typing.Callable[typing.Concatenate[Bigraph, P], R],
    ) -> typing.Callable[typing.Concatenate[Bigraph, P], R]:
        @functools.wraps(func)
        def wrapper(bigraph: Bigraph, *args: P.args, **kwargs: P.kwargs) -> R:
            if len(bigraph) < 2:  # base case, nothing to select
                return func(bigraph, *args, **kwargs)
            i = selector(bigraph)
            return func([bigraph[i], *bigraph[:i], *bigraph[i + 1 :]], *args, **kwargs)

        return wrapper

    return decorator
