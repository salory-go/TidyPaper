"""Abstract base class for metadata providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetadataResult:
    """Standardized result from a metadata provider."""

    provider: str = ""
    title: str = ""
    authors: list[str] = field(default_factory=list)
    first_author: str = ""
    year: int | None = None
    venue: str = ""
    paper_type: str = ""  # "conference" | "journal" | "preprint"
    doi: str | None = None
    arxiv_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not self.title and not self.doi


class MetadataProvider(ABC):
    """Base class for all metadata providers."""

    name: str = "base"

    @abstractmethod
    async def query(self, **hints: Any) -> MetadataResult | None:
        """Query the provider with extracted hints.

        Common hint keys:
        - doi: str
        - arxiv_id: str
        - title: str
        - url: str
        """
        ...
