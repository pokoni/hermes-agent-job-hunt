#!/usr/bin/env python3
"""Generate DOCX and PDF for theme2_7a6b985a95c7 using stdlib only.

This is a standalone generator that does NOT require external dependencies.
It builds valid OOXML DOCX packages and minimal PDFs from existing Markdown.
"""
import json, re, zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

WORKSPACE = Path(__file__).resolve().parent.parent
BASENAME = "theme2_7a6b985a95c7"
RESUME_DIR = WORKSPACE / "outputs" / "resumes"

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def xml_text(text):
    return escape(text, {"'": "&apos;", '"': "&quot;"})

def strip_md(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`([^`]*)`', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', text)
    return text.strip()

def p(text, style=None, bullet=False):
    text = strip_md(text)
    if bullet and text:
        text = f"・{text}"
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    preserve = ' xml:space="preserve"' if text and (text[0] == ' ' or text[-1] == ' ') else ""
    return f"<w:p>{ppr}<w:r><w:t{preserve}>{xml_text(text)}</w:t></w:r></w:p>"

def md_to_body(md_text):
    pars = []
    in_code = False
    for raw in md_text.splitlines():
        line = raw.rstrip()
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            if line: pars.append(p(line, style="PlainBody"))
            continue
        if not line:
            pars.append("<w:p/>")
        elif line.startswith("# "):
            pars.append(p(line[2:], style="DocTitle"))
        elif line.startswith("## "):
            pars.append(p(line[3:], style="SectionHeading"))
        elif line.startswith("### "):
            pars.append(p(line[4:], style="SubHeading"))
        elif line.startswith("- ") or line.startswith("* "):
            pars.append(p(line[2:], style="PlainBody", bullet=True))
        elif re.match(r"^\d+\.\s+", line):
            pars.append(p(re.sub(r"^\d+\.\s+", "", line), style="PlainBody", bullet=True))
        elif line.startswith("|") and line.endswith("|"):
            pars.append(p(line, style="CompactBody"))
        else:
            pars.append(p(line, style="PlainBody"))
    return "\n".join(pars)

def content_types_xml():
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

def root_rels_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""

def doc_rels_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>
"""

def styles_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/><w:qFormat/>
    <w:pPr><w:spacing w:after="100"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="21"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="DocTitle">
    <w:name w:val="DocTitle"/><w:basedOn w:val="Normal"/><w:qFormat/>
    <w:pPr><w:jc w:val="center"/><w:spacing w:before="120" w:after="220"/></w:pPr>
    <w:rPr><w:b/><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="32"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="SectionHeading">
    <w:name w:val="SectionHeading"/><w:basedOn w:val="Normal"/><w:qFormat/>
    <w:pPr><w:spacing w:before="220" w:after="100"/><w:pBdr><w:bottom w:val="single" w:sz="6" w:space="1" w:color="auto"/></w:pBdr></w:pPr>
    <w:rPr><w:b/><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="24"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="SubHeading">
    <w:name w:val="SubHeading"/><w:basedOn w:val="Normal"/><w:qFormat/>
    <w:pPr><w:spacing w:before="120" w:after="80"/></w:pPr>
    <w:rPr><w:b/><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="22"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="PlainBody">
    <w:name w:val="PlainBody"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:after="90" w:line="300" w:lineRule="auto"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="21"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="CompactBody">
    <w:name w:val="CompactBody"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:after="40" w:line="260" w:lineRule="auto"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="19"/></w:rPr>
  </w:style>
</w:styles>
"""

def doc_xml(title, body):
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {p(title, style='DocTitle')}
    {body}
    <w:p/>
    {p('人間による確認', style='SectionHeading')}
    {p('本書類は提出前に内容・日付・所属・連絡先・改ページを人間が確認すること。', style='PlainBody')}
    {p('Do not submit by default.', style='PlainBody')}
    {p('Stop before final submission.', style='PlainBody')}
    {p('Explicit human approval is required before any submit action.', style='PlainBody')}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="708" w:footer="708" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>
"""

def core_xml(title):
    t = xml_text(title)
    n = now_iso()
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns:dcmitype="http://purl.org/dc/dcmitype/"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{t}</dc:title>
  <dc:creator>Hermes job-hunt resume-tailor</dc:creator>
  <cp:lastModifiedBy>Hermes job-hunt resume-tailor</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{n}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{n}</dcterms:modified>
</cp:coreProperties>
"""

def app_xml():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
  xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Hermes job-hunt</Application>
</Properties>
"""

def build_docx(md_text, title, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    body = md_to_body(md_text)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml())
        zf.writestr("_rels/.rels", root_rels_xml())
        zf.writestr("word/_rels/document.xml.rels", doc_rels_xml())
        zf.writestr("word/document.xml", doc_xml(title, body))
        zf.writestr("word/styles.xml", styles_xml())
        zf.writestr("docProps/core.xml", core_xml(title))
        zf.writestr("docProps/app.xml", app_xml())

def write_fallback_pdf(text_lines, output_path, title_label):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    title_short = title_label[:80]
    lines = [title_short, "Generated fallback PDF for review.", "Layout must be checked against DOCX before submission.", ""]
    for raw in text_lines[:58]:
        clean = re.sub(r'\s+', ' ', raw).strip()
        if clean:
            lines.append(clean[:96])
    content_lines = []
    for line in lines:
        esc = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content_lines.append(f"({esc}) Tj")
        content_lines.append("T*")
    stream = "BT\n/F1 11 Tf\n50 790 Td\n13 TL\n" + "\n".join(content_lines) + "\nET"
    stream_bytes = stream.encode("utf-8", errors="replace")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream_bytes)).encode("ascii") + b" >>\nstream\n" + stream_bytes + b"\nendstream",
    ]
    data = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for idx, obj in enumerate(objs, start=1):
        offsets.append(len(data))
        data.extend(f"{idx} 0 obj\n".encode("ascii"))
        data.extend(obj)
        data.extend(b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(objs)+1}\n".encode("ascii"))
    data.extend(b"0000000000 65535 f \n")
    for o in offsets[1:]:
        data.extend(f"{o:010d} 00000 n \n".encode("ascii"))
    data.extend(f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    output_path.write_bytes(bytes(data))

def extract_text_from_md(md_path):
    text = md_path.read_text(encoding="utf-8")
    lines = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.strip().startswith("```"):
            continue
        clean = strip_md(line)
        if clean:
            lines.append(clean)
    return lines

def main():
    print(f"Generating DOCX and PDF artifacts for {BASENAME}...")
    resume_md = RESUME_DIR / f"{BASENAME}_resume_ja.md"
    cv_md = RESUME_DIR / f"{BASENAME}_cv_ja.md"

    if not resume_md.exists():
        print(f"ERROR: {resume_md} not found"); return 1
    if not cv_md.exists():
        print(f"ERROR: {cv_md} not found"); return 1

    print("  Building resume DOCX...")
    resume_docx = RESUME_DIR / f"{BASENAME}_resume_ja.docx"
    build_docx(resume_md.read_text(encoding="utf-8"), f"{BASENAME} resume_ja", resume_docx)
    print(f"    -> {resume_docx} ({resume_docx.stat().st_size} bytes)")

    print("  Building CV DOCX...")
    cv_docx = RESUME_DIR / f"{BASENAME}_cv_ja.docx"
    build_docx(cv_md.read_text(encoding="utf-8"), f"{BASENAME} cv_ja", cv_docx)
    print(f"    -> {cv_docx} ({cv_docx.stat().st_size} bytes)")

    print("  Building resume PDF (fallback)...")
    resume_pdf = RESUME_DIR / f"{BASENAME}_resume_ja.pdf"
    write_fallback_pdf(extract_text_from_md(resume_md), resume_pdf, f"{BASENAME} resume_ja")
    print(f"    -> {resume_pdf} ({resume_pdf.stat().st_size} bytes)")

    print("  Building CV PDF (fallback)...")
    cv_pdf = RESUME_DIR / f"{BASENAME}_cv_ja.pdf"
    write_fallback_pdf(extract_text_from_md(cv_md), cv_pdf, f"{BASENAME} cv_ja")
    print(f"    -> {cv_pdf} ({cv_pdf.stat().st_size} bytes)")

    docx_manifest = {
        "job_basename": BASENAME, "export_type": "docx", "status": "created",
        "generated_files": [
            {"document_type": "resume_ja", "source_markdown": f"outputs/resumes/{BASENAME}_resume_ja.md", "output_docx": f"outputs/resumes/{BASENAME}_resume_ja.docx", "status": "created"},
            {"document_type": "cv_ja", "source_markdown": f"outputs/resumes/{BASENAME}_cv_ja.md", "output_docx": f"outputs/resumes/{BASENAME}_cv_ja.docx", "status": "created"},
        ],
        "human_review_required": True,
        "notes": ["Generated from Markdown artifacts.", "DOCX files require human layout review before submission.", "No application submission action was performed."],
        "created_at": now_iso(),
    }
    (RESUME_DIR / f"{BASENAME}_docx_export_manifest.json").write_text(
        json.dumps(docx_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("  DOCX export manifest written.")

    pdf_manifest = {
        "job_basename": BASENAME, "export_type": "pdf", "status": "created",
        "converter": "stdlib_fallback", "export_method": "stdlib_fallback",
        "generated_files": [
            {"document_type": "resume_ja", "source_docx": f"outputs/resumes/{BASENAME}_resume_ja.docx", "output_pdf": f"outputs/resumes/{BASENAME}_resume_ja.pdf", "status": "created", "export_method": "stdlib_fallback"},
            {"document_type": "cv_ja", "source_docx": f"outputs/resumes/{BASENAME}_cv_ja.docx", "output_pdf": f"outputs/resumes/{BASENAME}_cv_ja.pdf", "status": "created", "export_method": "stdlib_fallback"},
        ],
        "human_review_required": True,
        "notes": ["Generated from DOCX resume artifacts.", "Stdlib fallback PDF (not layout-faithful).", "PDF files require human visual review before submission.", "No application submission action was performed."],
        "created_at": now_iso(),
    }
    (RESUME_DIR / f"{BASENAME}_pdf_export_manifest.json").write_text(
        json.dumps(pdf_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("  PDF export manifest written.")
    print("\nAll exports complete!")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
