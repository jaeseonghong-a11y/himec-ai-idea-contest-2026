"""Build `changes.json` from a transcript, via a live provider or a fixture.

Examples:
    python prototype/extract/run_extract.py
    python prototype/extract/run_extract.py --provider openai
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from prototype.extract import core, providers  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transcript", type=Path, default=FIXTURES / "transcript_demo.txt")
    parser.add_argument("--sidecars", type=Path, default=FIXTURES,
                        help="folder holding sidecar_<sheet>.json (A's output once available)")
    parser.add_argument("--fixture", type=Path, default=FIXTURES / "replay_changes.json")
    parser.add_argument("--provider", choices=core.PROVIDERS,
                        help="attempt a live call; falls back to fixture replay on failure")
    parser.add_argument("--model", help="override the provider's default model")
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parents[1] / "out" / "changes.json")
    args = parser.parse_args()

    transcript = core.load_transcript(args.transcript)
    sidecars = core.load_sidecars(args.sidecars)
    if not sidecars:
        print(f"경고: {args.sidecars}에 사이드카가 없어 모든 대상이 미확정 처리됩니다.")

    mode, provider, raw_items = "fixture_replay", None, None
    if args.provider:
        key = providers.resolve_api_key(args.provider)
        if not key:
            print(f"{providers.ENV_KEYS[args.provider]}가 없어 저장된 예시 재생으로 전환합니다.")
        else:
            try:
                raw_items = providers.call_provider(args.provider, transcript, key, args.model)
                mode, provider = "live_api", args.provider
            except core.ExtractionError as error:
                print(f"{error} — 저장된 예시 재생으로 전환합니다.")
    if raw_items is None:
        raw_items = providers.replay_fixture(args.fixture)

    items = core.normalize_items(raw_items, transcript, sidecars)
    core.write_changes(args.output, core.build_changes(mode, provider, items))

    print(f"모드: {mode} / 제공자: {provider or '없음'}")
    for item in items:
        target = item["target"].get("tag") or "미확정"
        handle = item["target"].get("handle") or "핸들 없음"
        print(f"  {item['id']} [{item['status']}] {item['sheet'] or '도면 미확정'} / {target} / {handle}")
    print(f"저장: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
