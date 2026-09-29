"""Append square annotations to an existing PDF without extra dependencies.

The file is never rewritten in place: the original bytes are copied and an
incremental update section is appended, so the source PDF stays byte-identical
inside the output and the change is auditable.

Scope: classic `xref` tables only, which is what the synthetic sample PDFs use.
Cross-reference streams and object streams (PDF 1.5+) raise `PdfStampError`
rather than producing a file we have not verified.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_OBJ_HEADER = re.compile(rb"(?<![0-9])(\d+)\s+(\d+)\s+obj\b")
_KID_REF = re.compile(rb"(\d+)\s+\d+\s+R")


class PdfStampError(ValueError):
    """The PDF is outside the shape this stamper has been verified against."""


@dataclass(frozen=True)
class Annotation:
    page: int
    rect_pt: tuple[float, float, float, float]
    title: str
    contents: str


def _find_objects(data: bytes) -> dict[int, bytes]:
    """Map object number to its body text (between `obj` and `endobj`)."""
    objects: dict[int, bytes] = {}
    for match in _OBJ_HEADER.finditer(data):
        end = data.find(b"endobj", match.end())
        if end == -1:
            continue
        # A later definition wins, which matches how incremental updates read.
        objects[int(match.group(1))] = data[match.end():end]
    return objects


def _trailer_root(data: bytes) -> int:
    match = re.search(rb"/Root\s+(\d+)\s+\d+\s+R", data)
    if not match:
        raise PdfStampError("trailer has no /Root reference")
    return int(match.group(1))


def _page_numbers(objects: dict[int, bytes], root: int) -> list[int]:
    """Walk /Root -> /Pages -> /Kids so page order is the document's own."""
    root_body = objects.get(root)
    if root_body is None:
        raise PdfStampError("catalog object is missing")
    pages_match = re.search(rb"/Pages\s+(\d+)\s+\d+\s+R", root_body)
    if not pages_match:
        raise PdfStampError("catalog has no /Pages reference")

    ordered: list[int] = []
    seen: set[int] = set()

    def walk(number: int) -> None:
        if number in seen:
            raise PdfStampError("page tree contains a cycle")
        seen.add(number)
        body = objects.get(number)
        if body is None:
            raise PdfStampError(f"page tree object {number} is missing")
        if re.search(rb"/Type\s*/Pages\b", body):
            kids = re.search(rb"/Kids\s*\[(.*?)\]", body, re.DOTALL)
            if not kids:
                raise PdfStampError(f"/Pages object {number} has no /Kids")
            for kid in _KID_REF.finditer(kids.group(1)):
                walk(int(kid.group(1)))
        elif re.search(rb"/Type\s*/Page\b", body):
            ordered.append(number)
        else:
            raise PdfStampError(f"object {number} is neither /Page nor /Pages")

    walk(int(pages_match.group(1)))
    if not ordered:
        raise PdfStampError("document has no pages")
    return ordered


def _utf16_hex(text: str) -> bytes:
    """PDF text string that survives Korean content."""
    return b"<" + (b"\xfe\xff" + text.encode("utf-16-be")).hex().upper().encode("ascii") + b">"


def _annot_object(number: int, annotation: Annotation) -> bytes:
    x0, y0, x1, y1 = annotation.rect_pt
    return (
        b"%d 0 obj\n<< /Type /Annot /Subtype /Square /F 4 "
        b"/Rect [%s %s %s %s] /C [1 0 0] /CA 1 /Border [0 0 2] /T %s /Contents %s >>\nendobj\n"
        % (
            number,
            b"%.3f" % x0, b"%.3f" % y0, b"%.3f" % x1, b"%.3f" % y1,
            _utf16_hex(annotation.title),
            _utf16_hex(annotation.contents),
        )
    )


def _page_with_annots(number: int, body: bytes, refs: list[int]) -> bytes:
    """Re-emit a page object with our annotation references merged in."""
    added = b" ".join(b"%d 0 R" % ref for ref in refs)
    existing = re.search(rb"/Annots\s*\[(.*?)\]", body, re.DOTALL)
    if existing:
        merged = existing.group(1).strip()
        merged = (merged + b" " + added).strip()
        new_body = body[:existing.start()] + b"/Annots [" + merged + b"]" + body[existing.end():]
    elif re.search(rb"/Annots\s+\d+\s+\d+\s+R", body):
        raise PdfStampError("page /Annots is an indirect reference; not supported")
    else:
        close = body.rfind(b">>")
        if close == -1:
            raise PdfStampError(f"page object {number} is not a dictionary")
        new_body = body[:close] + b" /Annots [" + added + b"] " + body[close:]
    return b"%d 0 obj%s\nendobj\n" % (number, new_body.rstrip())


def _xref_section(entries: dict[int, int], size: int, root: int, prev: int, start: int) -> bytes:
    """Classic xref table written as contiguous subsections."""
    lines = [b"xref\n"]
    numbers = sorted(entries)
    run: list[int] = []
    for number in numbers + [None]:
        if run and (number is None or number != run[-1] + 1):
            lines.append(b"%d %d\n" % (run[0], len(run)))
            for item in run:
                lines.append(b"%010d %05d n \n" % (entries[item], 0))
            run = []
        if number is not None:
            run.append(number)
    lines.append(b"trailer\n<< /Size %d /Root %d 0 R /Prev %d >>\nstartxref\n%d\n%%%%EOF\n"
                 % (size, root, prev, start))
    return b"".join(lines)


def stamp(source: Path, output: Path, annotations: list[Annotation]) -> int:
    """Copy `source` to `output` with `annotations` appended. Returns the count."""
    if not annotations:
        raise PdfStampError("no annotations to write")
    data = source.read_bytes()
    if not data.startswith(b"%PDF-"):
        raise PdfStampError(f"not a PDF: {source}")

    tail = data.rfind(b"startxref")
    if tail == -1:
        raise PdfStampError("no startxref")
    prev_match = re.search(rb"startxref\s+(\d+)", data[tail:])
    if not prev_match:
        raise PdfStampError("startxref offset is unreadable")
    prev = int(prev_match.group(1))
    if data[prev:prev + 4] != b"xref":
        raise PdfStampError("cross-reference streams are not supported by this stamper")

    objects = _find_objects(data)
    root = _trailer_root(data)
    pages = _page_numbers(objects, root)

    next_number = max(objects) + 1
    per_page: dict[int, list[int]] = {}
    chunks: list[bytes] = []
    offsets: dict[int, int] = {}
    body = bytearray(data)

    for annotation in annotations:
        if not 0 <= annotation.page < len(pages):
            raise PdfStampError(f"page {annotation.page} is outside the document")
        per_page.setdefault(pages[annotation.page], []).append(next_number)
        chunks.append(_annot_object(next_number, annotation))
        next_number += 1

    for page_number, refs in per_page.items():
        chunks.append(_page_with_annots(page_number, objects[page_number], refs))

    if not body.endswith(b"\n"):
        body.extend(b"\n")
    for chunk in chunks:
        number = int(_OBJ_HEADER.match(chunk).group(1))
        offsets[number] = len(body)
        body.extend(chunk)

    start = len(body)
    body.extend(_xref_section(offsets, next_number, root, prev, start))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(bytes(body))
    return len(annotations)
