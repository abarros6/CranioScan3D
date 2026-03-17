.PHONY: setup test lint run clean help

PYTHON := python3
PIP := pip3
VENV := venv
SRC := src

help:
	@echo "CranioScan3D — available targets:"
	@echo "  setup   Install all dependencies (runs setup_mac.sh)"
	@echo "  test    Run pytest test suite"
	@echo "  lint    Run ruff linter"
	@echo "  run     Run pipeline on sample data (set INPUT=path/to/video.mp4)"
	@echo "  clean   Remove generated data and build artifacts"

setup:
	bash scripts/setup_mac.sh

test:
	$(PYTHON) -m pytest tests/ -v --tb=short

lint:
	$(PYTHON) -m ruff check src/ tests/

run:
	$(PYTHON) -m cranioscan.pipeline --input $(INPUT) --config configs/default.yaml

clean:
	rm -rf data/captures/* data/frames/* data/reconstructions/* data/results/*
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	find . -name "*.log" -delete
	rm -rf dist/ build/ *.egg-info/
