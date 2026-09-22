from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel

from .schemas import DriverCatalog


def discover_markdown_cases(directory: Path) -> list[Path]:
    if not directory.exists():
        raise FileNotFoundError(f"Cases directory does not exist: {directory}")
    return sorted(path for path in directory.glob("*.md") if path.is_file())


def case_id_from_path(path: Path) -> str:
    parts = path.stem.split("_")
    return "_".join(parts[:2]) if len(parts) >= 2 and parts[0] == "case" else path.stem


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_prompt(prompts_dir: Path, name: str) -> str:
    return read_text(prompts_dir / name)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def atomic_write_json(path: Path, value: BaseModel | dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    fd, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(payload, output, ensure_ascii=False, indent=2)
            output.write("\n")
        os.replace(temporary_name, path)
    except Exception:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def append_jsonl(path: Path, value: BaseModel | dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    with path.open("a", encoding="utf-8") as output:
        output.write(json.dumps(payload, ensure_ascii=False) + "\n")


def load_catalog(path: Path) -> DriverCatalog:
    return DriverCatalog.model_validate_json(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_csv(path: Path, rows: Iterable[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
