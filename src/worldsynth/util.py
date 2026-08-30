from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def canonical_data(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return canonical_data(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {str(key): canonical_data(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [canonical_data(item) for item in value]
    if isinstance(value, tuple):
        return [canonical_data(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    return value


def canonical_json(value: Any, *, pretty: bool = False) -> str:
    kwargs: dict[str, Any] = {
        "ensure_ascii": False,
        "sort_keys": True,
    }
    if pretty:
        kwargs["indent"] = 2
    else:
        kwargs["separators"] = (",", ":")
    return json.dumps(canonical_data(value), **kwargs) + ("\n" if pretty else "")


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def write_text_if_changed(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return
    path.write_text(text, encoding="utf-8", newline="\n")
