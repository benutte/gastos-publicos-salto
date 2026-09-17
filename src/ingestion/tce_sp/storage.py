import hashlib
import json
from pathlib import Path
from typing import Any


def save_json_atomic(data: Any, output_path: Path) -> dict:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    temporary_path.replace(output_path)

    content = output_path.read_bytes()

    return {
        "sha256": hashlib.sha256(content).hexdigest(),
        "content_length_bytes": len(content),
    }
