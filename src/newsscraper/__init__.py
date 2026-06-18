"""newsscraper: keyword-driven news scraper for Honduran outlets, built on Playwright.

The package is organised around a small hexagonal core:

* ``models``      -- plain data structures (``Article``, ``SitemapEntry``).
* ``ports``       -- abstract contracts (``SiteAdapter``, ``ArticleRepository``).
* ``sitemap`` /
  ``extraction``  -- pure parsing logic with no I/O (unit-testable in isolation).
* ``robots`` /
  ``browser``     -- the I/O edges that talk to the network via Playwright.
* ``sites``       -- one adapter per news outlet (site-specific knowledge only).
* ``storage``     -- CSV + SQLite repositories.
* ``pipeline``    -- orchestration that wires everything together.
* ``cli``         -- the command-line entry point.
"""

__version__ = "1.0.0"
