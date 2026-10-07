# syntax=docker/dockerfile:1.7
#
# Calm-Trend Regime system: the frozen BTC/ETH strategies, the backtest engine and the data analysis.
# Ships code, tests and the raw competition data only (no reports, notebooks or research history);
# data/processed is rebuilt from data/raw at build time (byte-identical to the published files).
#
#   docker build -t ctr .
#   docker run --rm ctr info
#   docker run --rm -v "$PWD/runs:/app/runs" ctr run data/raw/BTCUSDT_1h.csv
#   docker run --rm -v "$PWD/runs:/app/runs" -v "$PWD/my_data:/app/data/external:ro" ctr run data/external/ETH.csv --asset eth
#
# Targets: runtime (default, ~slim) and dev (adds the research stack and Jupyter for the notebooks).

ARG PYTHON_VERSION=3.14

# ---------------------------------------------------------------- base
FROM python:${PYTHON_VERSION}-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MPLBACKEND=Agg \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

# ---------------------------------------------------------------- dependencies (cached layer)
FROM base AS deps
RUN python -m venv /opt/venv
COPY requirements-lock.txt /tmp/
RUN pip install -r /tmp/requirements-lock.txt "setuptools>=69"

# ---------------------------------------------------------------- runtime
FROM base AS runtime
LABEL org.opencontainers.image.title="ctr" \
      org.opencontainers.image.description="Calm-Trend Regime: frozen BTC/ETH strategies and data analysis for unseen data" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.source="https://github.com/PriyanshuIITGHY2006/InterIIT_Quant_Jain-Streeter"

RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin ctr
COPY --from=deps /opt/venv /opt/venv
WORKDIR /app
COPY pyproject.toml pytest.ini run.py ./
COPY src ./src
COPY scripts ./scripts
COPY tests ./tests
COPY data ./data
RUN pip install --no-deps --no-build-isolation -e . \
 && python -m src.data.preprocess \
 && mkdir -p runs results data/external \
 && chown -R ctr:ctr /app

USER ctr
VOLUME ["/app/runs", "/app/data/external"]
HEALTHCHECK NONE
ENTRYPOINT ["ctr"]
CMD ["--help"]

# ---------------------------------------------------------------- dev (research stack + Jupyter)
FROM runtime AS dev
USER root
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/* \
 && pip install --no-build-isolation -e ".[research,dev]"
USER ctr
ENTRYPOINT []
CMD ["bash"]
