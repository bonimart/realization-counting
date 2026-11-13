import marimo

__generated_with = "0.25.0"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Current performance of $\text{Plane}_\#$ from pyrigi

    This notebook measures execution time of the existing `number_of_realizations` function from `pyrigi`.
    """)


@app.cell
def _():
    import altair as alt
    import marimo as mo
    import matplotlib.pyplot as plt
    import polars as pl
    import pyrigi

    from realization_counting.edge_selection import SELECTOR_FACTORIES
    from realization_counting.measure import measure_realization_counting
    from realization_counting.measurement_helpers import measurements_path

    return (
        SELECTOR_FACTORIES,
        alt,
        measure_realization_counting,
        measurements_path,
        mo,
        pl,
        plt,
        pyrigi,
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
def _(SELECTOR_FACTORIES):
    selectors = {name: factory() for name, factory in SELECTOR_FACTORIES.items()}
    return (selectors,)


@app.cell
def _(measurements_path, mo, n_nodes_slider, pl, selectors):
    _missing = [
        name
        for name in selectors
        if not measurements_path(name, n_nodes_slider.value).exists()
    ]
    mo.stop(
        bool(_missing),
        mo.callout(
            mo.md(
                f"Missing measurements for selectors: {', '.join(_missing)}. Generate them with "
                f"`uv run scripts/measure_realization_counting.py --max-nodes {n_nodes_slider.value} --selector <selector>`."
            ),
            kind="warn",
        ),
    )

    measurements_df = pl.concat(
        pl.read_csv(measurements_path(name, n_nodes_slider.value)).with_columns(
            selector=pl.lit(name)
        )
        for name in selectors
    )
    df = measurements_df.filter(pl.col("selector") == "first")
    return df, measurements_df


@app.cell(hide_code=True)
def _(df, mo):
    mo.md(f"""
    Total execution time: {df.select("execution_time_ms").sum().item() / 1000:.2f} s
    """)


@app.cell
def _(df):
    df.select("execution_time_ms").describe()


@app.cell
def _(alt, df):
    alt.Chart(
        df.select("execution_time_ms"),
        title="Number of graphs by total execution time (grouped by 100 ms)",
    ).mark_bar(tooltip=True).encode(
        x=alt.X(
            "execution_time_ms", bin=alt.Bin(step=100), title="Execution time [ms]"
        ),
        y="count()",
    ).interactive()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Recursion step count measurement

    We measure 2 variants:
    1. Unweighted recursion step count - each recursion call has weight 1
    2. Weighted recursion step count - each recursion call is weighted by the number of biedges on input

    Intuitively, edge selection in early recursion calls (with bigger bigraphs) should have bigger impact on execution time.
    """)


@app.cell
def _(df):
    df.select(
        ["function_result", "execution_time_ms", "calls", "weighted", "max_depth"]
    ).corr(label="cols").select(["cols", "execution_time_ms"])


@app.cell
def _(alt, df):
    base = alt.Chart(df).mark_point(tooltip=True)

    c1 = base.encode(x="weighted", y="execution_time_ms")
    c2 = base.encode(x="calls", y="execution_time_ms")
    c3 = base.encode(x="function_result", y="execution_time_ms")

    (c1 | c2 | c3).interactive()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Edge selection algorithm comparison

    We will measure 3 trivial approaches of edge selection in terms of weighted recursion step count:

    1. Selecting first edge
    2. Selecting last edge
    3. Selecting a random edge
    """)


@app.cell
def _(measurements_df, pl):
    measurements_df.group_by("selector", maintain_order=True).agg(
        total_time_s=pl.col("execution_time_ms").sum() / 1000,
        mean_time_ms=pl.col("execution_time_ms").mean(),
        median_time_ms=pl.col("execution_time_ms").median(),
        max_time_ms=pl.col("execution_time_ms").max(),
        mean_weighted=pl.col("weighted").mean(),
        mean_calls=pl.col("calls").mean(),
    )


@app.cell(expand_output=True)
def _(alt, measurements_df):
    alt.Chart(
        measurements_df.select("execution_time_ms", "selector"),
        width=800,
        height=200,
        title="Number of graphs by total execution time (grouped by 100 ms) per edge selection",
    ).mark_bar(tooltip=True).encode(
        x=alt.X(
            "execution_time_ms", bin=alt.Bin(step=100), title="Execution time [ms]"
        ),
        y="count()",
        row=alt.Row("selector:N", title="Edge selection"),
    ).interactive()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Per-graph comparison

    Random selection performs consistently worse than the first selection, last selection performs a little worse in the mean, but there are some cases when it is much better than first selection.
    """)


@app.cell(expand_output=True)
def _(alt, measurements_df, selectors):
    per_graph_df = measurements_df.pivot(
        "selector", index="graph_id", values="execution_time_ms"
    ).unpivot(
        [selector for selector in selectors if selector != "first"],
        index=["graph_id", "first"],
        variable_name="selector",
        value_name="execution_time_ms",
    )
    _x = alt.X("first", title="First edge execution time [ms]")
    _points = (
        alt.Chart()
        .mark_point()
        .encode(
            x=_x,
            y=alt.Y("execution_time_ms", title="Execution time [ms]"),
            tooltip=["graph_id:N", "selector:N", "first", "execution_time_ms"],
        )
    )
    _diagonal = (
        alt.Chart().mark_line(color="gray", strokeDash=[4, 4]).encode(x=_x, y="first")
    )
    alt.layer(_points, _diagonal, data=per_graph_df).properties(
        width=500, height=500
    ).facet(
        column=alt.Column("selector:N", title="Edge selection vs. first edge"),
        title="Per-graph execution time compared to first edge selection",
    ).interactive()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Single graph exploration

    Why does edge selection matter so much for some graphs? We force each biedge to be selected in the root call
    (pyrigi's default first biedge below it) and compare the recursion cost.
    The root bigraph is built from the graph with degree-2 vertices removed, biedge $i$ is its $i$-th edge.

    I have identified 2 graphs where the first/last difference was the most significant
    - 1315206214433 - first significantly outperforms last
    - 27523242111198 - last significantly outperforms first
    """)


@app.cell
def _():
    last_worst_id = 1315206214433
    last_best_id = 27523242111198
    return last_best_id, last_worst_id


@app.cell
def _(last_best_id, last_worst_id, mo):
    graph_id_input = mo.ui.dropdown(
        {str(last_worst_id): last_worst_id, str(last_best_id): last_best_id},
        value=str(last_worst_id),
        label="Graph id: ",
    )
    graph_id_input  # ruff: ignore[B018]
    return (graph_id_input,)


@app.cell
def _(graph_id_input, pyrigi):
    graph = pyrigi.Graph.from_int(graph_id_input.value)
    root_edges = list(graph.edges)
    return graph, root_edges


@app.cell
def _(graph, plt, root_edges):
    # first root biedge red, last green
    graph.plot(edge_colors_custom={"red": [root_edges[0]], "green": [root_edges[-1]]})
    plt.gca()


@app.cell
def _(graph, measure_realization_counting, pl, selectors):
    pl.concat(
        measure_realization_counting([graph], selector).with_columns(
            selector=pl.lit(name)
        )
        for name, selector in selectors.items()
    ).select("selector", "execution_time_ms", "calls", "weighted", "max_depth")


if __name__ == "__main__":
    app.run()
