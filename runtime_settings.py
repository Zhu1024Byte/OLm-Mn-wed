"""Runtime settings persisted in ``data/settings.json``.

Used by the API enable/disable toggle and the API port configuration
(port changes take effect after a container restart).
"""

import json
import logging
from pathlib import Path

from ..config import settings as app_settings

logger = logging.getLogger("olmwed.settings")

SETTINGS_FILE = Path("data/settings.json")


def load() -> dict:
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save(data: dict) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def api_enabled() -> bool:
    """Effective API-service toggle: runtime setting wins, else env default."""
    return bool(load().get("api_enabled", app_settings.api_enabled))


def api_port() -> int:
    """Effective API port: runtime setting wins, else env default."""
    return int(load().get("api_port", app_settings.api_port))
