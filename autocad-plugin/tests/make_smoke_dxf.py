"""Create a synthetic millimetre drawing for the AutoCAD plug-in smoke test."""

from pathlib import Path

import ezdxf
from ezdxf import units


def main() -> None:
    output = Path(__file__).resolve().parent / "three_columns_mm.dxf"
    drawing = ezdxf.new("R2018", setup=True)
    drawing.units = units.MM
    drawing.header["$INSUNITS"] = units.MM

    column = drawing.blocks.new(name="COLUMN")
    column.add_lwpolyline(
        [(-100, -100), (100, -100), (100, 100), (-100, 100)],
        close=True,
    )

    model = drawing.modelspace()
    for index, x in enumerate((0, 1000, 2000), start=1):
        model.add_blockref("COLUMN", (x, 0), dxfattribs={"layer": "0"})
        model.add_text(
            f"COLUMN {index}",
            dxfattribs={"height": 60, "insert": (x - 100, -220)},
        )

    drawing.saveas(output)
    reopened = ezdxf.readfile(output)
    blocks = list(reopened.modelspace().query("INSERT"))
    assert reopened.header["$INSUNITS"] == units.MM
    assert len(blocks) == 3
    assert [tuple(block.dxf.insert) for block in blocks] == [
        (0.0, 0.0, 0.0),
        (1000.0, 0.0, 0.0),
        (2000.0, 0.0, 0.0),
    ]
    print(output)


if __name__ == "__main__":
    main()
