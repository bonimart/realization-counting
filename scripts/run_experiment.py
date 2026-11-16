"""Build the image and run a command over every parameter combination of an experiment.

The experiment file is TOML with a `command` (script path inside the image) and a
`[grid]` table mapping each command-line flag to a list of values. `true` passes the
flag, `false` omits it, anything else is passed as `--flag value`. Each combination
writes to `data/<experiment>/<key=value,...>.csv`; existing outputs are skipped.
"""

import argparse
import itertools
import subprocess
import tomllib
from pathlib import Path

IMAGE = "realization-counting"
DATA_DIR = Path("data")


def to_flags(params: dict) -> list[str]:
    flags = []
    for key, value in params.items():
        flag = "--" + key.replace("_", "-")
        if value is True:
            flags.append(flag)
        elif value is not False:
            flags += [flag, str(value)]
    return flags


def output_name(params: dict) -> str:
    def fmt(value: object) -> str:
        return str(value).lower() if isinstance(value, bool) else str(value)

    return ",".join(f"{key}={fmt(value)}" for key, value in params.items()) + ".csv"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path, help="experiment TOML file")
    args = parser.parse_args()

    spec = tomllib.loads(args.experiment.read_text())
    grid = spec["grid"]
    subprocess.run(["podman", "build", "-t", IMAGE, "."], check=True)

    for values in itertools.product(*grid.values()):
        params = dict(zip(grid, values))
        output = DATA_DIR / args.experiment.stem / output_name(params)
        if output.exists():
            print(f"{output} already exists, skipping")
            continue
        cmd = [
            "podman", "run", "--rm", "-v", f"./{DATA_DIR}:/app/{DATA_DIR}", IMAGE,
            spec["command"], *to_flags(params), "--output", str(output),
        ]  # fmt: skip
        print(" ".join(cmd), flush=True)
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
