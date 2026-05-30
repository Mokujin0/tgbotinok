import csv
import json
import threading
from pathlib import Path

_locks_guard = threading.Lock()
_file_locks: dict[str, threading.Lock] = {}


def _lock_for(path: Path) -> threading.Lock:
    key = str(Path(path).resolve())
    with _locks_guard:
        lock = _file_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _file_locks[key] = lock
        return lock


def read_json(path: Path, default=None):
    path = Path(path)
    with _lock_for(path):
        if not path.exists():
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


def write_json(path: Path, data) -> None:
    path = Path(path)
    with _lock_for(path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def update_json(path: Path, mutator, default=None):
    path = Path(path)
    with _lock_for(path):
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = default
        new_data = mutator(data)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
        return new_data


def read_csv_rows(path: Path) -> tuple[list[dict], list[str] | None]:
    path = Path(path)
    with _lock_for(path):
        if not path.exists() or path.stat().st_size == 0:
            return [], None
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            return rows, reader.fieldnames


def write_csv_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path = Path(path)
    with _lock_for(path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def update_csv(path: Path, mutator, default_fieldnames: list[str]):
    path = Path(path)
    with _lock_for(path):
        rows: list[dict] = []
        fieldnames = default_fieldnames
        if path.exists() and path.stat().st_size > 0:
            with open(path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                fieldnames = reader.fieldnames or default_fieldnames
        result = mutator(rows, fieldnames)
        new_rows, new_fieldnames, payload = result
        if new_rows is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=new_fieldnames)
                writer.writeheader()
                writer.writerows(new_rows)
        return payload
