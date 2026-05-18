#!/usr/bin/env python3
"""Pure-stdlib Japanese PDF fallback for resume-tailor exports."""

from __future__ import annotations

import re
import unicodedata
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


FALLBACK_EXPORT_METHOD = "cid_japanese_fallback"


def extract_docx_text(path: Path) -> list[str]:
    """Extract visible paragraph text from a DOCX file."""
    with zipfile.ZipFile(path) as zf:
        xml_bytes = zf.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    lines: list[str] = []
    for paragraph in root.findall(".//w:p", ns):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", ns)).strip()
        if text:
            lines.append(text)
    return lines or [path.stem]


def _display_width(value: str) -> int:
    return sum(2 if unicodedata.east_asian_width(ch) in {"F", "W"} else 1 for ch in value)


def _wrap_visual_line(value: str, max_width: int) -> list[str]:
    if _display_width(value) <= max_width:
        return [value]

    lines: list[str] = []
    current: list[str] = []
    current_width = 0
    for ch in value:
        width = 2 if unicodedata.east_asian_width(ch) in {"F", "W"} else 1
        if current and current_width + width > max_width:
            lines.append("".join(current).rstrip())
            current = []
            current_width = 0
        current.append(ch)
        current_width += width
    if current:
        lines.append("".join(current).rstrip())
    return lines


def _clean_lines(lines: list[str], *, max_width: int) -> list[str]:
    cleaned: list[str] = []
    for raw in lines:
        clean = re.sub(r"\s+", " ", raw).strip()
        if not clean:
            continue
        cleaned.extend(_wrap_visual_line(clean, max_width))
    return cleaned


def _pdf_hex_text(text: str) -> str:
    return text.encode("utf-16-be", errors="replace").hex().upper()


def _text_stream(lines: list[str]) -> bytes:
    content = [
        "BT",
        "/F1 10.5 Tf",
        "48 790 Td",
        "14.5 TL",
    ]
    for line in lines:
        content.append(f"<{_pdf_hex_text(line)}> Tj")
        content.append("T*")
    content.append("ET")
    return "\n".join(content).encode("ascii")


def _stream_object(stream: bytes) -> bytes:
    return b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"


def _to_unicode_cmap() -> bytes:
    return b"""/CIDInit /ProcSet findresource begin
12 dict begin
begincmap
/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def
/CMapName /Hermes-UCS2-Identity def
/CMapType 2 def
1 begincodespacerange
<0000> <FFFF>
endcodespacerange
1 beginbfrange
<0000> <FFFF> <0000>
endbfrange
endcmap
CMapName currentdict /CMap defineresource pop
end
end"""


def _build_pdf(page_lines: list[list[str]]) -> bytes:
    page_count = len(page_lines)
    first_page_obj = 7
    page_object_numbers = [first_page_obj + idx * 2 for idx in range(page_count)]
    content_object_numbers = [first_page_obj + idx * 2 + 1 for idx in range(page_count)]
    kids = " ".join(f"{obj} 0 R" for obj in page_object_numbers)

    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode("ascii"),
        b"<< /Type /Font /Subtype /Type0 /BaseFont /HeiseiKakuGo-W5 /Encoding /UniJIS-UCS2-H /DescendantFonts [4 0 R] /ToUnicode 6 0 R >>",
        b"<< /Type /Font /Subtype /CIDFontType0 /BaseFont /HeiseiKakuGo-W5 /CIDSystemInfo << /Registry (Adobe) /Ordering (Japan1) /Supplement 6 >> /FontDescriptor 5 0 R /DW 1000 >>",
        b"<< /Type /FontDescriptor /FontName /HeiseiKakuGo-W5 /Flags 4 /FontBBox [0 -200 1000 900] /ItalicAngle 0 /Ascent 880 /Descent -120 /CapHeight 700 /StemV 80 >>",
        _stream_object(_to_unicode_cmap()),
    ]

    for page_obj, content_obj, lines in zip(page_object_numbers, content_object_numbers, page_lines):
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_obj} 0 R >>"
            ).encode("ascii")
        )
        objects.append(_stream_object(_text_stream(lines)))

    data = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(data))
        data.extend(f"{idx} 0 obj\n".encode("ascii"))
        data.extend(obj)
        data.extend(b"\nendobj\n")
    xref_offset = len(data)
    data.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    data.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    data.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(data)


def write_cid_japanese_fallback_pdf(
    source_docx: Path,
    output_pdf: Path,
    title: str,
    *,
    review_note: str,
) -> None:
    """Write a readable Japanese PDF from DOCX text using standard PDF CID fonts."""
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    body_lines = _clean_lines(extract_docx_text(source_docx), max_width=88)
    header_lines = _clean_lines(
        [
            title,
            review_note,
            "Layout must be checked against the DOCX before submission.",
            "",
        ],
        max_width=88,
    )
    all_lines = header_lines + body_lines
    lines_per_page = 50
    pages = [all_lines[idx : idx + lines_per_page] for idx in range(0, len(all_lines), lines_per_page)]
    if not pages:
        pages = [[title]]

    output_pdf.write_bytes(_build_pdf(pages))
    if output_pdf.read_bytes()[:5] != b"%PDF-":
        raise RuntimeError(f"Fallback PDF output has invalid header: {output_pdf}")
