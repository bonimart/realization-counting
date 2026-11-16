FROM ghcr.io/astral-sh/uv:0.13.7-trixie-slim AS builder
RUN apt-get update \
        && apt-get install -y --no-install-recommends git build-essential \
        && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy \
    UV_PYTHON_PREFERENCE=only-managed UV_PYTHON_INSTALL_DIR=/python
COPY .python-version ./
RUN uv python install
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
        uv sync --frozen --no-dev --no-install-project
COPY README.md ./
COPY src src
COPY scripts scripts
RUN --mount=type=cache,target=/root/.cache/uv \
        uv sync --frozen --no-dev


FROM debian:trixie-slim
COPY --from=builder /python /python
COPY --from=builder /app /app
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT ["python"]
CMD ["scripts/measure_realization_counting.py", "--help"]
