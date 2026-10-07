# Calm-Trend Regime system. `make` lists every target.
SHELL := /bin/bash
.DEFAULT_GOAL := help

PYTHON ?= python3
VENV   ?= .venv
BIN    := $(VENV)/bin
IMAGE  ?= ctr:1.0.0
DATA   ?= data/raw/BTCUSDT_1h.csv
ASSET  ?=
START  ?=
END    ?=
RUN_ARGS = $(DATA) $(if $(ASSET),--asset $(ASSET)) $(if $(START),--start $(START)) $(if $(END),--end $(END))

.PHONY: help install install-research test info run check binance reproduce \
        docker-build docker-test docker-run docker-reproduce docker-dev clean

help: ## show this help
	@awk 'BEGIN {FS = ":.*## "; printf "\n  \033[1mCTR\033[0m  Calm-Trend Regime system\n\n"} \
	     /^[a-zA-Z_-]+:.*## / {printf "    \033[36m%-18s\033[0m %s\n", $$1, $$2} END {print ""}' $(MAKEFILE_LIST)
	@printf "  Variables: DATA=<csv> ASSET=btc|eth START=YYYY-MM-DD END=YYYY-MM-DD\n\n"

$(BIN)/ctr:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install -q --upgrade pip
	$(BIN)/pip install -q -e ".[dev]"

install: $(BIN)/ctr ## create .venv and install the system (runtime + tests)

install-research: install ## also install the research stack (notebooks, ML)
	$(BIN)/pip install -q -e ".[research]"

test: install ## run the test suite (lookahead, engine, frozen results, system)
	$(BIN)/ctr selftest

info: install ## show strategies, costs, versions and bundled data
	$(BIN)/ctr info

run: install ## analyse DATA and run the frozen strategy on it
	$(BIN)/ctr run $(RUN_ARGS)

check: install ## data-quality report for DATA
	$(BIN)/ctr check $(DATA) $(if $(ASSET),--asset $(ASSET))

binance: install ## fetch Binance candles and evaluate ASSET from START to END (a year of warm-up is added)
	$(BIN)/ctr binance --asset $(ASSET) --start $(START) --end $(END)

reproduce: install ## rebuild the competition results in results/
	$(BIN)/ctr reproduce

docker-build: ## build the runtime image
	docker build --target runtime -t $(IMAGE) .

docker-test: docker-build ## run the test suite inside the image
	docker run --rm $(IMAGE) selftest

docker-run: docker-build ## run on DATA inside the image (DATA under data/raw or data/external)
	mkdir -p runs data/external
	docker run --rm -v "$(CURDIR)/runs:/app/runs" -v "$(CURDIR)/data/external:/app/data/external" $(IMAGE) run $(RUN_ARGS)

docker-reproduce: docker-build ## rebuild the competition results inside the image
	mkdir -p runs results
	docker run --rm -v "$(CURDIR)/results:/app/results" $(IMAGE) reproduce

docker-dev: ## Jupyter Lab with the research stack on http://localhost:8888
	docker compose --profile dev up notebook

clean: ## remove caches and run outputs (keeps results/ and data/)
	rm -rf runs .pytest_cache *.egg-info
	find . -name __pycache__ -type d -prune -not -path "./$(VENV)/*" -exec rm -rf {} +
