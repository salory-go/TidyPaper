"""OpenAlex title search provider."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from tidypaper.providers.base import MetadataProvider, MetadataResult

logger = logging.getLogger(__name__)

_OPENALEX_API = "https://api.openalex.org/works"
_TIMEOUT = 15.0
_USER_AGENT = "TidyPaper/0.1.0 (mailto:tidypaper@example.com)"


class OpenAlexProvider(MetadataProvider):
    """Search OpenAlex for paper metadata by title."""

    name = "openalex"

    async def query(self, **hints: Any) -> MetadataResult | None:
        title: str | None = hints.get("title")
        if not title or len(title) < 5:
            return None

        params = {"search": title, "per_page": "1"}
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(
                    _OPENALEX_API,
                    params=params,
                    headers={"User-Agent": _USER_AGENT},
                )
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, Exception) as exc:
            logger.warning("OpenAlex search failed for title '%s': %s", title[:50], exc)
            return None

        results = data.get("results", [])
        if not results:
            return None

        return self._parse_work(results[0])

    def _parse_work(self, work: dict) -> MetadataResult:
        # Title
        title = work.get("title", "") or ""

        # Authors
        authors = []
        for authorship in work.get("authorships", []):
            author = authorship.get("author", {})
            name = author.get("display_name", "")
            if name:
                authors.append(name)
        first_author = authors[0] if authors else ""

        # Year
        year = work.get("publication_year")

        # Venue
        venue = ""
        primary_location = work.get("primary_location", {}) or {}
        source = primary_location.get("source", {}) or {}
        venue = source.get("display_name", "") or ""

        # DOI
        doi = work.get("doi", "")
        if doi and doi.startswith("https://doi.org/"):
            doi = doi[len("https://doi.org/"):]

        # Type
        work_type = work.get("type", "")
        paper_type = ""
        if "article" in work_type:
            paper_type = "journal"
        elif "proceedings" in work_type:
            paper_type = "conference"

        return MetadataResult(
            provider=self.name,
            title=title,
            authors=authors,
            first_author=first_author,
            year=year,
            venue=venue,
            paper_type=paper_type,
            doi=doi or None,
            raw=work,
        )
