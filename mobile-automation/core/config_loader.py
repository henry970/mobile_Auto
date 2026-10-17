"""Loads config/config.yaml and applies command-line overrides."""
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"


def load_config(overrides: dict | None = None) -> dict:
    with open(CONFIG_FILE, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    overrides = overrides or {}
    if overrides.get("app"):
        cfg["app"]["path"] = overrides["app"]
    if overrides.get("package"):
        cfg["app"]["package"] = overrides["package"]
    if overrides.get("activity"):
        cfg["app"]["activity"] = overrides["activity"]
    if overrides.get("device"):
        cfg["device"]["udid"] = overrides["device"]
    if overrides.get("server"):
        cfg["appium"]["server_url"] = overrides["server"]

    app_path = Path(cfg["app"]["path"])
    if not app_path.is_absolute():
        app_path = PROJECT_ROOT / app_path
    cfg["app"]["path"] = str(app_path)
    return cfg
