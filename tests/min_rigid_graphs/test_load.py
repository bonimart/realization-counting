from pathlib import Path

import pyrigi
import pytest
from pyrigi import graphDB

from realization_counting.min_rigid_graphs.load import (
    read_graphs_from_mathematica,
    read_min_rigid_graphs,
)
from realization_counting.min_rigid_graphs.paths import (
    DATA_DIR,
    min_rigid_graphs_filename,
)


def write(path: Path, *graphs: pyrigi.Graph) -> Path:
    """Write graphs as a Mathematica list split over lines, like the Zenodo files."""
    numbers = ", \n ".join(str(g.to_int()) for g in graphs)
    path.write_text(f"{{{numbers}}}\n", encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "graph", [graphDB.Complete(3), graphDB.Diamond(), graphDB.ThreePrism()]
)
def test_reads_graph_in_mathematica_format(tmp_path, graph):
    [loaded] = read_graphs_from_mathematica(write(tmp_path / "g.txt", graph))

    assert loaded == graph


def test_reads_files_up_to_node_count(tmp_path):
    write(tmp_path / min_rigid_graphs_filename(3), graphDB.Complete(3))
    write(tmp_path / min_rigid_graphs_filename(4), graphDB.Diamond())

    loaded = list(read_min_rigid_graphs(3, dir=tmp_path))

    assert [g.number_of_nodes() for g in loaded] == [3]


# number of minimally rigid graphs up to isomorphism, https://oeis.org/A227117
@pytest.mark.parametrize(("n", "count"), {3: 1, 4: 1, 5: 3, 6: 13, 7: 70}.items())
def test_zenodo_files(n, count):
    if not (DATA_DIR / min_rigid_graphs_filename(n)).exists():
        pytest.skip("Zenodo graphs not downloaded")

    loaded = list(read_min_rigid_graphs(n, min_node_count=n, dir=DATA_DIR))

    assert len(loaded) == count
    assert all(g.is_min_rigid(dim=2) for g in loaded)
