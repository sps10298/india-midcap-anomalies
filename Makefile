# One command per stage. `make all` reproduces every table, figure and the paper
# from the processed panel that ships with the repository (about 5 minutes).
.PHONY: all data panel backtests stats figures paper test lint

all: backtests stats figures paper

data:        ## download ~2 GB of raw files (optional)
	python scripts/01_download_data.py --reference
panel:       ## rebuild data/processed from raw (optional, ~10 min)
	python scripts/02_build_panel.py
backtests:
	python scripts/03_run_backtests.py
stats:
	python scripts/04_statistics.py
figures:
	python scripts/05_figures.py
paper:
	python scripts/06_build_paper.py
test:
	pytest -q
lint:
	ruff check . && ruff format --check .
