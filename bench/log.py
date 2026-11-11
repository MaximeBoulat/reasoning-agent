import json
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunLog:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.path = directory / "trajectory.jsonl"

    def write(self, event: str, **fields: object) -> None:
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"timestamp": utc_now(), "event": event, **fields}, ensure_ascii=False) + "\n")

    def save(self, filename: str, value: dict) -> None:
        (self.directory / filename).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
