from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


SELECTED_IMPROVEMENT_SITE_FILE = "layout-improvement-target.json"


def selected_improvement_site_path(runtime_dir: Path) -> Path:
    return Path(runtime_dir) / SELECTED_IMPROVEMENT_SITE_FILE


def load_selected_improvement_site(runtime_dir: Path, objective: str = "launch_rocket_program") -> dict[str, Any]:
    path = selected_improvement_site_path(runtime_dir)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    selected = sanitize_selected_improvement_site(data)
    if not selected:
        return {}
    stored_objective = str(selected.get("objective") or "")
    if stored_objective and stored_objective != objective:
        return {}
    return selected


def save_selected_improvement_site(
    runtime_dir: Path,
    objective: str,
    site: dict[str, Any],
    *,
    selected_at: str | None = None,
) -> Path:
    selected = sanitize_selected_improvement_site(site)
    if not selected:
        raise ValueError("selected improvement site requires a site_id")
    selected["objective"] = objective
    selected["source"] = str(selected.get("source") or "operator")
    selected["selected_at"] = selected_at or datetime.now(timezone.utc).isoformat()
    runtime = Path(runtime_dir)
    runtime.mkdir(parents=True, exist_ok=True)
    path = selected_improvement_site_path(runtime)
    path.write_text(json.dumps(selected, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def clear_selected_improvement_site(runtime_dir: Path, objective: str = "launch_rocket_program") -> bool:
    path = selected_improvement_site_path(runtime_dir)
    if not path.exists():
        return False
    if not load_selected_improvement_site(runtime_dir, objective):
        return False
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    return True


def selected_improvement_site_from_form(values: dict[str, list[str]]) -> dict[str, Any]:
    site_id = _first(values, "site_id", "improvement_site_id")
    site: dict[str, Any] = {
        "site_id": site_id,
        "kind": _first(values, "site_kind", "kind"),
        "item": _first(values, "site_item", "item"),
        "status": _first(values, "site_status", "status"),
        "automation_level": _first(values, "site_automation_level", "automation_level"),
        "source": "operator",
    }
    position = _position_from_values(values)
    if position:
        site["position"] = position
    return sanitize_selected_improvement_site(site)


def sanitize_selected_improvement_site(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    site_id = str(value.get("site_id") or "").strip()
    if not site_id:
        return {}
    selected: dict[str, Any] = {"site_id": site_id}
    for key in ("objective", "kind", "item", "status", "automation_level", "source", "selected_at"):
        raw = value.get(key)
        if raw not in (None, ""):
            selected[key] = str(raw)
    position = _sanitize_position(value.get("position"))
    if position:
        selected["position"] = position
    return selected


def _position_from_values(values: dict[str, list[str]]) -> dict[str, float]:
    x_raw = _first(values, "site_position_x", "position_x")
    y_raw = _first(values, "site_position_y", "position_y")
    return _sanitize_position({"x": x_raw, "y": y_raw})


def _sanitize_position(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    try:
        return {
            "x": round(float(value.get("x") or 0.0), 3),
            "y": round(float(value.get("y") or 0.0), 3),
        }
    except (TypeError, ValueError):
        return {}


def _first(values: dict[str, list[str]], *keys: str) -> str:
    for key in keys:
        raw_values = values.get(key) or []
        if raw_values:
            return str(raw_values[0])
    return ""
