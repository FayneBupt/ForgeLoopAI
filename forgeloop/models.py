from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class RunStatus(str, Enum):
    INIT = "INIT"
    RUNNING_LOOP = "RUNNING_LOOP"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class Run:
    run_id: str
    project_name: str
    repo: str
    branch: str
    status: str
    phase: str
    current_round: int
    started_at: str
    ended_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Gate:
    gate_id: str
    run_id: str
    round_index: int
    phase: str
    reason: str
    risk_level: str
    status: str
    opened_at: str
    resolved_at: str | None
    resolved_by: str | None
    decision: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
