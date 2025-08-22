from __future__ import annotations

import os
from pathlib import Path

from bingo_gen.config import resolve_parameters, compute_params_hash, canonical_json_dumps


def test_env_precedence_over_config(tmp_path: Path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("R: 60\nT: 10\n", encoding="utf-8")
    monkeypatch.setenv("BINGO_GEN_R", "75")

    resolved, params_hash, _ = resolve_parameters(
        config_path_str=str(cfg), cli_overrides={}, env=os.environ
    )
    assert resolved["R"] == 75
    assert params_hash.startswith("sha256:")


def test_cli_precedence_over_env(tmp_path: Path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("R: 60\nT: 10\n", encoding="utf-8")
    monkeypatch.setenv("BINGO_GEN_R", "70")

    resolved, _hash, _ = resolve_parameters(
        config_path_str=str(cfg), cli_overrides={"R": 80}, env=os.environ
    )
    assert resolved["R"] == 80


def test_path_normalization_cli_vs_config(tmp_path: Path, monkeypatch):
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    cfg = cfg_dir / "conf.yaml"
    cfg.write_text("out_cards: cards.json\n", encoding="utf-8")

    # CLI override for report path (should be relative to CWD)
    cwd = tmp_path
    monkeypatch.chdir(cwd)
    resolved, _hash, _ = resolve_parameters(
        config_path_str=str(cfg),
        cli_overrides={"out_report": "rep.json"},
        env=os.environ,
    )
    assert Path(resolved["out_cards"]).parent == cfg_dir.resolve()
    assert Path(resolved["out_report"]).parent == cwd.resolve()


def test_params_hash_contract_stability():
    base = {
        "R": 75,
        "T": 150,
        "m": 3,
        "n": 4,
        "unique_scope": ["col_sets", "row_sets"],
        "uniformity": "strict",
        "position_balance": True,
        "seed": {"engine": "py_random", "value": 20250824},
        "bbd_mode": "auto",
        "build_timeout_sec": 90,
        "swap_iterations": 20000,
        "parallel": False,
        "parallelism": 1,
        "allow_best_effort": False,
        # Excluded fields
        "out_cards": "cards.json",
        "log_level": "INFO",
    }

    resolved, h1, _ = resolve_parameters(config_path_str=None, cli_overrides=base, env={})
    # Change excluded field only and expect same hash
    altered = dict(base)
    altered["log_level"] = "DEBUG"
    _, h2, _ = resolve_parameters(config_path_str=None, cli_overrides=altered, env={})
    assert h1 == h2


