from pathlib import Path

DATA_DIR = Path("data")


def min_rigid_graphs_filename(n: int) -> Path:
    return Path(f"LamanGraphs{n}.txt")
