"""Application configuration model."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AppConfig:
    """Global configuration for TidyPaper."""

    watch_dirs: list[str] = field(default_factory=lambda: [str(Path.home() / "Downloads")])
    archive_root: str = field(default_factory=lambda: str(Path.home() / "Papers"))
    filename_template: str = "{year} - {venue} - {title}"
    folder_template: str = "{year}/{venue}"
    preview_before_apply: bool = True
    auto_apply_threshold: float = 0.85
    unsorted_folder_name: str = "Unsorted"
    metadata_provider_order: list[str] = field(
        default_factory=lambda: ["doi_lookup", "arxiv_lookup", "openalex"]
    )
