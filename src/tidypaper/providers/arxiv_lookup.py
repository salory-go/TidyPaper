"""arXiv API lookup provider."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any

import httpx

from tidypaper.providers.base import MetadataProvider, MetadataResult

logger = logging.getLogger(__name__)

_ARXIV_API = "http://export.arxiv.org/api/query"
_TIMEOUT = 15.0
_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivLookupProvider(MetadataProvider):
    """Look up paper metadata via arXiv API."""

    name = "arxiv_lookup"

    async def query(self, **hints: Any) -> MetadataResult | None:
        arxiv_id: str | None = hints.get("arxiv_id")
        if not arxiv_id:
            return None

        params = {"id_list": arxiv_id}
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(_ARXIV_API, params=params)
                resp.raise_for_status()
                xml_text = resp.text
        except (httpx.HTTPError, Exception) as exc:
            logger.warning("arXiv lookup failed for ID %s: %s", arxiv_id, exc)
            return None

        return self._parse_response(xml_text, arxiv_id)

    def _parse_response(self, xml_text: str, arxiv_id: str) -> MetadataResult | None:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            logger.warning("Failed to parse arXiv XML response")
            return None

        entry = root.find("atom:entry", _NS)
        if entry is None:
            return None

        # Title
        title_el = entry.find("atom:title", _NS)
        title = title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else ""

        # Authors
        authors = []
        for author_el in entry.findall("atom:author", _NS):
            name_el = author_el.find("atom:name", _NS)
            if name_el is not None and name_el.text:
                authors.append(name_el.text.strip())
        first_author = authors[0] if authors else ""

        # Year from published date
        year = None
        published_el = entry.find("atom:published", _NS)
        if published_el is not None and published_el.text:
            try:
                year = int(published_el.text[:4])
            except (ValueError, IndexError):
                pass

        # Categories as venue hint
        categories = []
        for cat_el in entry.findall("atom:category", _NS):
            term = cat_el.get("term", "")
            if term:
                categories.append(term)

        return MetadataResult(
            provider=self.name,
            title=title,
            authors=authors,
            first_author=first_author,
            year=year,
            venue="arXiv",
            paper_type="preprint",
            arxiv_id=arxiv_id,
            raw={"categories": categories},
        )
