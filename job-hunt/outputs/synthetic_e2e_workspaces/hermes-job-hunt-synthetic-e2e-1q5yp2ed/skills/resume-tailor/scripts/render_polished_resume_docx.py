#!/usr/bin/env python3
"""Render polished Japanese resume/CV DOCX artifacts from existing Markdown.

This script belongs to the frozen Hermes Japan job-hunt `resume-tailor` component.

It reads existing Markdown resume/CV artifacts and the Japanese layout profile,
then renders reviewable polished DOCX files.

It does not invent facts, rewrite candidate content, or submit applications.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def xml_text(text: str) -> str:
    return escape(text, {"'": "&apos;", '"': "&quot;"})


def strip_inline_md(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    return text.strip()


def p(text: str = "", style: str | None = None, bullet: bool = False) -> str:
    text = strip_inline_md(text)
    if bullet and text:
        text = f"・{text}"
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    preserve = ' xml:space="preserve"' if text.startswith(" ") or text.endswith(" ") else ""
    return f"<w:p>{ppr}<w:r><w:t{preserve}>{xml_text(text)}</w:t></w:r></w:p>"


def md_to_docx_paragraphs(markdown_text: str) -> str:
    paragraphs: list[str] = []
    in_code = False
    for raw in markdown_text.splitlines():
        line = raw.rstrip()
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            if line:
                paragraphs.append(p(line, style="PlainBody"))
            continue
        if not line:
            paragraphs.append("<w:p/>")
        elif line.startswith("# "):
            paragraphs.append(p(line[2:], style="DocTitle"))
        elif line.startswith("## "):
            paragraphs.append(p(line[3:], style="SectionHeading"))
        elif line.startswith("### "):
            paragraphs.append(p(line[4:], style="SubHeading"))
        elif line.startswith("- ") or line.startswith("* "):
            paragraphs.append(p(line[2:], style="PlainBody", bullet=True))
        elif re.match(r"^\d+\.\s+", line):
            paragraphs.append(p(re.sub(r"^\d+\.\s+", "", line), style="PlainBody", bullet=True))
        elif line.startswith("|") and line.endswith("|"):
            paragraphs.append(p(line, style="CompactBody"))
        else:
            paragraphs.append(p(line, style="PlainBody"))
    return "\n".join(paragraphs)


def content_types() -> str:
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


def root_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""


def doc_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>
"""


def styles(font_family: str, font_size_pt: float) -> str:
    half_points = int(font_size_pt * 2)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:after="100"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="{xml_text(font_family)}" w:eastAsia="{xml_text(font_family)}" w:hAnsi="{xml_text(font_family)}"/><w:sz w:val="{half_points}"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="DocTitle">
    <w:name w:val="DocTitle"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:jc w:val="center"/><w:spacing w:before="120" w:after="220"/></w:pPr>
    <w:rPr><w:b/><w:rFonts w:ascii="{xml_text(font_family)}" w:eastAsia="{xml_text(font_family)}" w:hAnsi="{xml_text(font_family)}"/><w:sz w:val="32"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="SectionHeading">
    <w:name w:val="SectionHeading"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:before="220" w:after="100"/><w:pBdr><w:bottom w:val="single" w:sz="6" w:space="1" w:color="auto"/></w:pBdr></w:pPr>
    <w:rPr><w:b/><w:rFonts w:ascii="{xml_text(font_family)}" w:eastAsia="{xml_text(font_family)}" w:hAnsi="{xml_text(font_family)}"/><w:sz w:val="24"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="SubHeading">
    <w:name w:val="SubHeading"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="120" w:after="80"/></w:pPr>
    <w:rPr><w:b/><w:rFonts w:ascii="{xml_text(font_family)}" w:eastAsia="{xml_text(font_family)}" w:hAnsi="{xml_text(font_family)}"/><w:sz w:val="22"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="PlainBody">
    <w:name w:val="PlainBody"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:after="90" w:line="300" w:lineRule="auto"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="{xml_text(font_family)}" w:eastAsia="{xml_text(font_family)}" w:hAnsi="{xml_text(font_family)}"/><w:sz w:val="{half_points}"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="CompactBody">
    <w:name w:val="CompactBody"/>
    <w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:after="40" w:line="260" w:lineRule="auto"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="{xml_text(font_family)}" w:eastAsia="{xml_text(font_family)}" w:hAnsi="{xml_text(font_family)}"/><w:sz w:val="19"/></w:rPr>
  </w:style>
</w:styles>
"""


def core(title: str) -> str:
    now = now_iso()
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns:dcmitype="http://purl.org/dc/dcmitype/"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{xml_text(title)}</dc:title>
  <dc:creator>Hermes job-hunt resume-tailor</dc:creator>
  <cp:lastModifiedBy>Hermes job-hunt resume-tailor</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>
"""


def app() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
  xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Hermes job-hunt</Application>
</Properties>
"""


def document_xml(title: str, body: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {p(title, style="DocTitle")}
    {body}
    <w:p/>
    {p("人間による確認", style="SectionHeading")}
    {p("本書類は提出前に内容・日付・所属・連絡先・改ページを人間が確認すること。", style="PlainBody")}
    {p("Do not submit by default.", style="PlainBody")}
    {p("Stop before final submission.", style="PlainBody")}
    {p("Explicit human approval is required before any submit action.", style="PlainBody")}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="708" w:footer="708" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>
"""


def write_docx(path: Path, title: str, body: str, font_family: str, font_size_pt: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types())
        zf.writestr("_rels/.rels", root_rels())
        zf.writestr("word/_rels/document.xml.rels", doc_rels())
        zf.writestr("word/document.xml", document_xml(title, body))
        zf.writestr("word/styles.xml", styles(font_family, font_size_pt))
        zf.writestr("docProps/core.xml", core(title))
        zf.writestr("docProps/app.xml", app())


def validate_docx(path: Path) -> None:
    if not path.exists() or path.stat().st_size <= 0:
        raise RuntimeError(f"DOCX output missing or empty: {path}")
    if not zipfile.is_zipfile(path):
        raise RuntimeError(f"DOCX output is not a valid package: {path}")
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
    required = {"[Content_Types].xml", "word/document.xml", "word/styles.xml"}
    missing = required - names
    if missing:
        raise RuntimeError(f"DOCX missing members {sorted(missing)}: {path}")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--basename", required=True)
    parser.add_argument("--profile", default="data/japanese_resume_layout_profile.json")
    args = parser.parse_args(list(argv) if argv is not None else None)

    workspace = Path(args.workspace).resolve()
    basename = args.basename
    profile_path = (workspace / args.profile).resolve() if not Path(args.profile).is_absolute() else Path(args.profile)
    profile = json.loads(profile_path.read_text(encoding="utf-8"))

    resume_dir = workspace / "outputs" / "resumes"
    resume_md = resume_dir / f"{basename}_resume_ja.md"
    cv_md = resume_dir / f"{basename}_cv_ja.md"

    if not resume_md.exists():
        raise FileNotFoundError(f"Missing source Markdown: {resume_md}")
    if not cv_md.exists():
        raise FileNotFoundError(f"Missing source Markdown: {cv_md}")

    rules = profile.get("global_rules", {})
    font_family = rules.get("font_family", "Yu Gothic")
    font_size_pt = float(rules.get("font_size_pt", 10.5))

    outputs = [
        {
            "document_type": "rirekisho",
            "source_markdown": resume_md,
            "output_docx": resume_dir / f"{basename}_rirekisho_polished.docx",
            "title": "履歴書",
        },
        {
            "document_type": "shokumukeirekisho",
            "source_markdown": cv_md,
            "output_docx": resume_dir / f"{basename}_shokumukeirekisho_polished.docx",
            "title": "職務経歴書",
        },
    ]

    generated = []
    for item in outputs:
        body = md_to_docx_paragraphs(item["source_markdown"].read_text(encoding="utf-8"))
        write_docx(item["output_docx"], item["title"], body, font_family, font_size_pt)
        validate_docx(item["output_docx"])
        generated.append(
            {
                "document_type": item["document_type"],
                "source_markdown": rel(item["source_markdown"], workspace),
                "output_docx": rel(item["output_docx"], workspace),
                "status": "created",
            }
        )

    manifest = {
        "job_basename": basename,
        "render_type": "polished_japanese_docx",
        "layout_profile": rel(profile_path, workspace),
        "status": "created",
        "generated_files": generated,
        "human_review_required": True,
        "notes": [
            "Rendered from existing Markdown artifacts.",
            "Candidate facts were not rewritten during rendering.",
            "Human layout and content review is required before submission.",
            "No application submission action was performed.",
        ],
        "created_at": now_iso(),
    }
    manifest_path = resume_dir / f"{basename}_polished_docx_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
