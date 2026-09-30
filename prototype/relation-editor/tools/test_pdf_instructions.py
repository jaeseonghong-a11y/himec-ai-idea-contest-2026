"""Safety checks for locating a column named in a change-list PDF."""

import unittest

import ezdxf

from pdf_instructions import find_by_handle, find_target


class ColumnTargetTests(unittest.TestCase):
    def setUp(self):
        self.doc = ezdxf.new()
        self.msp = self.doc.modelspace()
        self.doc.blocks.new("COLUMN")
        self.doc.blocks.new("FURNITURE")
        self.column = self.msp.add_blockref("COLUMN", (500, 0))
        self.other = self.msp.add_blockref("FURNITURE", (0, 0))
        self.msp.add_text("C1", dxfattribs={"insert": (0, -100)})

    def test_tag_never_selects_closer_non_column_block(self):
        target, count = find_target(self.doc, "C1")
        self.assertEqual(count, 1)
        self.assertEqual(target["handle"], self.column.dxf.handle)

    def test_handle_never_selects_non_column_block(self):
        self.assertIsNone(find_by_handle(self.doc, self.other.dxf.handle))
        target, count = find_target(self.doc, "C1", self.other.dxf.handle)
        self.assertEqual(count, 1)
        self.assertEqual(target["handle"], self.column.dxf.handle)

    def test_only_col_layer_rectangle_is_column(self):
        self.msp.delete_entity(self.column)
        outline = self.msp.add_lwpolyline(
            [(350, -150), (650, -150), (650, 150), (350, 150)],
            close=True,
            dxfattribs={"layer": "COL"},
        )
        target, count = find_target(self.doc, "C1")
        self.assertEqual(count, 1)
        self.assertEqual(target["handle"], outline.dxf.handle)


if __name__ == "__main__":
    unittest.main()
