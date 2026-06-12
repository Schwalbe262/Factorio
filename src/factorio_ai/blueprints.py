from __future__ import annotations

import base64
import binascii
from collections import Counter
from dataclasses import dataclass
import json
import zlib
from typing import Any, Iterable


class BlueprintDecodeError(ValueError):
    pass


@dataclass(frozen=True)
class BlueprintSummary:
    label: str
    entity_counts: dict[str, int]
    tile_counts: dict[str, int]

    @property
    def entity_total(self) -> int:
        return sum(self.entity_counts.values())


def decode_blueprint_string(text: str) -> dict[str, Any]:
    """Decode a Factorio blueprint exchange string or raw blueprint JSON."""

    payload = text.strip()
    if not payload:
        raise BlueprintDecodeError("blueprint string is empty")

    if payload.startswith("{"):
        return _parse_json(payload)

    if not payload.startswith("0"):
        raise BlueprintDecodeError("blueprint exchange string must start with version byte '0'")

    try:
        compressed = base64.b64decode(payload[1:], validate=True)
        decoded = zlib.decompress(compressed).decode("utf-8")
    except (binascii.Error, zlib.error, UnicodeDecodeError) as exc:
        raise BlueprintDecodeError(f"invalid blueprint exchange string: {exc}") from exc
    return _parse_json(decoded)


def encode_blueprint_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "0" + base64.b64encode(zlib.compress(raw)).decode("ascii")


def iter_blueprints(payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    if isinstance(payload.get("blueprint"), dict):
        yield payload["blueprint"]
        return

    book = payload.get("blueprint_book")
    if not isinstance(book, dict):
        return
    entries = book.get("blueprints")
    if not isinstance(entries, list):
        return
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("blueprint"), dict):
            yield entry["blueprint"]


def summarize_blueprint_payload(payload: dict[str, Any]) -> list[BlueprintSummary]:
    return [summarize_blueprint(blueprint) for blueprint in iter_blueprints(payload)]


def summarize_blueprint(blueprint: dict[str, Any]) -> BlueprintSummary:
    entities = blueprint.get("entities")
    tiles = blueprint.get("tiles")
    entity_counts: Counter[str] = Counter()
    tile_counts: Counter[str] = Counter()

    if isinstance(entities, list):
        for entity in entities:
            if isinstance(entity, dict) and isinstance(entity.get("name"), str):
                entity_counts[entity["name"]] += 1

    if isinstance(tiles, list):
        for tile in tiles:
            if isinstance(tile, dict) and isinstance(tile.get("name"), str):
                tile_counts[tile["name"]] += 1

    return BlueprintSummary(
        label=str(blueprint.get("label") or ""),
        entity_counts=dict(entity_counts),
        tile_counts=dict(tile_counts),
    )


def _parse_json(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BlueprintDecodeError(f"invalid blueprint JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise BlueprintDecodeError("blueprint payload must be a JSON object")
    return parsed
