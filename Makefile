# Convenience targets. `KW` is the search keyword, e.g. `make run KW=elecciones`.
KW ?= honduras
IMAGE ?= newsscraper:latest

.PHONY: help install test run docker-build docker-test docker-run clean

help:
	@echo "Targets:"
	@echo "  install       Create a local install with dev deps (+ Playwright browser)"
	@echo "  test          Run the offline unit test suite"
	@echo "  run           Run the scraper locally        (make run KW=elecciones)"
	@echo "  docker-build  Build the Docker image"
	@echo "  docker-test   Run the test suite inside Docker"
	@echo "  docker-run    Run the scraper inside Docker   (make docker-run KW=mundial)"
	@echo "  clean         Remove build/output artifacts"

install:
	pip install -e ".[dev]"
	python -m playwright install --with-deps chromium

test:
	pytest -q

run:
	python -m newsscraper "$(KW)"

docker-build:
	docker build -t $(IMAGE) .

docker-test: docker-build
	docker run --rm --entrypoint pytest $(IMAGE) -q

docker-run: docker-build
	docker run --rm -v "$(PWD)/data:/app/data" $(IMAGE) "$(KW)"

clean:
	rm -rf build dist *.egg-info src/*.egg-info .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
