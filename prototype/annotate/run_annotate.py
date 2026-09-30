"""Annotate the synthetic PDFs and record reviewer decisions.

Examples:
    python prototype/annotate/run_annotate.py
    python prototype/annotate/run_annotate.py --reviewer archuni --approve CR-001 --reject CR-004
    python prototype/annotate/run_annotate.py --reviewer archuni --interactive
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from prototype.annotate import core, review as review_module  # noqa: E402
from prototype.extract.core import load_sidecars  # noqa: E402

PROTOTYPE = Path(__file__).resolve().parents[1]
FIXTURES = PROTOTYPE / "extract" / "fixtures"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--changes", type=Path, default=PROTOTYPE / "out" / "changes.json")
    parser.add_argument("--sidecars", type=Path, default=FIXTURES)
    parser.add_argument("--samples", type=Path, default=PROTOTYPE / "samples",
                        help="folder holding <sheet>.pdf (A's output once available)")
    parser.add_argument("--output", type=Path, default=PROTOTYPE / "out")
    parser.add_argument("--reviewer", help="name recorded on approved or rejected items")
    parser.add_argument("--approve", nargs="*", default=[], metavar="ID")
    parser.add_argument("--reject", nargs="*", default=[], metavar="ID")
    parser.add_argument("--interactive", action="store_true", help="ask about each open item")
    args = parser.parse_args()

    changes = core.load_changes(args.changes)
    sidecars = load_sidecars(args.sidecars)
    placements, warnings = core.plan(changes, sidecars)

    plan_path = args.output / "annotations.json"
    core.write_plan(plan_path, changes, placements, warnings)
    print(f"모드: {changes.get('mode')} / 제공자: {changes.get('provider') or '없음'}")
    print(f"위치 확정 {len(placements)}건 / 경고 {len(warnings)}건 → {plan_path}")
    for placement in placements:
        print(f"  확정 {placement.change_id} {placement.sheet} p{placement.page} {list(placement.rect_pt)}")
    for warning in warnings:
        print(f"  경고 {warning.change_id} {warning.sheet or '-'}: {warning.reason}")

    for sheet, result in core.stamp_sheets(placements, args.samples, args.output).items():
        print(f"  PDF {sheet}: {result}")

    decisions = {change_id: "approve" for change_id in args.approve}
    decisions.update({change_id: "reject" for change_id in args.reject})
    if args.interactive:
        decisions.update(review_module.prompt_decisions(changes["items"]))
    if not decisions:
        print("검토 결정이 없어 changes.json은 그대로 둡니다.")
        return 0
    if not args.reviewer:
        parser.error("--approve/--reject/--interactive 를 쓰려면 --reviewer 가 필요합니다.")

    reviewed = review_module.review(changes, decisions, args.reviewer)
    review_module.save(args.changes, reviewed)
    for item in reviewed["items"]:
        if item["reviewer"]:
            print(f"  검토 {item['id']} → {item['status']} ({item['reviewer']} {item['reviewed_at']})")
    print(f"갱신: {args.changes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
