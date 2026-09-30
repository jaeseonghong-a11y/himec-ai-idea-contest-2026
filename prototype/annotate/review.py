"""Record a human decision on each extracted change.

Approval is the gate in front of stage C, so this module refuses to mark
anything `confirmed` that stage C is not allowed to apply. Non-executable but
well-grounded items stay `needs_review`: they are shown on the PDF and carried
into the report, and they are never propagated to a drawing.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..extract.core import ExtractionError, is_executable, write_changes

DECISIONS = ("approve", "reject", "skip")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()


def apply_decision(item: dict, decision: str, reviewer: str, when: str) -> dict:
    """Return a copy of `item` carrying the reviewer's decision."""
    if decision not in DECISIONS:
        raise ExtractionError(f"decision must be one of {DECISIONS}")
    updated = dict(item)
    if decision == "skip":
        return updated
    if decision == "reject":
        updated["status"] = "rejected"
    elif is_executable(item):
        updated["status"] = "confirmed"
    else:
        # Approving a review-only item must not hand stage C a change it would
        # refuse. The decision is still recorded against `needs_review`.
        updated["status"] = "needs_review"
    updated["reviewer"] = reviewer
    updated["reviewed_at"] = when
    return updated


def review(changes: dict, decisions: dict[str, str], reviewer: str, when: str | None = None) -> dict:
    """Apply `decisions` (change id -> decision) to a changes document."""
    if not reviewer or not reviewer.strip():
        raise ExtractionError("reviewer is required")
    items = changes.get("items")
    if not isinstance(items, list):
        raise ExtractionError("changes items must be a list")
    known = {item.get("id") for item in items if isinstance(item, dict)}
    unknown = sorted(set(decisions) - known)
    if unknown:
        raise ExtractionError(f"unknown change ids: {', '.join(unknown)}")

    stamped = when or now_iso()
    reviewed = [
        apply_decision(item, decisions.get(item.get("id"), "skip"), reviewer.strip(), stamped)
        for item in items
    ]
    confirmed = [item for item in reviewed if item["status"] == "confirmed"]
    if len(confirmed) > 1:
        raise ExtractionError("stage C accepts at most one confirmed change")

    updated = dict(changes)
    updated["items"] = reviewed
    return updated


def prompt_decisions(items: list[dict], read_line=input, write=print) -> dict[str, str]:
    """Ask the reviewer about each item that is still open."""
    decisions: dict[str, str] = {}
    for item in items:
        if item.get("status") in {"confirmed", "rejected", "applied"}:
            continue
        target = (item.get("target") or {}).get("tag") or "미확정"
        write(f"\n[{item.get('id')}] {item.get('sheet') or '도면 미확정'} / {target}")
        write(f"  근거: {(item.get('source') or {}).get('quote', '')}")
        write(f"  요청: {item.get('action')} {item.get('params')}")
        if not is_executable(item):
            write("  주의: 실행 범위 밖입니다. 승인해도 도면에 반영되지 않고 검토 기록만 남습니다.")
        while True:
            answer = read_line("  승인(a) / 기각(r) / 보류(s): ").strip().lower()
            if answer in {"a", "approve"}:
                decisions[item["id"]] = "approve"
                break
            if answer in {"r", "reject"}:
                decisions[item["id"]] = "reject"
                break
            if answer in {"s", "skip", ""}:
                decisions[item["id"]] = "skip"
                break
            write("  a, r, s 중에서 입력하세요.")
    return decisions


def save(path: Path, changes: dict) -> None:
    write_changes(path, changes)
