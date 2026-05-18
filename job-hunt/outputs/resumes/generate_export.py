#!/usr/bin/env python3
"""Generate DOCX and PDF files for resume-tailor artifacts.

Usage: python3 generate_export.py

This script reads the Markdown artifacts and creates DOCX/PDF outputs.
"""

import base64
import json
import zipfile
import io
import re
import struct
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

WORKSPACE = Path("/Users/huyaohua/PycharmProjects/hermes-agent-job-hunt/job-hunt")
BASENAME = "生成AIの検索基盤におけるデータリネージ可視化の検討_6f5f758e135b"
RESUME_DIR = WORKSPACE / "outputs" / "resumes"

MARKDOWN_FILES = {
    "resume_ja": RESUME_DIR / f"{BASENAME}_resume_ja.md",
    "cv_ja": RESUME_DIR / f"{BASENAME}_cv_ja.md",
}

DOCX_OUTPUTS = {
    "resume_ja": RESUME_DIR / f"{BASENAME}_resume_ja.docx",
    "cv_ja": RESUME_DIR / f"{BASENAME}_cv_ja.docx",
}

PDF_OUTPUTS = {
    "resume_ja": RESUME_DIR / f"{BASENAME}_resume_ja.pdf",
    "cv_ja": RESUME_DIR / f"{BASENAME}_cv_ja.pdf",
}


def xml_text(text: str) -> str:
    return escape(text, {"'": "&apos;", '"': "&quot;"})


def strip_md(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    return text


def para_xml(text: str, style=None, bullet=False):
    text = xml_text(strip_md(text.rstrip()))
    if bullet:
        text = f"• {text}"
    ppr_parts = []
    if style:
        ppr_parts.append(f'<w:pStyle w:val="{style}"/>')
    ppr = f"<w:pPr>{''.join(ppr_parts)}</w:pPr>" if ppr_parts else ""
    preserve = ' xml:space="preserve"' if text.startswith(" ") or text.endswith(" ") else ""
    return f"<w:p>{ppr}<w:r><w:t{preserve}>{text}</w:t></w:r></w:p>"


def md_to_body(md_text):
    paragraphs = []
    in_code = False
    for raw_line in md_text.splitlines():
        line = raw_line.rstrip("\n").rstrip()
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            if line:
                paragraphs.append(para_xml(line, style="Code"))
            continue
        if not line:
            paragraphs.append("<w:p/>")
            continue
        if line.startswith("# "):
            paragraphs.append(para_xml(line[2:].strip(), style="Title"))
        elif line.startswith("## "):
            paragraphs.append(para_xml(line[3:].strip(), style="Heading1"))
        elif line.startswith("### "):
            paragraphs.append(para_xml(line[4:].strip(), style="Heading2"))
        elif line.startswith("- ") or line.startswith("* "):
            paragraphs.append(para_xml(line[2:].strip(), bullet=True))
        elif re.match(r"^\d+\.\s+", line):
            paragraphs.append(para_xml(re.sub(r"^\d+\.\s+", "", line), bullet=True))
        elif line.startswith("|") and line.endswith("|"):
            paragraphs.append(para_xml(line))
        else:
            paragraphs.append(para_xml(line))
    return "\n".join(paragraphs)


def make_docx(md_text, title):
    body = md_to_body(md_text)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    title_xml = xml_text(title)

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        '</Types>'
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
        '</Relationships>'
    )
    doc_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body>'
        f'{body}'
        '<w:sectPr>'
        '<w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="708" w:footer="708" w:gutter="0"/>'
        '</w:sectPr>'
        '</w:body>'
        '</w:document>'
    )
    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
        '<w:name w:val="Normal"/><w:qFormat/>'
        '<w:pPr><w:spacing w:after="120"/></w:pPr>'
        '<w:rPr><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="21"/></w:rPr>'
        '</w:style>'
        '<w:style w:type="paragraph" w:styleId="Title">'
        '<w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:qFormat/>'
        '<w:pPr><w:spacing w:before="120" w:after="240"/></w:pPr>'
        '<w:rPr><w:b/><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="32"/></w:rPr>'
        '</w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading1">'
        '<w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:qFormat/>'
        '<w:pPr><w:spacing w:before="240" w:after="120"/></w:pPr>'
        '<w:rPr><w:b/><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="26"/></w:rPr>'
        '</w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading2">'
        '<w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:qFormat/>'
        '<w:pPr><w:spacing w:before="180" w:after="100"/></w:pPr>'
        '<w:rPr><w:b/><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="23"/></w:rPr>'
        '</w:style>'
        '<w:style w:type="paragraph" w:styleId="Code">'
        '<w:name w:val="Code"/><w:basedOn w:val="Normal"/>'
        '<w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:eastAsia="Yu Gothic"/><w:sz w:val="19"/></w:rPr>'
        '</w:style>'
        '</w:styles>'
    )
    core_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"'
        ' xmlns:dc="http://purl.org/dc/elements/1.1/"'
        ' xmlns:dcterms="http://purl.org/dc/terms/"'
        ' xmlns:dcmitype="http://purl.org/dc/dcmitype/"'
        ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f'<dc:title>{title_xml}</dc:title>'
        '<dc:creator>Hermes job-hunt resume-tailor</dc:creator>'
        '<cp:lastModifiedBy>Hermes job-hunt resume-tailor</cp:lastModifiedBy>'
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
        '</cp:coreProperties>'
    )
    app_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"'
        ' xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        '<Application>Hermes job-hunt</Application>'
        '</Properties>'
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types.encode("utf-8"))
        zf.writestr("_rels/.rels", root_rels.encode("utf-8"))
        zf.writestr("word/_rels/document.xml.rels", doc_rels.encode("utf-8"))
        zf.writestr("word/document.xml", document_xml.encode("utf-8"))
        zf.writestr("word/styles.xml", styles_xml.encode("utf-8"))
        zf.writestr("docProps/core.xml", core_xml.encode("utf-8"))
        zf.writestr("docProps/app.xml", app_xml.encode("utf-8"))
    return buf.getvalue()


def make_fallback_pdf(docx_bytes, doc_type):
    """Generate a simple text-based fallback PDF from DOCX text."""
    buf = io.BytesIO(docx_bytes)
    lines = []
    with zipfile.ZipFile(buf) as zf:
        xml_bytes = zf.read("word/document.xml")
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_bytes)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    for para in root.findall(".//w:p", ns):
        text = "".join(node.text or "" for node in para.findall(".//w:t", ns)).strip()
        if text:
            lines.append(text)

    title = f"{BASENAME} {doc_type}"
    content_lines = [
        "BT",
        "/F1 12 Tf",
        "50 790 Td",
        "14 TL",
        f"({title[:90].replace('\\\\', '\\\\\\\\').replace('(', '\\\\\\\\(').replace(')', '\\\\\\\\)')}) Tj",
        "T*",
        "(Generated fallback PDF for human review.) Tj",
        "T*",
        "(Layout must be checked against the DOCX before submission.) Tj",
        "T*",
    ]
    for raw in lines[:52]:
        clean = re.sub(r"\s+", " ", raw).strip()
        if not clean:
            continue
        escaped = clean[:96].replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content_lines.append(f"({escaped}) Tj")
        content_lines.append("T*")
    content_lines.append("ET")
    stream = "\n".join(content_lines)
    stream_bytes = stream.encode("utf-8", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream_bytes)).encode("ascii") + b" >>\nstream\n" + stream_bytes + b"\nendstream",
    ]

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


def main():
    RESUME_DIR.mkdir(parents=True, exist_ok=True)

    for doc_type in ["resume_ja", "cv_ja"]:
        md_path = MARKDOWN_FILES[doc_type]
        if not md_path.exists():
            print(f"WARNING: Markdown file not found: {md_path}")
            continue

        md_text = md_path.read_text(encoding="utf-8")
        title = f"{BASENAME} {doc_type}"

        # Generate DOCX
        docx_bytes = make_docx(md_text, title)
        docx_path = DOCX_OUTPUTS[doc_type]
        docx_path.write_bytes(docx_bytes)
        print(f"Created DOCX: {docx_path} ({len(docx_bytes)} bytes)")

        # Generate PDF
        pdf_bytes = make_fallback_pdf(docx_bytes, doc_type)
        pdf_path = PDF_OUTPUTS[doc_type]
        pdf_path.write_bytes(pdf_bytes)
        print(f"Created PDF: {pdf_path} ({len(pdf_bytes)} bytes)")

    # Write docx export manifest
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    docx_manifest = {
        "job_basename": BASENAME,
        "export_type": "docx",
        "status": "created",
        "generated_files": [
            {
                "document_type": "resume_ja",
                "source_markdown": f"outputs/resumes/{BASENAME}_resume_ja.md",
                "output_docx": f"outputs/resumes/{BASENAME}_resume_ja.docx",
                "status": "created",
            },
            {
                "document_type": "cv_ja",
                "source_markdown": f"outputs/resumes/{BASENAME}_cv_ja.md",
                "output_docx": f"outputs/resumes/{BASENAME}_cv_ja.docx",
                "status": "created",
            },
        ],
        "human_review_required": True,
        "notes": [
            "Generated from Markdown artifacts.",
            "DOCX files require human layout review before submission.",
            "No application submission action was performed.",
        ],
        "created_at": now,
    }
    dm_path = RESUME_DIR / f"{BASENAME}_docx_export_manifest.json"
    dm_path.write_text(json.dumps(docx_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Created manifest: {dm_path}")

    # Write pdf export manifest
    pdf_manifest = {
        "job_basename": BASENAME,
        "export_type": "pdf",
        "status": "created",
        "converter": "stdlib_fallback",
        "export_method": "stdlib_fallback",
        "generated_files": [
            {
                "document_type": "resume_ja",
                "source_docx": f"outputs/resumes/{BASENAME}_resume_ja.docx",
                "output_pdf": f"outputs/resumes/{BASENAME}_resume_ja.pdf",
                "status": "created",
                "export_method": "stdlib_fallback",
            },
            {
                "document_type": "cv_ja",
                "source_docx": f"outputs/resumes/{BASENAME}_cv_ja.docx",
                "output_pdf": f"outputs/resumes/{BASENAME}_cv_ja.pdf",
                "status": "created",
                "export_method": "stdlib_fallback",
            },
        ],
        "human_review_required": True,
        "notes": [
            "Generated from DOCX resume artifacts.",
            "stdlib fallback PDF used (LibreOffice not available in this environment).",
            "PDF files require human visual review before submission.",
            "No application submission action was performed.",
        ],
        "created_at": now,
    }
    pm_path = RESUME_DIR / f"{BASENAME}_pdf_export_manifest.json"
    pm_path.write_text(json.dumps(pdf_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Created manifest: {pm_path}")

    print("\n=== All exports complete ===")


if __name__ == "__main__":
    main()
