import json
from pathlib import Path
from typing import Any


class LocalLMSClient:
    """Auditable local LMS adapter; replace this class with an institutional API."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def publish(self, package: dict[str, Any]) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        destination = self.output_dir / f"{package['course_code']}_next_class.json"
        destination.write_text(
            json.dumps(package, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return destination
