"""Measure pyrigi's realization counting on minimally 2-rigid graphs and save the results to a CSV."""

import argparse
from functools import partial
from pathlib import Path

from realization_counting.edge_selection import SELECTOR_FACTORIES
from realization_counting.measure.experiment import measure_realization_counting
from realization_counting.measure.preprocess import has_no_zero_extension, preprocess
from realization_counting.min_rigid_graphs.download import download_min_rigid_graphs
from realization_counting.min_rigid_graphs.load import read_min_rigid_graphs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-nodes",
        type=int,
        required=True,
        choices=range(6, 13),
        help="maximum node count of the Laman graphs to measure",
    )
    parser.add_argument(
        "--selector",
        required=True,
        choices=SELECTOR_FACTORIES,
        help="function picking the biedge to branch on",
    )
    parser.add_argument("--save", action="store_true", help="store results to a file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.save:
        output = Path("x")
        if output.exists():
            print(f"{output} already exists, skipping measurement")
            return

    download_min_rigid_graphs()
    graphs = preprocess(
        read_min_rigid_graphs(args.max_nodes), partial(filter, has_no_zero_extension)
    )
    print(f"Measuring {len(graphs)} graphs with selector {args.selector}")
    results = measure_realization_counting(graphs, SELECTOR_FACTORIES[args.selector]())

    if args.save:
        results.write_csv(output)
        print(f"Saved measurements to {output}")


if __name__ == "__main__":
    main()
