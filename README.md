# Diploma Thesis

## Source Code

### Requirements

- [uv](https://docs.astral.sh/uv/)

### Running scripts

1. `uv sync`
2. `uv run ...`

### Download minimally rigid graphs

As of September 2026, PyRigi doesn't contain functions to download known minimally 2-rigid graphs. There is a helper script to achieve this in the repo, run:

`uv run src/diploma_thesis/zenodo_download.py`

### Running benchmarks

Benchmarks write their results to `data/`, where the notebooks read them from:

`uv run scripts/measure_realization_counting.py --max-nodes 8 --selector first`

To run any script in a container, pass its path and arguments to the image:

```
podman build -t realization-counting .
podman run --rm -v ./data:/app/data realization-counting scripts/measure_realization_counting.py --max-nodes 8 --selector first
```

### Running notebooks

Notebooks were written using [marimo](https://marimo.io/). To run a notebook, use:

`uv run marimo run ...`


Example

`uv run marimo run src/diploma_thesis/measurement.py`
