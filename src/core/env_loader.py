"""Loaders that inject the local env var JSON files into os.environ."""

import json
import os
from pathlib import Path

LOCAL_ENV_VARS_DIR = Path(__file__).parent / "env_vars" / "LOCAL"
SHARED_ENV_VARS_FILE = LOCAL_ENV_VARS_DIR / "env_vars_LOCAL.json"


def read_env_file(path: Path) -> dict[str, str]:
    """Return the non-empty variables of a JSON env var file as a name to value mapping."""
    with open(path, "r", encoding="utf-8") as f:
        env_vars = json.load(f)
    return {var["name"]: var["value"] for var in env_vars if var.get("name") and var.get("value")}


def inject(env_vars: dict[str, str]) -> None:
    """Set the variables in os.environ, without overriding existing ones."""
    for name, value in env_vars.items():
        if not os.getenv(name):
            os.environ[name] = value


def load_shared_env_file(path: Path = SHARED_ENV_VARS_FILE) -> None:
    """Inject only the shared variables (API keys, endpoints etc.), not the agent ones."""
    inject(read_env_file(path))


def load_env_files(folder: Path = LOCAL_ENV_VARS_DIR) -> None:
    """Inject the variables of every JSON file in the folder, failing on names defined twice."""
    files = sorted(folder.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No env var files found in {folder}")

    seen: dict[str, str] = {}
    for path in files:
        env_vars = read_env_file(path)
        for name in env_vars:
            if name in seen:
                raise ValueError(f"Duplicate env var {name} in {path.name} and {seen[name]}")
            seen[name] = path.name
        inject(env_vars)
