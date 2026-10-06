import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Realization counting measurement

    This notebook measures execution time of the existing `number_of_realizations` function from `pyrigi`.
    """)
    return


@app.cell
def _():
    from pathlib import Path

    import altair as alt
    import marimo as mo
    import polars as pl
    from pyrigi.graph._rigidity.realization_counting import number_of_realizations

    from realization_counting.edge_selection import FirstBiedgeSelector, LastBiedgeSelector, RandomBiedgeSelector
    from realization_counting.measurement_helpers import (
        measure_graph_function,
        read_graphs_up_to,
        filter_zero_deletions
    )
    from realization_counting.realization_counting_env import (
        RealizationCountingEnvironment,
    )
    from realization_counting.zenodo_download import download_min_rigid_graphs

    return (
        FirstBiedgeSelector,
        LastBiedgeSelector,
        Path,
        RandomBiedgeSelector,
        RealizationCountingEnvironment,
        alt,
        download_min_rigid_graphs,
        filter_zero_deletions,
        measure_graph_function,
        mo,
        number_of_realizations,
        pl,
        read_graphs_up_to,
    )


@app.cell
def _(mo):
    n_nodes_slider = mo.ui.slider(
        start=8,
        stop=10,
        step=1,
        value=8,
        label="Maximum number of nodes of minimally 2-rigid graphs to count realizations for: ",
        show_value=True,
    )
    n_nodes_slider  # ruff: ignore[B018]
    return (n_nodes_slider,)


@app.cell
def _(
    Path,
    download_min_rigid_graphs,
    filter_zero_deletions,
    mo,
    n_nodes_slider,
    read_graphs_up_to,
):
    if not Path("data/").exists():
        download_min_rigid_graphs()
    try:
        graphs = filter_zero_deletions(read_graphs_up_to(n_nodes_slider.value))
    except FileNotFoundError as e:
        mo.stop(
            True,
            mo.callout(f"Could not read minimally rigid graph files {e}", kind="warn"),
        )
    return (graphs,)


@app.cell
def _(
    Path,
    graphs,
    measure_graph_function,
    n_nodes_slider,
    number_of_realizations,
    pl,
):
    exec_time_fname = Path(f"data/execution_time_{n_nodes_slider.value}.csv")
    if not exec_time_fname.exists():
        results = measure_graph_function(graphs, number_of_realizations)
        df = pl.DataFrame(results)
        df.write_csv(exec_time_fname)
    else:
        df = pl.read_csv(exec_time_fname)
    return (df,)


@app.cell
def _(df, mo):
    mo.md(f"""
    Total execution time: {df.select("execution_time_ms").sum().item() / 1000:.2f} s
    """)
    return


@app.cell
def _(df):
    df.select("execution_time_ms").describe()
    return


@app.cell
def _(alt, df):
    alt.Chart(
        df.select("execution_time_ms"),
        width=1200,
        height=400,
        title="Number of graphs by total execution time (grouped by 100 ms)",
    ).mark_bar(tooltip=True).encode(
        x=alt.X(
            "execution_time_ms", bin=alt.Bin(step=100), title="Execution time [ms]"
        ),
        y="count()",
    ).interactive()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Recursion step count measurement

    We measure 2 variants:
    1. Unweighted recursion step count - each recursion call has weight 1
    2. Weighted recursion step count - each recursion call is weighted by the number of biedges on input

    Intuitively, edge selection in early recursion calls (with bigger bigraphs) should have bigger impact on execution time.
    """)
    return


@app.cell
def _(FirstBiedgeSelector, RealizationCountingEnvironment, pl, pyrigi):
    def measure_rec_steps(graphs: list[pyrigi.Graph]) -> pl.DataFrame:
        costs = []
        for graph in graphs:
            env = RealizationCountingEnvironment(
                graph, biedge_selector=FirstBiedgeSelector()
            )
            cost = env.evaluate()
            costs.append(cost)
        return pl.DataFrame({"weighted_rec_steps": [cost.weighted for cost in costs], "unweighted_rec_steps": [cost.unweighted for cost in costs]})

    return (measure_rec_steps,)


@app.cell
def _(Path, graphs, measure_rec_steps, n_nodes_slider, pl):
    rec_steps_fname = Path(f"data/rec_steps_{n_nodes_slider.value}.csv")
    if not rec_steps_fname.exists():
        rec_steps_df = measure_rec_steps(graphs)
        rec_steps_df.write_csv(rec_steps_fname)
    else:
        rec_steps_df = pl.read_csv(rec_steps_fname)
    return (rec_steps_df,)


@app.cell
def _(df, rec_steps_df):
    df_with_rec_steps = df.hstack(rec_steps_df)
    return (df_with_rec_steps,)


@app.cell
def _(df_with_rec_steps):
    df_with_rec_steps.select(
        [
            "function_result",
            "execution_time_ms",
            "unweighted_rec_steps",
            "weighted_rec_steps",
        ]
    ).corr(label="cols").select(["cols", "execution_time_ms"])
    return


@app.cell
def _(alt, df_with_rec_steps):
    base = alt.Chart(df_with_rec_steps).mark_point(tooltip=True)

    c1 = base.encode(x="weighted_rec_steps", y="execution_time_ms")
    c2 = base.encode(x="unweighted_rec_steps", y="execution_time_ms")
    c3 = base.encode(x="function_result", y="execution_time_ms")

    (c1 | c2 | c3).interactive()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Edge selection algorithm comparison

    We will measure 3 trivial approaches of edge selection in terms of weighted recursion step count:

    1. Selecting first edge
    2. Selecting last edge
    3. Selecting a random edge
    """)
    return


@app.cell
def _(
    FirstBiedgeSelector,
    LastBiedgeSelector,
    RandomBiedgeSelector,
    RealizationCountingEnvironment,
    pl,
    pyrigi,
):
    def measure_selectors(graphs: list[pyrigi.Graph]) -> pl.DataFrame:
        data = {}
        selectors = [
            ("first", FirstBiedgeSelector()),
            ("last", LastBiedgeSelector()),
            ("random", RandomBiedgeSelector(seed=42))
        ]
        for name, selector in selectors:
            weighted_rec_steps = []
            for graph in graphs:
                env = RealizationCountingEnvironment(
                    graph, biedge_selector=selector
                )
                cost = env.evaluate()
                weighted_rec_steps.append(cost.weighted)
            data[name] = weighted_rec_steps
        return pl.DataFrame(data)

    return (measure_selectors,)


@app.cell
def _(Path, graphs, measure_selectors, n_nodes_slider, pl):
    selector_fname = Path(f"data/selector_{n_nodes_slider.value}.csv")
    if not selector_fname.exists():
        selector_df = measure_selectors(graphs)
        selector_df.write_csv(selector_fname)
    else:
        selector_df = pl.read_csv(selector_fname)
    return (selector_df,)


@app.cell
def _(selector_df):
    selector_df.describe()
    return


if __name__ == "__main__":
    app.run()
