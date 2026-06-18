# ---------------------------------------------------------------------------
# Official Playwright image: ships Python + Chromium + all system libraries the
# browser needs, pinned to the exact Playwright version we depend on. This is by
# far the most reliable way to run Playwright in a container.
# ---------------------------------------------------------------------------
FROM mcr.microsoft.com/playwright/python:v1.60.0-noble

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    NEWSSCRAPER_HEADLESS=true \
    NEWSSCRAPER_OUTPUT_DIR=/app/data

WORKDIR /app

# 1) Install the package (editable) with its dev extras. Editable keeps /app/src
#    as the import source, which also allows mounting host code for iteration.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install -e ".[dev]"

# 2) Add the test suite (used by `make docker-test`).
COPY tests ./tests

# 3) Sanity-check that the browser binary is present in the base image.
RUN python -c "from playwright.sync_api import sync_playwright; \
print('Playwright OK')"

# Output (CSV + SQLite) lands here; mount a host volume to keep the files.
RUN mkdir -p /app/data
VOLUME ["/app/data"]

# `docker run <image> <keyword> [flags]` -> runs the scraper.
ENTRYPOINT ["python", "-m", "newsscraper"]
CMD ["--help"]
