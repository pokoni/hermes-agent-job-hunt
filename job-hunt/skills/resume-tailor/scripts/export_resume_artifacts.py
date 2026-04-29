#!/usr/bin/env python3
"""Export Markdown resume artifacts to minimal DOCX files.

This script is intentionally dependency-free. It writes simple valid OOXML DOCX
packages using only the Python standard library.

Expected inputs:
  outputs/resumes/<job_basename>_resume_ja.md
  outputs/resumes/<job_basename>_cv_ja.md

Generated outputs:
  outputs/resumes/<job_basename>_resume_ja.docx
  outputs/resumes/<job_basename>_cv_ja.docx
  outputs/resumes/<job_basename>_docx_export_manifest.json
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape


@dataclass(frozen=True)
class ExportTarget:
    source_md: Path
    output_docx: Path
    document_type: str


def _xml_text(text: str) -> str:
    return escape(text, {"'": "&apos;", '"': "&quot;"})


def _strip_md_inline(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    return text


def _paragraph_xml(text: str, style: str | None = None, bullet: bool = False) -> str:
    text = _xml_text(_strip_md_inline(text.rstrip()))
    if bullet:
        text = f"• {text}"

    ppr_parts: list[str] = []
    if style:
        ppr_parts.append(f'<w:pStyle w:val="{style}"/>')
    ppr = f"<w:pPr>{''.join(ppr_parts)}</w:pPr>" if ppr_parts else ""
    preserve = ' xml:space="preserve"' if text.startswith(" ") or text.endswith(" ") else ""
    return f"<w:p>{ppr}<w:r><w:t{preserve}>{text}</w:t></w:r></w:p>"


def _markdown_to_body(markdown_text: str) -> str:
    paragraphs: list[str] = []
    in_code_block = False

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip("\n").rstrip()

        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            if line:
                paragraphs.append(_paragraph_xml(line, style="Code"))
            continue

        if not line:
            paragraphs.append("<w:p/>")
            continue

        if line.startswith("# "):
            paragraphs.append(_paragraph_xml(line[2:].strip(), style="Title"))
        elif line.startswith("## "):
            paragraphs.append(_paragraph_xml(line[3:].strip(), style="Heading1"))
        elif line.startswith("### "):
            paragraphs.append(_paragraph_xml(line[4:].strip(), style="Heading2"))
        elif line.startswith("- ") or line.startswith("* "):
            paragraphs.append(_paragraph_xml(line[2:].strip(), bullet=True))
        elif re.match(r"^\d+\.\s+", line):
            paragraphs.append(_paragraph_xml(re.sub(r"^\d+\.\s+", "", line), bullet=True))
        elif line.startswith("|") and line.endswith("|"):
            paragraphs.append(_paragraph_xml(line))
        else:
            paragraphs.append(_paragraph_xml(line))

    return "\n".join(paragraphs)


def _content_types_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""


def _root_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""


def _document_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>
"""


def _styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:after="120"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="21"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:before="120" w:after="240"/></w:pPr>
    <w:rPr><w:b/><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="32"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:before="240" w:after="120"/></w:pPr>
    <w:rPr><w:b/><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="26"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:before="180" w:after="100"/></w:pPr>
    <w:rPr><w:b/><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="23"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Code">
    <w:name w:val="Code"/>
    <w:basedOn w:val="Normal"/>
    <w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:eastAsia="Yu Gothic"/><w:sz w:val="19"/></w:rPr>
  </w:style>
</w:styles>
"""


def _document_xml(markdown_text: str) -> str:
    body = _markdown_to_body(markdown_text)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {body}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="708" w:footer="708" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>
"""


def _core_xml(title: str) -> str:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    title_xml = _xml_text(title)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns:dcmitype="http://purl.org/dc/dcmitype/"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{title_xml}</dc:title>
  <dc:creator>Hermes job-hunt resume-tailor</dc:creator>
  <cp:lastModifiedBy>Hermes job-hunt resume-tailor</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>
"""


def _app_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
  xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Hermes job-hunt</Application>
</Properties>
"""


def write_docx(markdown_text: str, output_path: Path, title: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _content_types_xml())
        zf.writestr("_rels/.rels", _root_rels_xml())
        zf.writestr("word/_rels/document.xml.rels", _document_rels_xml())
        zf.writestr("word/document.xml", _document_xml(markdown_text))
        zf.writestr("word/styles.xml", _styles_xml())
        zf.writestr("docProps/core.xml", _core_xml(title))
        zf.writestr("docProps/app.xml", _app_xml())


def _validate_docx(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(f"DOCX was not created or is empty: {path}")
    with zipfile.ZipFile(path) as zf:
        required = {
            "[Content_Types].xml",
            "_rels/.rels",
            "word/document.xml",
            "word/styles.xml",
            "docProps/core.xml",
            "docProps/app.xml",
        }
        names = set(zf.namelist())
        missing = required - names
        if missing:
            raise RuntimeError(f"DOCX missing required package members: {path}: {sorted(missing)}")


def export_targets(workspace: Path, basename: str) -> list[ExportTarget]:
    resume_dir = workspace / "outputs" / "resumes"
    return [
        ExportTarget(
            source_md=resume_dir / f"{basename}_resume_ja.md",
            output_docx=resume_dir / f"{basename}_resume_ja.docx",
            document_type="resume_ja",
        ),
        ExportTarget(
            source_md=resume_dir / f"{basename}_cv_ja.md",
            output_docx=resume_dir / f"{basename}_cv_ja.docx",
            document_type="cv_ja",
        ),
    ]


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export job-hunt Markdown resume artifacts to DOCX.")
    parser.add_argument("--workspace", default=".", help="Path to job-hunt workspace root.")
    parser.add_argument("--basename", required=True, help="Job basename.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    workspace = Path(args.workspace).resolve()
    basename = args.basename
    targets = export_targets(workspace, basename)

    generated: list[dict] = []
    for target in targets:
        if not target.source_md.exists():
            raise FileNotFoundError(f"Missing source Markdown artifact: {target.source_md}")
        markdown_text = target.source_md.read_text(encoding="utf-8")
        title = f"{basename} {target.document_type}"
        write_docx(markdown_text, target.output_docx, title)
        _validate_docx(target.output_docx)
        generated.append(
            {
                "document_type": target.document_type,
                "source_markdown": str(target.source_md.relative_to(workspace)),
                "output_docx": str(target.output_docx.relative_to(workspace)),
                "status": "created",
            }
        )

    manifest = {
        "job_basename": basename,
        "export_type": "docx",
        "status": "created",
        "generated_files": generated,
        "human_review_required": True,
        "notes": [
            "Generated from Markdown artifacts.",
            "DOCX files require human layout review before submission.",
            "No application submission action was performed.",
        ],
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    manifest_path = workspace / "outputs" / "resumes" / f"{basename}_docx_export_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
