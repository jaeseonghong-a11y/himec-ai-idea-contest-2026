import json
import tempfile
import unittest
from pathlib import Path

import ezdxf

from prototype.propagate.core import UnsafeChange, apply_approved_move


class PropagationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.samples = self.root / "samples"
        self.sidecars = self.root / "sidecars"
        self.samples.mkdir()
        self.sidecars.mkdir()
        for sheet in ("A-101", "A-301"):
            doc = ezdxf.new()
            doc.blocks.new("C1")
            entity = doc.modelspace().add_blockref("C1", (100, 200))
            doc.saveas(self.samples / f"{sheet}.dxf")
            self.write_json(self.sidecars / f"sidecar_{sheet}.json", {
                "schema_version": 1, "sheet_id": sheet, "unit": "mm",
                "objects": [{"handle": entity.dxf.handle, "tag": "C1"}],
            })
        self.changes = self.root / "changes.json"
        self.item = {
            "id": "CR-001", "source": {"quote": "C1 위로 500"},
            "sheet": "A-101", "target": {"tag": "C1"}, "action": "move",
            "params": {"dx_mm": 0, "dy_mm": 500}, "status": "confirmed",
            "reviewer": "test-reviewer", "reviewed_at": "2026-09-29T11:00:00+09:00",
        }
        self.write_changes([self.item])

    @staticmethod
    def write_json(path, value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def write_changes(self, items):
        self.write_json(self.changes, {"schema_version": 1, "mode": "fixture_replay", "provider": None, "items": items})

    def test_only_copies_move(self):
        out = self.root / "out"
        results = apply_approved_move(self.changes, self.samples, self.sidecars, out)
        self.assertEqual(len(results), 2)
        for sheet in ("A-101", "A-301"):
            original = ezdxf.readfile(self.samples / f"{sheet}.dxf")
            modified = ezdxf.readfile(out / f"modified_{sheet}.dxf")
            self.assertEqual(original.modelspace().query("INSERT")[0].dxf.insert.y, 200)
            self.assertEqual(modified.modelspace().query("INSERT")[0].dxf.insert.y, 700)
        self.assertIn("E-201", (out / "report.md").read_text(encoding="utf-8"))
        with self.assertRaises(UnsafeChange):
            apply_approved_move(self.changes, self.samples, self.sidecars, out)

    def test_unapproved_and_unexpected_changes_do_not_write(self):
        out = self.root / "out"
        self.item["reviewer"] = None
        self.write_changes([self.item])
        with self.assertRaises(UnsafeChange):
            apply_approved_move(self.changes, self.samples, self.sidecars, out)
        self.assertFalse(out.exists())
        self.item["reviewer"] = "test-reviewer"
        self.item["action"] = "delete"
        self.write_changes([self.item])
        with self.assertRaises(UnsafeChange):
            apply_approved_move(self.changes, self.samples, self.sidecars, out)
        self.assertFalse(out.exists())

    def test_missing_mapping_prevents_partial_output(self):
        out = self.root / "out"
        (self.sidecars / "sidecar_A-301.json").unlink()
        with self.assertRaises(UnsafeChange):
            apply_approved_move(self.changes, self.samples, self.sidecars, out)
        self.assertFalse(out.exists())

    def test_duplicate_c1_mapping_prevents_output(self):
        out = self.root / "out"
        path = self.sidecars / "sidecar_A-101.json"
        sidecar = json.loads(path.read_text(encoding="utf-8"))
        sidecar["objects"].append(dict(sidecar["objects"][0]))
        self.write_json(path, sidecar)
        with self.assertRaises(UnsafeChange):
            apply_approved_move(self.changes, self.samples, self.sidecars, out)
        self.assertFalse(out.exists())

    def test_mismatched_target_handle_prevents_output(self):
        out = self.root / "out"
        self.item["target"]["handle"] = "FFFF"
        self.write_changes([self.item])
        with self.assertRaises(UnsafeChange):
            apply_approved_move(self.changes, self.samples, self.sidecars, out)
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
