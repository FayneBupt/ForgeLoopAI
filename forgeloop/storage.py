from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RunStore:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.runs_root = project_root / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)

    def run_dir(self, run_id: str) -> Path:
        return self.runs_root / run_id

    def ensure_run_layout(self, run_id: str) -> Path:
        run_dir = self.run_dir(run_id)
        (run_dir / "artifacts" / "logs").mkdir(parents=True, exist_ok=True)
        (run_dir / "artifacts" / "sql").mkdir(parents=True, exist_ok=True)
        (run_dir / "artifacts" / "patches").mkdir(parents=True, exist_ok=True)
        (run_dir / "artifacts" / "diffs").mkdir(parents=True, exist_ok=True)
        return run_dir

    def write_json(self, path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def read_json(self, path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    def append_event(self, run_id: str, event: dict[str, Any]) -> None:
        events_file = self.run_dir(run_id) / "events.jsonl"
        with events_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
