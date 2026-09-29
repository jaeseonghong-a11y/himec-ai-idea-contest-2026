"""Narrow, audited C1-move demo for synthetic drawings.

This is not a DWG editor or engineering safety checker. No input DXF is saved.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import ezdxf


SHEETS = ("A-101", "A-301")


class UnsafeChange(ValueError):
    """The requested change is outside the reviewed demo contract."""


@dataclass(frozen=True)
class MoveResult:
    sheet: str
    handle: str
    before: tuple[float, float]
    after: tuple[float, float]


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise UnsafeChange(f"JSON object required: {path}")
    return value


def _approved_move(changes: dict) -> dict:
    if changes.get("schema_version") != 1:
        raise UnsafeChange("changes schema_version must be 1")
    if changes.get("mode") not in {"live_api", "fixture_replay"}:
        raise UnsafeChange("changes mode is missing or unknown")
    items = changes.get("items")
    if not isinstance(items, list):
        raise UnsafeChange("changes items must be a list")
    approved = [item for item in items if isinstance(item, dict) and item.get("status") == "confirmed"]
    if len(approved) != 1:
        raise UnsafeChange("exactly one confirmed change is required")
    change = approved[0]
    if not change.get("reviewer") or not change.get("reviewed_at"):
        raise UnsafeChange("confirmed change needs reviewer and reviewed_at")
    target = change.get("target")
    if not isinstance(target, dict) or change.get("sheet") != "A-101" or target.get("tag") != "C1":
        raise UnsafeChange("only the A-101 C1 target is supported")
    if change.get("action") != "move" or change.get("params") != {"dx_mm": 0, "dy_mm": 500}:
        raise UnsafeChange("only C1 Y+500 mm move is supported")
    if not change.get("source", {}).get("quote"):
        raise UnsafeChange("source quote is required")
    return change


def _locate(doc, sidecar: dict, sheet: str):
    if sidecar.get("schema_version") != 1 or sidecar.get("sheet_id") != sheet:
        raise UnsafeChange(f"invalid sidecar for {sheet}")
    if sidecar.get("unit") != "mm":
        raise UnsafeChange(f"sidecar {sheet} must use mm")
    objects = sidecar.get("objects")
    if not isinstance(objects, list):
        raise UnsafeChange(f"{sheet} objects must be a list")
    matches = [obj for obj in objects if isinstance(obj, dict) and obj.get("tag") == "C1"]
    if len(matches) != 1:
        raise UnsafeChange(f"{sheet} needs exactly one C1 mapping")
    handle = matches[0].get("handle")
    if not isinstance(handle, str) or not handle:
        raise UnsafeChange(f"{sheet} C1 handle missing")
    entity = doc.entitydb.get(handle)
    if entity is None or entity.dxftype() != "INSERT" or entity not in doc.modelspace():
        raise UnsafeChange(f"{sheet} C1 handle is not a modelspace INSERT")
    if entity.dxf.name != "C1" and not any(attr.dxf.text == "C1" for attr in entity.attribs):
        raise UnsafeChange(f"{sheet} mapped INSERT is not labeled C1")
    return handle, entity


def apply_approved_move(changes_path: Path, samples_dir: Path, sidecar_dir: Path, out_dir: Path) -> list[MoveResult]:
    """Validate both drawings first, then save modified copies and a report.

    The caller must provide a dedicated output directory. Existing outputs are
    not overwritten, which keeps repeated runs auditable.
    """
    changes = _read_json(changes_path)
    change = _approved_move(changes)
    prepared = []
    for sheet in SHEETS:
        dxf_path = samples_dir / f"{sheet}.dxf"
        sidecar_path = sidecar_dir / f"sidecar_{sheet}.json"
        if not dxf_path.is_file() or not sidecar_path.is_file():
            raise UnsafeChange(f"missing input for {sheet}")
        doc = ezdxf.readfile(dxf_path)
        handle, entity = _locate(doc, _read_json(sidecar_path), sheet)
        if sheet == "A-101" and change["target"].get("handle") not in (None, handle):
            raise UnsafeChange("change target handle does not match A-101 sidecar")
        before = (float(entity.dxf.insert.x), float(entity.dxf.insert.y))
        prepared.append((sheet, doc, handle, entity, before))

    out_dir = out_dir.resolve()
    if out_dir == samples_dir.resolve() or out_dir == sidecar_dir.resolve():
        raise UnsafeChange("output directory must differ from inputs")
    output_paths = [out_dir / f"modified_{sheet}.dxf" for sheet in SHEETS]
    output_paths.append(out_dir / "report.md")
    if any(path.exists() for path in output_paths):
        raise UnsafeChange("output exists; choose a new output directory")
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for sheet, doc, handle, entity, before in prepared:
        entity.dxf.insert = (before[0], before[1] + 500, float(entity.dxf.insert.z))
        after = (float(entity.dxf.insert.x), float(entity.dxf.insert.y))
        doc.saveas(out_dir / f"modified_{sheet}.dxf")
        results.append(MoveResult(sheet, handle, before, after))

    lines = [
        "# 합성 DXF 변경 보고서", "",
        f"- 변경 ID: {change.get('id', 'unknown')}",
        f"- 입력 방식: {changes['mode']} / 제공자: {changes.get('provider') or '없음'}",
        f"- 승인자: {change['reviewer']} / 승인 시각: {change['reviewed_at']}",
        f"- 발화 근거: {change['source']['quote']}",
        "- 범위: 합성 DXF의 C1 INSERT 이동만. 실제 DWG/구조 안전성/설비 간섭 해결 미검증.",
        "", "## 도면별 변경", "",
    ]
    for item in results:
        lines.append(f"- {item.sheet} / handle {item.handle}: {item.before} → {item.after} mm")
    lines.extend([
        "", "## 규칙 검사와 미해결 사항", "",
        "- A-101과 A-301에서 C1 태그가 각각 정확히 하나인지 확인했고, 두 도면 모두 Y+500 mm 이동했다.",
        "- E-201 전기 도면은 자동 수정하지 않았다. 전기·기계·소방 영향은 담당자가 재검토해야 한다.",
        "- B12 보 스팬은 샘플의 기준점·연결 관계가 검증되지 않아 계산하지 않았다. 구조 검토와 대안은 별도 전문 검토가 필요하다.",
        "- LLM 대안 생성은 이 실행 경로에서 수행하지 않았다.", "",
    ])
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return results
