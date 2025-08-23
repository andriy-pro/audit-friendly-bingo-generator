from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - loader fallback
    yaml = None


ENV_PREFIX = "BINGO_GEN_"


def _read_config_file(config_path: Path | None) -> Dict[str, Any]:
    if not config_path:
        return {}
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    suffix = config_path.suffix.lower()
    text = config_path.read_text(encoding="utf-8")
    if suffix in (".yaml", ".yml"):
        if yaml is None:
            raise RuntimeError("PyYAML is required to read YAML config files")
        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            raise ValueError("Top-level YAML config must be a mapping")
        return data
    if suffix == ".json":
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("Top-level JSON config must be a mapping")
        return data
    raise ValueError(f"Unsupported config extension: {suffix}")


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _collect_env_vars(env: Mapping[str, str]) -> Dict[str, Any]:
    """Map ENV variables with BINGO_GEN_ prefix to config keys.

    We use an explicit map to avoid ambiguity. Keys not present are ignored.
    """
    mapping: Dict[str, str] = {
        # Core params
        f"{ENV_PREFIX}R": "R",
        f"{ENV_PREFIX}T": "T",
        f"{ENV_PREFIX}M": "m",
        f"{ENV_PREFIX}N": "n",
        f"{ENV_PREFIX}UNIQUE_SCOPE": "unique_scope",
        f"{ENV_PREFIX}UNIFORMITY": "uniformity",
        f"{ENV_PREFIX}POSITION_BALANCE": "position_balance",
        # Seed
        f"{ENV_PREFIX}SEED_MODE": "seed.mode",
        f"{ENV_PREFIX}SEED_VALUE": "seed.value",
        f"{ENV_PREFIX}SEED_ENGINE": "seed.engine",
        # IDs
        f"{ENV_PREFIX}CARD_ID_MODE": "card_id_mode",
        f"{ENV_PREFIX}CARD_NUMBER_START": "card_number_start",
        # Build controls
        f"{ENV_PREFIX}BUILD_TIMEOUT_SEC": "build_timeout_sec",
        f"{ENV_PREFIX}SWAP_ITERATIONS": "swap_iterations",
        # Output & UX
        f"{ENV_PREFIX}COLORS": "colors",
        f"{ENV_PREFIX}LOG_LEVEL": "log_level",
        f"{ENV_PREFIX}LOG_FORMAT": "log_format",
        f"{ENV_PREFIX}LOG_FILE": "log_file",
        f"{ENV_PREFIX}OUT_CARDS": "out_cards",
        f"{ENV_PREFIX}OUT_REPORT": "out_report",
        f"{ENV_PREFIX}SUMMARY_CSV": "summary_csv",
        # Stats
        f"{ENV_PREFIX}STATS_ENGINE": "stats_engine",
        # Termination
        f"{ENV_PREFIX}ALLOW_BEST_EFFORT": "allow_best_effort",
        f"{ENV_PREFIX}BEST_EFFORT_ZERO": "best_effort_zero",
        # Performance
        f"{ENV_PREFIX}PARALLEL": "parallel",
        f"{ENV_PREFIX}PARALLELISM": "parallelism",
    }

    result: Dict[str, Any] = {}
    for env_key, cfg_key in mapping.items():
        if env_key not in env:
            continue
        raw = env[env_key]
        # Type conversions for common keys
        if cfg_key in {
            "R",
            "T",
            "m",
            "n",
            "card_number_start",
            "build_timeout_sec",
            "swap_iterations",
            "parallelism",
        }:
            try:
                result[cfg_key] = int(raw)
            except ValueError:
                result[cfg_key] = raw
        elif cfg_key in {
            "position_balance",
            "allow_best_effort",
            "best_effort_zero",
            "parallel",
        }:
            result[cfg_key] = _parse_bool(raw)
        elif cfg_key == "unique_scope":
            result[cfg_key] = _parse_list(raw)
        elif cfg_key in {"seed.value"}:
            try:
                result[cfg_key] = int(raw)
            except ValueError:
                result[cfg_key] = raw
        else:
            result[cfg_key] = raw

    return result


def _set_nested(config: Dict[str, Any], dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    cursor = config
    for part in parts[:-1]:
        if part not in cursor or not isinstance(cursor[part], dict):
            cursor[part] = {}
        cursor = cursor[part]
    cursor[parts[-1]] = value


def _apply_overrides(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = json.loads(json.dumps(base))  # deep copy via JSON
    for key, value in overrides.items():
        if "." in key:
            _set_nested(merged, key, value)
        else:
            merged[key] = value
    return merged


def canonical_json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def compute_params_hash(resolved: Mapping[str, Any]) -> str:
    include = {
        "R",
        "T",
        "m",
        "n",
        "unique_scope",
        "uniformity",
        "position_balance",
        "build_timeout_sec",
        "swap_iterations",
        "parallel",
        "parallelism",
        "allow_best_effort",
        # seed
        "seed.engine",
        "seed.value",
    }

    def extract(path: str, source: Mapping[str, Any]) -> Any:
        cur: Any = source
        for part in path.split("."):
            if not isinstance(cur, Mapping) or part not in cur:
                return None
            cur = cur[part]
        return cur

    contract: Dict[str, Any] = {}
    for item in include:
        if "." in item:
            value = extract(item, resolved)
            if value is not None:
                contract[item] = value
        else:
            if item in resolved:
                contract[item] = resolved[item]

    # normalize unique_scope: sorted, deduplicated
    if "unique_scope" in contract and isinstance(contract["unique_scope"], list):
        uniq = sorted(set(str(x) for x in contract["unique_scope"]))
        contract["unique_scope"] = uniq

    digest = hashlib.sha256(canonical_json_dumps(contract).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def resolve_paths(
    resolved: Dict[str, Any],
    config_file: Path | None,
    cli_overrides: Dict[str, Any],
) -> Dict[str, Any]:
    """Normalize paths per policy.

    - Paths from config file: resolve relative to config directory
    - Paths from CLI: resolve relative to CWD
    """
    cwd = Path.cwd()
    cfg_dir = config_file.parent if config_file else None

    def normalize(path_value: str | None, is_cli: bool) -> str | None:
        if path_value is None or path_value == "":
            return None
        p = Path(path_value)
        if p.is_absolute():
            return str(p)
        base = cwd if is_cli else (cfg_dir or cwd)
        return str((base / p).resolve())

    result = dict(resolved)
    # Determine which keys came from CLI
    cli_keys = {
        k
        for k in cli_overrides.keys()
        if k in {"out_cards", "out_report", "log_file", "summary_csv"}
    }

    for key in ("out_cards", "out_report", "log_file", "summary_csv"):
        value = resolved.get(key)
        if value is None:
            continue
        result[key] = normalize(str(value), key in cli_keys)

    return result


def resolve_parameters(
    *,
    config_path_str: str | None,
    cli_overrides: Dict[str, Any],
    env: Mapping[str, str] | None = None,
) -> Tuple[Dict[str, Any], str, Path | None]:
    """Resolve parameters with precedence CLI > ENV > config > defaults.

    Returns (resolved_params, params_hash, config_path)
    """
    config_path = Path(config_path_str).resolve() if config_path_str else None
    file_cfg = _read_config_file(config_path) if config_path else {}
    env_map = _collect_env_vars(env or os.environ)

    defaults: Dict[str, Any] = {
        "colors": "auto",
        "log_level": "INFO",
        "log_format": "text",
        "stats_engine": "wilson_hilferty",
        # prefer simple defaults per README
        "uniformity": "strict",
        "unique_scope": ["row_sets"],
    }

    # Merge: config > defaults, then ENV, then CLI
    merged = _apply_overrides(defaults, file_cfg)
    merged = _apply_overrides(merged, env_map)
    merged = _apply_overrides(merged, cli_overrides)

    # Normalize paths per policy
    merged = resolve_paths(merged, config_path, cli_overrides)

    # Compute params hash from contract subset
    params_hash = compute_params_hash(merged)
    return merged, params_hash, config_path
