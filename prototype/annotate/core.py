"""Decide where a change may be drawn on a PDF, and warn when it may not.

A change is placed only when the sidecar states both a page and a rectangle
for the matched handle. Everything else becomes a warning; this stage never
estimates a coordinate from the drawing itself.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..extract.core import ExtractionError, SidecarEntry, read_json
from .pdfstamp import Annotation, PdfStampError, stamp

SCHEMA_VERSION = 1

REASON_NO_SHEET = "도면 미확정"
REASON_NO_TAG = "대상 객체 미확정"
REASON_NO_MAPPING = "사이드카에 해당 핸들 매핑 없음"
REASON_NO_RECT = "사이드카에 PDF 좌표 없음"


@dataclass(frozen=True)
class Placement:
    change_id: str
    sheet: str
    tag: str
    handle: str
    page: int
    rect_pt: tuple[float, float, float, float]
    label: str
    contents: str


@dataclass(frozen=True)
class Warning_:
    change_id: str
    sheet: str | None
    tag: str | None
    reason: str
    quote: str


def _describe(item: dict) -> str:
    action = item.get("action")
    params = item.get("params") or {}
    if action == "move":
        dx, dy = params.get("dx_mm"), params.get("dy_mm")
        if dx is not None and dy is not None:
            return f"이동 X {dx:+} mm / Y {dy:+} mm"
        return "이동(양 미확정)"
    return "검토 요청"


def plan(changes: dict, sidecars: dict[str, list[SidecarEntry]]) -> tuple[list[Placement], list[Warning_]]:
    if changes.get("schema_version") != SCHEMA_VERSION:
        raise ExtractionError("changes schema_version must be 1")
    items = changes.get("items")
    if not isinstance(items, list):
        raise ExtractionError("changes items must be a list")

    placements: list[Placement] = []
    warnings: list[Warning_] = []
    for item in items:
        if not isinstance(item, dict):
            raise ExtractionError("each change item must be an object")
        change_id = item.get("id") or "unknown"
        sheet = item.get("sheet")
        target = item.get("target") or {}
        tag, handle = target.get("tag"), target.get("handle")
        quote = (item.get("source") or {}).get("quote", "")

        if item.get("status") == "rejected":
            continue
        if not sheet:
            warnings.append(Warning_(change_id, sheet, tag, REASON_NO_SHEET, quote))
            continue
        if not tag:
            warnings.append(Warning_(change_id, sheet, tag, REASON_NO_TAG, quote))
            continue
        entry = next(
            (e for e in sidecars.get(tag, []) if e.sheet == sheet and e.handle == handle),
            None,
        )
        if entry is None:
            warnings.append(Warning_(change_id, sheet, tag, REASON_NO_MAPPING, quote))
            continue
        if entry.pdf_page is None or entry.pdf_rect_pt is None:
            warnings.append(Warning_(change_id, sheet, tag, REASON_NO_RECT, quote))
            continue

        label = f"{change_id} / {tag} / {_describe(item)}"
        contents = f"{label}\n상태: {item.get('status')}\n근거: {quote}"
        placements.append(Placement(
            change_id, sheet, tag, entry.handle, entry.pdf_page,
            tuple(entry.pdf_rect_pt), label, contents,
        ))
    return placements, warnings


def write_plan(path: Path, changes: dict, placements: list[Placement], warnings: list[Warning_]) -> dict:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "mode": changes.get("mode"),
        "provider": changes.get("provider"),
        "placed": [
            {
                "id": p.change_id, "sheet": p.sheet, "tag": p.tag, "handle": p.handle,
                "pdf_page": p.page, "pdf_rect_pt": list(p.rect_pt), "label": p.label,
            }
            for p in placements
        ],
        "warnings": [
            {"id": w.change_id, "sheet": w.sheet, "tag": w.tag, "reason": w.reason, "quote": w.quote}
            for w in warnings
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def stamp_sheets(placements: list[Placement], samples_dir: Path, out_dir: Path) -> dict[str, str]:
    """Write one annotated PDF per sheet. Missing or unsupported PDFs are reported.

    Returns sheet -> result, where the result is the output path or a reason the
    sheet could not be annotated. A failure here never removes the placement
    from the plan; the plan stays the record of what was matched.
    """
    results: dict[str, str] = {}
    by_sheet: dict[str, list[Placement]] = {}
    for placement in placements:
        by_sheet.setdefault(placement.sheet, []).append(placement)

    for sheet, items in sorted(by_sheet.items()):
        source = samples_dir / f"{sheet}.pdf"
        if not source.is_file():
            results[sheet] = f"원본 PDF 없음: {source}"
            continue
        annotations = [Annotation(p.page, p.rect_pt, p.label, p.contents) for p in items]
        output = out_dir / f"annotated_{sheet}.pdf"
        try:
            stamp(source, output, annotations)
        except PdfStampError as error:
            results[sheet] = f"주석 실패: {error}"
            continue
        results[sheet] = str(output)
    return results


def load_changes(path: Path) -> dict:
    return read_json(path)
