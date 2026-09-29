"""Turn a synthetic transcript into the contract's `changes.json`.

This module does not decide engineering intent. It validates whatever a
provider (or a stored fixture) proposed against `prototype/CONTRACT.md`, keeps
the quoted evidence, and refuses to invent a drawing target that the sidecar
does not state.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

SCHEMA_VERSION = 1
MODES = ("live_api", "fixture_replay")
PROVIDERS = ("openai", "anthropic", "gemini")
STATUSES = ("proposed", "needs_review", "confirmed", "rejected", "applied")

# `prototype/CONTRACT.md` allows exactly one executable change. Everything else
# is annotated and reviewed but never propagated to a drawing.
EXECUTABLE_SHEET = "A-101"
EXECUTABLE_TAG = "C1"
EXECUTABLE_ACTION = "move"
EXECUTABLE_PARAMS = {"dx_mm": 0, "dy_mm": 500}

_SPEAKER_LINE = re.compile(r"^\[(?P<speaker>[^\]]+)\]\s+(?P<time>\d{2}:\d{2}:\d{2})\s+(?P<text>.+)$")


class ExtractionError(ValueError):
    """The proposed change list is outside the reviewed demo contract."""


@dataclass(frozen=True)
class SidecarEntry:
    sheet: str
    handle: str
    tag: str
    pdf_page: int | None
    pdf_rect_pt: list[float] | None


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ExtractionError(f"JSON object required: {path}")
    return value


def load_transcript(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ExtractionError(f"transcript is empty: {path}")
    return text


def transcript_lines(text: str) -> list[dict]:
    """Split the synthetic transcript into speaker/time/text records.

    Lines that do not carry the synthetic `[speaker] hh:mm:ss` prefix are kept
    as plain text so a differently shaped transcript still round-trips.
    """
    records = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = _SPEAKER_LINE.match(line)
        if match:
            records.append({
                "speaker": match.group("speaker"),
                "time": match.group("time"),
                "text": match.group("text"),
            })
        else:
            records.append({"speaker": None, "time": None, "text": line})
    return records


def load_sidecars(sidecar_dir: Path) -> dict[str, list[SidecarEntry]]:
    """Index sidecar objects by tag. A tag may appear on several sheets."""
    index: dict[str, list[SidecarEntry]] = {}
    for path in sorted(sidecar_dir.glob("sidecar_*.json")):
        sidecar = read_json(path)
        if sidecar.get("schema_version") != SCHEMA_VERSION:
            raise ExtractionError(f"sidecar schema_version must be 1: {path}")
        sheet = sidecar.get("sheet_id")
        if not isinstance(sheet, str) or not sheet:
            raise ExtractionError(f"sidecar sheet_id missing: {path}")
        if sidecar.get("unit") != "mm":
            raise ExtractionError(f"sidecar {sheet} must use mm")
        objects = sidecar.get("objects")
        if not isinstance(objects, list):
            raise ExtractionError(f"sidecar {sheet} objects must be a list")
        for obj in objects:
            if not isinstance(obj, dict):
                raise ExtractionError(f"sidecar {sheet} object must be an object")
            tag = obj.get("tag")
            handle = obj.get("handle")
            if not isinstance(tag, str) or not tag or not isinstance(handle, str) or not handle:
                raise ExtractionError(f"sidecar {sheet} needs tag and handle strings")
            rect = obj.get("pdf_rect_pt")
            if rect is not None and (not isinstance(rect, list) or len(rect) != 4):
                raise ExtractionError(f"sidecar {sheet} pdf_rect_pt must be null or 4 numbers")
            page = obj.get("pdf_page")
            if page is not None and not isinstance(page, int):
                raise ExtractionError(f"sidecar {sheet} pdf_page must be null or an integer")
            index.setdefault(tag, []).append(
                SidecarEntry(sheet, handle, tag, page, [float(v) for v in rect] if rect else None)
            )
    return index


def is_executable(item: dict) -> bool:
    """True only for the single C1 move that stage C is allowed to apply."""
    target = item.get("target")
    return (
        item.get("sheet") == EXECUTABLE_SHEET
        and isinstance(target, dict)
        and target.get("tag") == EXECUTABLE_TAG
        and item.get("action") == EXECUTABLE_ACTION
        and item.get("params") == EXECUTABLE_PARAMS
    )


def _resolve_target(item: dict, sidecars: dict[str, list[SidecarEntry]]) -> tuple[dict, str]:
    """Attach a sidecar handle only when the mapping is stated and unique."""
    target = dict(item.get("target") or {})
    tag = target.get("tag")
    sheet = item.get("sheet")
    if not isinstance(tag, str) or not tag:
        return {"tag": None, "handle": None}, "needs_review"
    matches = [entry for entry in sidecars.get(tag, []) if entry.sheet == sheet]
    if len(matches) != 1:
        # No mapping, or an ambiguous one. Never guess a handle.
        return {"tag": tag, "handle": None}, "needs_review"
    return {"tag": tag, "handle": matches[0].handle}, "proposed"


def normalize_items(raw_items: list, transcript: str, sidecars: dict[str, list[SidecarEntry]]) -> list[dict]:
    """Validate provider output and rebuild it in the contract's shape.

    Every item must quote the transcript verbatim; an item that cannot be
    grounded in the source text is rejected instead of being reworded.
    """
    if not isinstance(raw_items, list) or not raw_items:
        raise ExtractionError("items must be a non-empty list")
    normalized = []
    for index, raw in enumerate(raw_items, start=1):
        if not isinstance(raw, dict):
            raise ExtractionError("each item must be an object")
        source = raw.get("source")
        if not isinstance(source, dict):
            raise ExtractionError("item source must be an object")
        quote = source.get("quote")
        if not isinstance(quote, str) or not quote.strip():
            raise ExtractionError("item source.quote is required")
        if quote not in transcript:
            raise ExtractionError(f"quote is not a substring of the transcript: {quote!r}")
        action = raw.get("action")
        if not isinstance(action, str) or not action:
            raise ExtractionError("item action is required")
        params = raw.get("params")
        if params is None:
            params = {}
        if not isinstance(params, dict):
            raise ExtractionError("item params must be an object")
        impacts = raw.get("impacts") or []
        if not isinstance(impacts, list) or not all(isinstance(v, str) for v in impacts):
            raise ExtractionError("item impacts must be a list of sheet ids")

        item = {
            "id": raw.get("id") if isinstance(raw.get("id"), str) and raw.get("id") else f"CR-{index:03d}",
            "source": {
                "quote": quote,
                "speaker": source.get("speaker"),
                "time": source.get("time"),
            },
            "sheet": raw.get("sheet"),
            "target": None,
            "action": action,
            "params": params,
            # Providers do not return calibrated probabilities, so the contract
            # keeps this null rather than dressing up a model score.
            "confidence": None,
            "status": "proposed",
            "reviewer": None,
            "reviewed_at": None,
            "impacts": impacts,
        }
        target, status = _resolve_target(raw, sidecars)
        item["target"] = target
        item["status"] = status
        if status == "proposed" and not is_executable(item):
            # Grounded, but outside the executable slice: annotate and review only.
            item["status"] = "needs_review"
        normalized.append(item)

    ids = [item["id"] for item in normalized]
    if len(set(ids)) != len(ids):
        raise ExtractionError("item ids must be unique")
    return normalized


def build_changes(mode: str, provider: str | None, items: list[dict]) -> dict:
    if mode not in MODES:
        raise ExtractionError(f"mode must be one of {MODES}")
    if mode == "fixture_replay" and provider is not None:
        raise ExtractionError("fixture_replay must record provider null")
    if mode == "live_api" and provider not in PROVIDERS:
        raise ExtractionError(f"live_api must record one of {PROVIDERS}")
    return {"schema_version": SCHEMA_VERSION, "mode": mode, "provider": provider, "items": items}


def write_changes(path: Path, changes: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(changes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
