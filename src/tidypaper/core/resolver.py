"""Extract DOI, arXiv ID, and venue hints from text and URLs."""

from __future__ import annotations

import re

# ── DOI ─────────────────────────────────────────────────────

# DOI pattern: 10.XXXX/...  (captures the DOI value)
_DOI_RE = re.compile(
    r"""
    (10\.\d{4,9}          # DOI prefix: 10. + 4-9 digits
    /                      # separator
    [^\s,;\"'<>\]}{)]+     # suffix: non-whitespace chars (greedy)
    )
    """,
    re.VERBOSE,
)


def extract_doi(text: str) -> str | None:
    """Extract the first DOI found in the given text.

    Searches PDF text, URLs, and other strings for DOI patterns.
    """
    if not text:
        return None
    match = _DOI_RE.search(text)
    if match:
        doi = match.group(1).rstrip(".")  # strip trailing dot
        return doi
    return None


# ── arXiv ID ────────────────────────────────────────────────

# New-style: YYMM.NNNNN(vN)  e.g.  2301.12345, 2301.12345v2
# Old-style: category/YYMMNNN(vN)  e.g.  hep-th/9901001
_ARXIV_NEW_RE = re.compile(r"(\d{4}\.\d{4,5}(?:v\d+)?)")
_ARXIV_OLD_RE = re.compile(r"([a-z-]+/\d{7}(?:v\d+)?)")
_ARXIV_URL_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5}(?:v\d+)?)")


def extract_arxiv_id(text: str, filename: str = "") -> str | None:
    """Extract an arXiv ID from text or filename.

    Checks:
    1. arXiv URL patterns
    2. New-style IDs (YYMM.NNNNN)
    3. Old-style IDs (category/YYMMNNN)
    4. Filename patterns
    """
    combined = f"{text}\n{filename}"
    if not combined.strip():
        return None

    # Priority 1: arXiv URL
    m = _ARXIV_URL_RE.search(combined)
    if m:
        return m.group(1)

    # Priority 2: explicit "arXiv:" prefix
    explicit = re.search(r"arXiv:\s*(\d{4}\.\d{4,5}(?:v\d+)?)", combined, re.IGNORECASE)
    if explicit:
        return explicit.group(1)

    # Priority 3: new-style in text (only if context suggests arXiv)
    if "arxiv" in combined.lower():
        m = _ARXIV_NEW_RE.search(combined)
        if m:
            return m.group(1)

    # Priority 4: old-style
    m = _ARXIV_OLD_RE.search(combined)
    if m:
        return m.group(1)

    return None


# ── Venue hints ─────────────────────────────────────────────

_KNOWN_VENUES = [
    "NeurIPS", "ICML", "ICLR", "AAAI", "IJCAI", "CVPR", "ICCV", "ECCV",
    "ACL", "EMNLP", "NAACL", "COLING",
    "KDD", "WWW", "SIGIR", "WSDM", "CIKM",
    "SIGMOD", "VLDB", "ICDE",
    "OSDI", "SOSP", "NSDI", "EuroSys",
    "ISCA", "MICRO", "HPCA", "ASPLOS",
    "TPAMI", "TIP", "JMLR", "TACL",
    "Nature", "Science", "PNAS",
]

_PROCEEDINGS_RE = re.compile(
    r"(?:Proceedings?\s+of|Proc\.\s+of|In\s+Proceedings?\s+of)\s+(?:the\s+)?(.+?)(?:\.|,|\n)",
    re.IGNORECASE,
)

_VENUE_DOMAIN_MAP: dict[str, str] = {
    "openreview.net": "OpenReview",
    "proceedings.mlr.press": "PMLR",
    "openaccess.thecvf.com": "CVF",
    "ieeexplore.ieee.org": "IEEE",
    "dl.acm.org": "ACM",
    "link.springer.com": "Springer",
    "sciencedirect.com": "Elsevier",
}


def extract_venue_hints(text: str) -> list[str]:
    """Extract venue hints from PDF text.

    Returns a list of possible venue names, ordered by confidence.
    """
    hints: list[str] = []

    # Check for known venue abbreviations
    text_upper = text.upper()
    for v in _KNOWN_VENUES:
        if v.upper() in text_upper:
            if v not in hints:
                hints.append(v)

    # Check for "Proceedings of ..." patterns
    for m in _PROCEEDINGS_RE.finditer(text):
        proc = m.group(1).strip()
        if proc and proc not in hints:
            hints.append(proc)

    return hints


def extract_venue_from_url(url: str) -> str | None:
    """Infer a venue hint from a URL domain."""
    if not url:
        return None
    for domain, venue in _VENUE_DOMAIN_MAP.items():
        if domain in url:
            return venue
    return None
