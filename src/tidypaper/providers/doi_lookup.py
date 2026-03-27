"""Crossref DOI lookup provider."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from tidypaper.providers.base import MetadataProvider, MetadataResult

logger = logging.getLogger(__name__)

_CROSSREF_API = "https://api.crossref.org/works"
_TIMEOUT = 15.0
_USER_AGENT = "TidyPaper/0.1.0 (mailto:tidypaper@example.com)"


class DoiLookupProvider(MetadataProvider):
    """Look up paper metadata via Crossref DOI API."""

    name = "doi_lookup"

    async def query(self, **hints: Any) -> MetadataResult | None:
        doi: str | None = hints.get("doi")
        if not doi:
            return None

        url = f"{_CROSSREF_API}/{doi}"
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(
                    url,
                    headers={"User-Agent": _USER_AGENT},
                )
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, Exception) as exc:
            logger.warning("Crossref lookup failed for DOI %s: %s", doi, exc)
            return None

        return self._parse_response(data, doi)

    def _parse_response(self, data: dict, doi: str) -> MetadataResult:
        msg = data.get("message", {})

        # Title
        titles = msg.get("title", [])
        title = titles[0] if titles else ""

        # Authors
        authors_raw = msg.get("author", [])
        authors = []
        for a in authors_raw:
            given = a.get("given", "")
            family = a.get("family", "")
            name = f"{given} {family}".strip()
            if name:
                authors.append(name)
        first_author = authors[0] if authors else ""

        # Year
        year = None
        date_parts = msg.get("published-print", msg.get("published-online", {}))
        if isinstance(date_parts, dict):
            parts = date_parts.get("date-parts", [[]])
            if parts and parts[0]:
                year = parts[0][0]

        # Venue / type
        venue = ""
        container = msg.get("container-title", [])
        if container:
            venue = container[0]
        short_container = msg.get("short-container-title", [])
        if short_container and not venue:
            venue = short_container[0]

        paper_type = msg.get("type", "")
        if "journal" in paper_type:
            paper_type = "journal"
        elif "proceedings" in paper_type:
            paper_type = "conference"
        else:
            paper_type = ""

        return MetadataResult(
            provider=self.name,
            title=title,
            authors=authors,
            first_author=first_author,
            year=year,
            venue=venue,
            paper_type=paper_type,
            doi=doi,
            raw=msg,
        )
