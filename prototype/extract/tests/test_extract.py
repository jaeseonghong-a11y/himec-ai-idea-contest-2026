import json
import tempfile
import unittest
from pathlib import Path

from prototype.extract import providers
from prototype.extract.core import (
    ExtractionError,
    build_changes,
    is_executable,
    load_sidecars,
    load_transcript,
    normalize_items,
    transcript_lines,
    write_changes,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


class TranscriptTests(unittest.TestCase):
    def test_demo_transcript_has_five_lines(self):
        records = transcript_lines(load_transcript(FIXTURES / "transcript_demo.txt"))
        self.assertEqual(len(records), 5)
        self.assertEqual(records[1]["speaker"], "synthetic-speaker-2")
        self.assertEqual(records[1]["time"], "00:00:12")

    def test_empty_transcript_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "empty.txt"
            path.write_text("   \n", encoding="utf-8")
            with self.assertRaises(ExtractionError):
                load_transcript(path)


class SidecarTests(unittest.TestCase):
    def test_demo_sidecars_index_by_tag(self):
        index = load_sidecars(FIXTURES)
        self.assertEqual({entry.sheet for entry in index["C1"]}, {"A-101", "A-301"})
        b12 = index["B12"][0]
        self.assertIsNone(b12.pdf_rect_pt)
        self.assertIsNone(b12.pdf_page)

    def test_bad_rect_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sidecar_A-101.json"
            path.write_text(json.dumps({
                "schema_version": 1, "sheet_id": "A-101", "unit": "mm",
                "objects": [{"handle": "1A", "tag": "C1", "pdf_rect_pt": [1, 2]}],
            }), encoding="utf-8")
            with self.assertRaises(ExtractionError):
                load_sidecars(Path(temp))

    def test_non_mm_sidecar_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sidecar_A-101.json"
            path.write_text(json.dumps({
                "schema_version": 1, "sheet_id": "A-101", "unit": "inch", "objects": [],
            }), encoding="utf-8")
            with self.assertRaises(ExtractionError):
                load_sidecars(Path(temp))


class NormalizeTests(unittest.TestCase):
    def setUp(self):
        self.transcript = load_transcript(FIXTURES / "transcript_demo.txt")
        self.sidecars = load_sidecars(FIXTURES)
        self.raw = providers.replay_fixture(FIXTURES / "replay_changes.json")

    def test_demo_yields_four_candidates_with_one_executable(self):
        items = normalize_items(self.raw, self.transcript, self.sidecars)
        self.assertEqual(len(items), 4)
        executable = [item for item in items if is_executable(item)]
        self.assertEqual([item["id"] for item in executable], ["CR-001"])
        self.assertEqual(items[0]["status"], "proposed")
        self.assertEqual(items[0]["target"], {"tag": "C1", "handle": "1A"})

    def test_grounded_but_non_executable_item_needs_review(self):
        items = normalize_items(self.raw, self.transcript, self.sidecars)
        cr002 = next(item for item in items if item["id"] == "CR-002")
        self.assertEqual(cr002["target"], {"tag": "B12", "handle": "2B"})
        self.assertEqual(cr002["status"], "needs_review")

    def test_ambiguous_items_never_get_a_handle(self):
        items = normalize_items(self.raw, self.transcript, self.sidecars)
        for change_id in ("CR-003", "CR-004"):
            item = next(i for i in items if i["id"] == change_id)
            self.assertEqual(item["status"], "needs_review")
            self.assertIsNone(item["target"]["handle"])

    def test_confidence_is_never_invented(self):
        items = normalize_items(self.raw, self.transcript, self.sidecars)
        self.assertTrue(all(item["confidence"] is None for item in items))

    def test_quote_must_come_from_the_transcript(self):
        raw = [dict(self.raw[0])]
        raw[0]["source"] = dict(raw[0]["source"], quote="C1 기둥을 아래로 900 내려주세요.")
        with self.assertRaises(ExtractionError):
            normalize_items(raw, self.transcript, self.sidecars)

    def test_missing_quote_is_rejected(self):
        raw = [dict(self.raw[0])]
        raw[0]["source"] = {"speaker": "synthetic-speaker-2"}
        with self.assertRaises(ExtractionError):
            normalize_items(raw, self.transcript, self.sidecars)

    def test_duplicate_ids_are_rejected(self):
        raw = [dict(self.raw[0]), dict(self.raw[0])]
        with self.assertRaises(ExtractionError):
            normalize_items(raw, self.transcript, self.sidecars)

    def test_ambiguous_sidecar_mapping_is_not_guessed(self):
        sidecars = dict(self.sidecars)
        sidecars["C1"] = list(sidecars["C1"]) + [sidecars["C1"][0]]
        items = normalize_items(self.raw, self.transcript, sidecars)
        self.assertIsNone(items[0]["target"]["handle"])
        self.assertEqual(items[0]["status"], "needs_review")

    def test_empty_item_list_is_rejected(self):
        with self.assertRaises(ExtractionError):
            normalize_items([], self.transcript, self.sidecars)


class ChangesDocumentTests(unittest.TestCase):
    def test_fixture_replay_must_not_claim_a_provider(self):
        with self.assertRaises(ExtractionError):
            build_changes("fixture_replay", "openai", [{"id": "CR-001"}])

    def test_live_api_requires_a_known_provider(self):
        with self.assertRaises(ExtractionError):
            build_changes("live_api", None, [{"id": "CR-001"}])
        with self.assertRaises(ExtractionError):
            build_changes("live_api", "acme", [{"id": "CR-001"}])

    def test_unknown_mode_is_rejected(self):
        with self.assertRaises(ExtractionError):
            build_changes("simulation", None, [{"id": "CR-001"}])

    def test_written_document_round_trips_as_utf8(self):
        transcript = load_transcript(FIXTURES / "transcript_demo.txt")
        items = normalize_items(
            providers.replay_fixture(FIXTURES / "replay_changes.json"),
            transcript, load_sidecars(FIXTURES),
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "out" / "changes.json"
            write_changes(path, build_changes("fixture_replay", None, items))
            reloaded = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(reloaded["mode"], "fixture_replay")
        self.assertIsNone(reloaded["provider"])
        self.assertIn("C1 기둥", reloaded["items"][0]["source"]["quote"])


class ProviderTests(unittest.TestCase):
    def test_each_provider_builds_its_own_wire_format(self):
        for provider in ("openai", "anthropic", "gemini"):
            url, headers, body = providers.build_request(provider, "대본", "KEY", "m")
            self.assertTrue(url.startswith("https://"))
            self.assertIn("대본", json.dumps(body, ensure_ascii=False))
            self.assertNotIn("KEY", json.dumps(body))
            self.assertIn("KEY", json.dumps(headers))

    def test_unknown_provider_is_rejected(self):
        with self.assertRaises(ExtractionError):
            providers.build_request("acme", "대본", "KEY", "m")

    def test_replies_normalize_to_one_items_array(self):
        payloads = {
            "openai": {"choices": [{"message": {"content": '{"items": [{"id": "CR-001"}]}'}}]},
            "anthropic": {"content": [{"text": '```json\n{"items": [{"id": "CR-001"}]}\n```'}]},
            "gemini": {"candidates": [{"content": {"parts": [{"text": '[{"id": "CR-001"}]'}]}}]},
        }
        for provider, payload in payloads.items():
            self.assertEqual(providers.read_reply(provider, payload), [{"id": "CR-001"}])

    def test_unexpected_response_shape_is_reported(self):
        with self.assertRaises(ExtractionError):
            providers.read_reply("openai", {"choices": []})

    def test_non_json_reply_is_reported(self):
        with self.assertRaises(ExtractionError):
            providers.read_reply("openai", {"choices": [{"message": {"content": "죄송합니다"}}]})


if __name__ == "__main__":
    unittest.main()
