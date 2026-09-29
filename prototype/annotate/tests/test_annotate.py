import json
import re
import tempfile
import unittest
from pathlib import Path

from prototype.annotate import core, review as review_module
from prototype.annotate.pdfstamp import Annotation, PdfStampError, _find_objects, stamp
from prototype.extract.core import ExtractionError, load_sidecars, load_transcript, normalize_items
from prototype.extract.providers import replay_fixture

FIXTURES = Path(__file__).resolve().parents[2] / "extract" / "fixtures"


def minimal_pdf(pages: int = 1, page_extra: bytes = b"") -> bytes:
    """A classic-xref PDF with no content streams, built for the stamper tests."""
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [%s] /Count %d >>"
           % (b" ".join(b"%d 0 R" % (3 + i) for i in range(pages)), pages),
    }
    for index in range(pages):
        objects[3 + index] = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842]" + page_extra + b" >>"
        )

    buffer = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for number in sorted(objects):
        offsets[number] = len(buffer)
        buffer.extend(b"%d 0 obj\n" % number + objects[number] + b"\nendobj\n")

    start = len(buffer)
    size = max(objects) + 1
    buffer.extend(b"xref\n0 %d\n0000000000 65535 f \n" % size)
    for number in sorted(objects):
        buffer.extend(b"%010d 00000 n \n" % offsets[number])
    buffer.extend(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (size, start))
    return bytes(buffer)


class PdfStampTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "A-101.pdf"
        self.source.write_bytes(minimal_pdf())
        self.output = self.root / "out" / "annotated_A-101.pdf"
        self.annotation = Annotation(0, (100, 120, 130, 150), "CR-001 / C1", "이동 X +0 mm / Y +500 mm")

    def test_original_bytes_are_preserved_as_a_prefix(self):
        original = self.source.read_bytes()
        stamp(self.source, self.output, [self.annotation])
        written = self.output.read_bytes()
        self.assertTrue(written.startswith(original))
        self.assertGreater(len(written), len(original))

    def test_annotation_is_attached_to_the_page(self):
        stamp(self.source, self.output, [self.annotation])
        objects = _find_objects(self.output.read_bytes())
        self.assertIn(b"/Subtype /Square", objects[4])
        self.assertIn(b"/Annots [4 0 R]", objects[3])

    def test_new_xref_is_incremental(self):
        stamp(self.source, self.output, [self.annotation])
        written = self.output.read_bytes()
        offset = int(re.findall(rb"startxref\s+(\d+)", written)[-1])
        self.assertEqual(written[offset:offset + 4], b"xref")
        self.assertIn(b"/Prev", written[offset:])

    def test_korean_text_is_written_as_utf16_hex(self):
        stamp(self.source, self.output, [self.annotation])
        written = self.output.read_bytes()
        self.assertNotIn("이동".encode("utf-8"), written)
        self.assertIn(("﻿" + "이동").encode("utf-16-be").hex().upper().encode("ascii"), written)

    def test_existing_annots_array_is_merged_not_replaced(self):
        source = self.root / "with_annots.pdf"
        source.write_bytes(minimal_pdf(page_extra=b" /Annots [9 0 R]"))
        stamp(source, self.output, [self.annotation])
        objects = _find_objects(self.output.read_bytes())
        self.assertIn(b"/Annots [9 0 R 4 0 R]", objects[3])

    def test_multiple_pages_keep_document_order(self):
        source = self.root / "two.pdf"
        source.write_bytes(minimal_pdf(pages=2))
        stamp(source, self.output, [Annotation(1, (10, 10, 20, 20), "CR-002", "두 번째 장")])
        objects = _find_objects(self.output.read_bytes())
        self.assertIn(b"/Annots", objects[4])
        self.assertNotIn(b"/Annots", objects[3])

    def test_page_outside_the_document_is_refused(self):
        with self.assertRaises(PdfStampError):
            stamp(self.source, self.output, [Annotation(5, (1, 2, 3, 4), "x", "y")])
        self.assertFalse(self.output.exists())

    def test_empty_annotation_list_is_refused(self):
        with self.assertRaises(PdfStampError):
            stamp(self.source, self.output, [])

    def test_non_pdf_input_is_refused(self):
        bad = self.root / "not.pdf"
        bad.write_bytes(b"hello")
        with self.assertRaises(PdfStampError):
            stamp(bad, self.output, [self.annotation])

    def test_cross_reference_stream_is_refused(self):
        data = bytearray(minimal_pdf())
        data[data.rfind(b"startxref"):] = b"startxref\n0\n%%EOF\n"
        bad = self.root / "xrefstream.pdf"
        bad.write_bytes(bytes(data))
        with self.assertRaises(PdfStampError):
            stamp(bad, self.output, [self.annotation])


class PlanTests(unittest.TestCase):
    def setUp(self):
        transcript = load_transcript(FIXTURES / "transcript_demo.txt")
        self.sidecars = load_sidecars(FIXTURES)
        self.items = normalize_items(
            replay_fixture(FIXTURES / "replay_changes.json"), transcript, self.sidecars
        )
        self.changes = {"schema_version": 1, "mode": "fixture_replay", "provider": None, "items": self.items}

    def test_only_stated_coordinates_are_placed(self):
        placements, warnings = core.plan(self.changes, self.sidecars)
        self.assertEqual([p.change_id for p in placements], ["CR-001"])
        self.assertEqual(placements[0].rect_pt, (100.0, 120.0, 130.0, 150.0))
        self.assertEqual(
            {w.change_id: w.reason for w in warnings},
            {
                "CR-002": core.REASON_NO_RECT,
                "CR-003": core.REASON_NO_TAG,
                "CR-004": core.REASON_NO_SHEET,
            },
        )

    def test_rejected_items_are_dropped_from_the_plan(self):
        self.items[0]["status"] = "rejected"
        placements, warnings = core.plan(self.changes, self.sidecars)
        self.assertEqual(placements, [])
        self.assertNotIn("CR-001", [w.change_id for w in warnings])

    def test_handle_mismatch_becomes_a_warning(self):
        self.items[0]["target"]["handle"] = "ZZ"
        _, warnings = core.plan(self.changes, self.sidecars)
        self.assertEqual(
            next(w for w in warnings if w.change_id == "CR-001").reason, core.REASON_NO_MAPPING
        )

    def test_bad_schema_version_is_rejected(self):
        with self.assertRaises(ExtractionError):
            core.plan({"schema_version": 2, "items": []}, self.sidecars)

    def test_plan_file_records_mode_and_warnings(self):
        placements, warnings = core.plan(self.changes, self.sidecars)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "annotations.json"
            core.write_plan(path, self.changes, placements, warnings)
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["mode"], "fixture_replay")
        self.assertIsNone(payload["provider"])
        self.assertEqual(len(payload["placed"]), 1)
        self.assertEqual(len(payload["warnings"]), 3)

    def test_missing_source_pdf_is_reported_not_raised(self):
        placements, _ = core.plan(self.changes, self.sidecars)
        with tempfile.TemporaryDirectory() as temp:
            results = core.stamp_sheets(placements, Path(temp) / "samples", Path(temp) / "out")
        self.assertIn("원본 PDF 없음", results["A-101"])

    def test_present_source_pdf_is_annotated(self):
        placements, _ = core.plan(self.changes, self.sidecars)
        with tempfile.TemporaryDirectory() as temp:
            samples = Path(temp) / "samples"
            samples.mkdir()
            (samples / "A-101.pdf").write_bytes(minimal_pdf())
            out = Path(temp) / "out"
            results = core.stamp_sheets(placements, samples, out)
            self.assertEqual(results["A-101"], str(out / "annotated_A-101.pdf"))
            self.assertIn(b"/Subtype /Square", (out / "annotated_A-101.pdf").read_bytes())


class ReviewTests(unittest.TestCase):
    def setUp(self):
        transcript = load_transcript(FIXTURES / "transcript_demo.txt")
        sidecars = load_sidecars(FIXTURES)
        items = normalize_items(replay_fixture(FIXTURES / "replay_changes.json"), transcript, sidecars)
        self.changes = {"schema_version": 1, "mode": "fixture_replay", "provider": None, "items": items}

    def test_approving_the_executable_change_confirms_it(self):
        result = review_module.review(self.changes, {"CR-001": "approve"}, "archuni")
        item = result["items"][0]
        self.assertEqual(item["status"], "confirmed")
        self.assertEqual(item["reviewer"], "archuni")
        self.assertRegex(item["reviewed_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")

    def test_approving_a_review_only_item_does_not_reach_stage_c(self):
        result = review_module.review(self.changes, {"CR-002": "approve"}, "archuni")
        item = next(i for i in result["items"] if i["id"] == "CR-002")
        self.assertEqual(item["status"], "needs_review")
        self.assertEqual(item["reviewer"], "archuni")

    def test_rejecting_records_the_reviewer(self):
        result = review_module.review(self.changes, {"CR-004": "reject"}, "archuni")
        item = next(i for i in result["items"] if i["id"] == "CR-004")
        self.assertEqual(item["status"], "rejected")
        self.assertIsNotNone(item["reviewed_at"])

    def test_untouched_items_keep_a_null_reviewer(self):
        result = review_module.review(self.changes, {"CR-001": "approve"}, "archuni")
        for item in result["items"][1:]:
            self.assertIsNone(item["reviewer"])
            self.assertIsNone(item["reviewed_at"])

    def test_stage_c_never_receives_two_confirmed_changes(self):
        extra = dict(self.changes["items"][0])
        extra["id"] = "CR-005"
        changes = dict(self.changes, items=self.changes["items"] + [extra])
        with self.assertRaises(ExtractionError):
            review_module.review(changes, {"CR-001": "approve", "CR-005": "approve"}, "archuni")

    def test_reviewer_is_required(self):
        with self.assertRaises(ExtractionError):
            review_module.review(self.changes, {"CR-001": "approve"}, "  ")

    def test_unknown_change_id_is_rejected(self):
        with self.assertRaises(ExtractionError):
            review_module.review(self.changes, {"CR-999": "approve"}, "archuni")

    def test_prompt_skips_settled_items_and_reads_answers(self):
        self.changes["items"][0]["status"] = "confirmed"
        answers = iter(["a", "zzz", "r", "s"])
        decisions = review_module.prompt_decisions(
            self.changes["items"], read_line=lambda _: next(answers), write=lambda *_: None
        )
        self.assertNotIn("CR-001", decisions)
        self.assertEqual(decisions, {"CR-002": "approve", "CR-003": "reject", "CR-004": "skip"})


if __name__ == "__main__":
    unittest.main()
