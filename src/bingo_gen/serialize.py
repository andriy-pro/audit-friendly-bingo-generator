from __future__ import annotations

import csv
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence

from .uniqueness import cards_hash, matrix_hash


def ensure_parent(path: Path, *, mkdirs: bool) -> None:
    parent = path.parent
    if not parent.exists() and mkdirs:
        parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: object, *, mkdirs: bool, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"Refusing to overwrite existing file without --force: {path}"
        )
    ensure_parent(path, mkdirs=mkdirs)
    text = json.dumps(data, ensure_ascii=True, sort_keys=True, indent=2)
    path.write_text(text + "\n", encoding="utf-8")


def build_run_meta(
    *,
    app_version: str,
    params_hash: str,
    seed: int,
    rng_engine: str,
    parallel: bool,
    parallelism: int,
) -> Dict[str, object]:
    return {
        "app_version": app_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python_version": __import__("sys").version.split()[0],
        "platform": platform.system().lower(),
        "git_commit": None,
        "run_id": None,
        "params_hash": params_hash,
        "seed": seed,
        "rng_engine": rng_engine,
        "hash_algorithm": "sha256",
        "parallel": parallel,
        "parallelism": parallelism,
    }


def emit_cards_json(
    path: Path,
    *,
    cards: Sequence[Sequence[Sequence[int]]],
    run_meta: Dict[str, object],
    mkdirs: bool,
    overwrite: bool,
) -> None:
    entries: List[Dict[str, object]] = []
    for idx, matrix in enumerate(cards, start=1):
        entries.append(
            {"id": str(idx), "matrix": matrix, "matrix_hash": matrix_hash(matrix)}
        )
    data = {
        "run_meta": run_meta,
        "cards": entries,
        "cards_hash": cards_hash([c for c in cards]),
    }
    write_json(path, data, mkdirs=mkdirs, overwrite=overwrite)


def emit_report_json(
    path: Path, *, report: Dict[str, object], mkdirs: bool, overwrite: bool
) -> None:
    write_json(path, report, mkdirs=mkdirs, overwrite=overwrite)


def emit_summary_csv(
    path: Path,
    *,
    freqs: Dict[int, int],
    by_position: Dict[str, Dict[int, int]] | None,
    mkdirs: bool,
    overwrite: bool,
) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"Refusing to overwrite existing file without --force: {path}"
        )
    ensure_parent(path, mkdirs=mkdirs)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["number", "total"])
        for num in sorted(freqs.keys()):
            writer.writerow([num, freqs[num]])
        if by_position:
            writer.writerow([])
            writer.writerow(["position", "number", "count"])
            for pos in sorted(by_position.keys()):
                row = by_position[pos]
                for num in sorted(row.keys()):
                    writer.writerow([pos, num, row[num]])
