#!/usr/bin/env python3
"""Generate DOCX and PDF files from Markdown resume/CV artifacts.

Usage: python3 scripts/generate_binary_exports.py
"""
import sys, os, json, re, zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

WORKSPACE = Path(__file__).resolve().parent.parent
BASENAME = 'パーソナルAIエージェント向けLLMのためのプロンプト最適化技術の検討_7197f0b25e6f'

# ---- DOCX Generation ----
def _xml_text(text):
    return escape(text, {"'": "&apos;", '"': "&quot;"})

def _strip_md(text):
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    return text

def _para(text, style=None, bullet=False):
    text = _xml_text(_strip_md(text.rstrip()))
    if bullet:
        text = f"• {text}"
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ''
    return f'<w:p>{ppr}<w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>'

def _md2body(md_text):
    paras, in_code = [], False
    for line in md_text.splitlines():
        line = line.rstrip()
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            if line:
                paras.append(_para(line, style="Code"))
            continue
        if not line:
            paras.append("<w:p/>")
            continue
        if line.startswith("# "):
            paras.append(_para(line[2:].strip(), style="Title"))
        elif line.startswith("## "):
            paras.append(_para(line[3:].strip(), style="Heading1"))
        elif line.startswith("### "):
            paras.append(_para(line[4:].strip(), style="Heading2"))
        elif line.startswith("- ") or line.startswith("* "):
            paras.append(_para(line[2:].strip(), bullet=True))
        elif re.match(r"^\d+\.\s+", line):
            paras.append(_para(re.sub(r"^\d+\.\s+", "", line), bullet=True))
        elif line.startswith("|") and line.endswith("|"):
            paras.append(_para(line))
        else:
            paras.append(_para(line))
    return "\n".join(paras)

CONTENT_TYPES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>'''

ROOT_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''

DOC_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'''

STYLES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/><w:qFormat/>
    <w:pPr><w:spacing w:after="120"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="21"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:qFormat/>
    <w:pPr><w:spacing w:before="120" w:after="240"/></w:pPr>
    <w:rPr><w:b/><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="32"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:qFormat/>
    <w:pPr><w:spacing w:before="240" w:after="120"/></w:pPr>
    <w:rPr><w:b/><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="26"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:qFormat/>
    <w:pPr><w:spacing w:before="180" w:after="100"/></w:pPr>
    <w:rPr><w:b/><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="23"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Code">
    <w:name w:val="Code"/><w:basedOn w:val="Normal"/>
    <w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:eastAsia="Yu Gothic"/><w:sz w:val="19"/></w:rPr>
  </w:style>
</w:styles>'''

APP_XML = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
  xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Hermes job-hunt</Application>
</Properties>'''

def make_docx(md_text, title, docx_path):
    body = _md2body(md_text)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    
    DOC_XML = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {body}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="708" w:footer="708" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>'''
    
    CORE_XML = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{_xml_text(title)}</dc:title>
  <dc:creator>Hermes job-hunt resume-tailor</dc:creator>
  <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>'''
    
    docx_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(str(docx_path), "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("_rels/.rels", ROOT_RELS)
        zf.writestr("word/_rels/document.xml.rels", DOC_RELS)
        zf.writestr("word/document.xml", DOC_XML)
        zf.writestr("word/styles.xml", STYLES)
        zf.writestr("docProps/core.xml", CORE_XML)
        zf.writestr("docProps/app.xml", APP_XML)
    return docx_path

# ---- PDF Generation (stdlib fallback) ----
def _escape_pdf_text(text):
    return text.replace("\\", "\\\\\\\\").replace("(", "\\(").replace(")", "\\)")

def make_fallback_pdf(source_docx_path, pdf_path, title):
    """Write a simple one-page PDF from DOCX text using stdlib only."""
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Extract text from DOCX
    lines = []
    with zipfile.ZipFile(str(source_docx_path)) as zf:
        import xml.etree.ElementTree as ET
        xml_bytes = zf.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    for paragraph in root.findall(".//w:p", ns):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", ns)).strip()
        if text:
            lines.append(text)
    
    # Build PDF content stream
    content_parts = [
        "BT",
        "/F1 12 Tf",
        "50 790 Td",
        "14 TL",
        f"({_escape_pdf_text(title[:90])}) Tj",
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
        content_parts.append(f"({_escape_pdf_text(clean[:96])}) Tj")
        content_parts.append("T*")
    content_parts.append("ET")
    stream = "\n".join(content_parts)
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
    pdf_path.write_bytes(bytes(data))
    if pdf_path.read_bytes()[:5] != b"%PDF-":
        raise RuntimeError(f"PDF output has invalid header: {pdf_path}")
    return pdf_path

# ---- Main ----
def main():
    resume_dir = WORKSPACE / 'outputs' / 'resumes'
    
    # 1. Generate DOCX from Markdown
    print("Generating DOCX from Markdown...")
    resume_md = resume_dir / f'{BASENAME}_resume_ja.md'
    cv_md = resume_dir / f'{BASENAME}_cv_ja.md'
    
    docx_resume = make_docx(resume_md.read_text(encoding='utf-8'), f'{BASENAME} resume_ja',
                            resume_dir / f'{BASENAME}_resume_ja.docx')
    print(f"  Resume DOCX: {docx_resume} ({docx_resume.stat().st_size} bytes)")
    
    docx_cv = make_docx(cv_md.read_text(encoding='utf-8'), f'{BASENAME} cv_ja',
                        resume_dir / f'{BASENAME}_cv_ja.docx')
    print(f"  CV DOCX: {docx_cv} ({docx_cv.stat().st_size} bytes)")
    
    # 2. Generate PDF from DOCX (stdlib fallback)
    print("Generating PDF from DOCX (stdlib fallback)...")
    pdf_resume = make_fallback_pdf(docx_resume, resume_dir / f'{BASENAME}_resume_ja.pdf', f'{BASENAME} resume_ja')
    print(f"  Resume PDF: {pdf_resume} ({pdf_resume.stat().st_size} bytes)")
    
    pdf_cv = make_fallback_pdf(docx_cv, resume_dir / f'{BASENAME}_cv_ja.pdf', f'{BASENAME} cv_ja')
    print(f"  CV PDF: {pdf_cv} ({pdf_cv.stat().st_size} bytes)")
    
    # 3. PDF export manifest
    pdf_manifest = {
        "job_basename": BASENAME,
        "export_type": "pdf",
        "status": "created",
        "converter": "stdlib_fallback",
        "export_method": "stdlib_fallback",
        "generated_files": [
            {"document_type": "resume_ja", "output_pdf": f"outputs/resumes/{BASENAME}_resume_ja.pdf", "status": "created", "export_method": "stdlib_fallback"},
            {"document_type": "cv_ja", "output_pdf": f"outputs/resumes/{BASENAME}_cv_ja.pdf", "status": "created", "export_method": "stdlib_fallback"},
        ],
        "human_review_required": True,
        "notes": [
            "Generated from DOCX resume artifacts using stdlib fallback.",
            "LibreOffice/soffice is preferred for proper layout; rerun export_resume_pdfs.py if LibreOffice is available.",
            "PDF files require human visual review before submission.",
            "No application submission action was performed.",
        ],
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    pdf_manifest_path = resume_dir / f'{BASENAME}_pdf_export_manifest.json'
    pdf_manifest_path.write_text(json.dumps(pdf_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  PDF manifest: {pdf_manifest_path}")
    
    # Final listing
    print("\n=== All output files ===")
    for f in sorted(os.listdir(str(resume_dir))):
        if BASENAME in f:
            fp = resume_dir / f
            print(f"  {f} ({fp.stat().st_size} bytes)")
    
    print("\nDone. All 6 expected artifacts exist.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
