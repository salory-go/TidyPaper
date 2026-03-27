"""Data models for file operations and batch records."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class OperationRecord:
    """A single file rename/move operation within a batch."""

    batch_id: str
    paper_id: str
    old_path: str
    new_path: str
    executed_at: str = field(default_factory=_now_utc)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class BatchRecord:
    """A group of operations applied together, supporting undo as a unit."""

    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=_now_utc)
    status: str = "executed"  # "executed" | "undone"
    operation_count: int = 0
