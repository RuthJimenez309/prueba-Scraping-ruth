"""Registry of available site adapters.

The CLI resolves ``--site`` values through here, so wiring a new outlet is a
one-line change once its adapter exists.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..ports import SiteAdapter
from .elheraldo import ElHeraldo
from .latribuna import LaTribuna

_SITES: dict[str, SiteAdapter] = {
    site.key: site for site in (ElHeraldo(), LaTribuna())
}


def available_keys() -> list[str]:
    return list(_SITES.keys())


def get_sites(keys: Sequence[str] | None = None) -> list[SiteAdapter]:
    """Return adapters for *keys* (or all of them when *keys* is None/empty)."""
    if not keys:
        return list(_SITES.values())
    resolved: list[SiteAdapter] = []
    unknown: list[str] = []
    for key in keys:
        site = _SITES.get(key.strip().lower())
        if site is None:
            unknown.append(key)
        else:
            resolved.append(site)
    if unknown:
        raise KeyError(
            f"Unknown site(s): {', '.join(unknown)}. "
            f"Available: {', '.join(available_keys())}"
        )
    return resolved
