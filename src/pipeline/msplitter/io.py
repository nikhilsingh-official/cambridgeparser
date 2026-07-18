from pathlib import Path
from typing import Any
import json


def load_json(path: Path) -> Any:
    """Load a JSON document from disk."""
    with path.open() as f:
        return json.load(f)


def write_json(path: Path, document: Any) -> None:
    """Write a JSON document to disk, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(document, f, indent=2)
