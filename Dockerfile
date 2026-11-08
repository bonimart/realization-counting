FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim as builder
RUN apt-get update \
        && apt-get install -y --no-install-recommends git cmake gcc g++ build-essential \
        && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
RUN uv sync --frozen --no-dev


FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim
WORKDIR /app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "notebooks/01_current_performance.py"]
