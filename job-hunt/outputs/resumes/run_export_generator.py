import base64, json, zipfile, io, re, struct, sys
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

WORKSPACE = Path("/Users/huyaohua/PycharmProjects/hermes-agent-job-hunt/job-hunt")
BASENAME = "生成AIの検索基盤におけるデータリネージ可視化の検討_6f5f758e135b"
RESUME_DIR = WORKSPACE / "outputs" / "resumes"

def x(t): return escape(t, {"'":"&apos;",'"':"&quot;"})
def s(t):
    t=re.sub(r"\*\*(.*?)\*\*",r"\1",t);t=re.sub(r"\*(.*?)\*",r"\1",t)
    t=re.sub(r"`([^`]*)`",r"\1",t);t=re.sub(r"\[([^\]]+)\]\(([^)]+)\)",r"\1 (\2)",t)
    return t
def p(t,st=None,b=False):
    t=x(s(t.rstrip()))
    if b:t=f"\u2022 {t}"
    pp=[f'<w:pStyle w:val="{st}"/>'] if st else []
    ppr=f"<w:pPr>{''.join(pp)}</w:pPr>" if pp else ""
    pr=' xml:space="preserve"' if t.startswith(" ") or t.endswith(" ") else ""
    return f"<w:p>{ppr}<w:r><w:t{pr}>{t}</w:t></w:r></w:p>"
def m2b(md):
    ps=[];ic=False
    for rl in md.splitlines():
        l=rl.rstrip("\n").rstrip()
        if l.strip().startswith("```"):ic=not ic;continue
        if ic:
            if l:ps.append(p(l,st="Code"))
            continue
        if not l:ps.append("<w:p/>");continue
        if l.startswith("# "):ps.append(p(l[2:].strip(),st="Title"))
        elif l.startswith("## "):ps.append(p(l[3:].strip(),st="Heading1"))
        elif l.startswith("### "):ps.append(p(l[4:].strip(),st="Heading2"))
        elif l.startswith("- ") or l.startswith("* "):ps.append(p(l[2:].strip(),b=True))
        elif re.match(r"^\d+\.\s+",l):ps.append(p(re.sub(r"^\d+\.\s+","",l),b=True))
        elif l.startswith("|") and l.endswith("|"):ps.append(p(l))
        else:ps.append(p(l))
    return "\n".join(ps)

def make_docx(md,title):
    b=m2b(md)
    now=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    tx=x(title)
    ct='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>'
    rr='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>'
    dr='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
    dx=f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{b}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr></w:body></w:document>'
    sx='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:after="120"/></w:pPr><w:rPr><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="21"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:before="120" w:after="240"/></w:pPr><w:rPr><w:b/><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="32"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:before="240" w:after="120"/></w:pPr><w:rPr><w:b/><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="26"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:before="180" w:after="100"/></w:pPr><w:rPr><w:b/><w:rFonts w:ascii="Yu Gothic" w:eastAsia="Yu Gothic" w:hAnsi="Yu Gothic"/><w:sz w:val="23"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Code"><w:name w:val="Code"/><w:basedOn w:val="Normal"/><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:eastAsia="Yu Gothic"/><w:sz w:val="19"/></w:rPr></w:style></w:styles>'
    cx=f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>{tx}</dc:title><dc:creator>Hermes job-hunt resume-tailor</dc:creator><cp:lastModifiedBy>Hermes job-hunt resume-tailor</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>'
    ax='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Hermes job-hunt</Application></Properties>'
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w",compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml",ct.encode("utf-8"))
        zf.writestr("_rels/.rels",rr.encode("utf-8"))
        zf.writestr("word/_rels/document.xml.rels",dr.encode("utf-8"))
        zf.writestr("word/document.xml",dx.encode("utf-8"))
        zf.writestr("word/styles.xml",sx.encode("utf-8"))
        zf.writestr("docProps/core.xml",cx.encode("utf-8"))
        zf.writestr("docProps/app.xml",ax.encode("utf-8"))
    return buf.getvalue()

def make_pdf(docx_bytes,doc_type):
    import xml.etree.ElementTree as ET
    buf=io.BytesIO(docx_bytes)
    lines=[]
    with zipfile.ZipFile(buf) as zf:
        root=ET.fromstring(zf.read("word/document.xml"))
    ns={"w":"http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    for p in root.findall(".//w:p",ns):
        t="".join(n.text or "" for n in p.findall(".//w:t",ns)).strip()
        if t:lines.append(t)
    title=f"{BASENAME} {doc_type}"
    cl=["BT","/F1 12 Tf","50 790 Td","14 TL",f"({title[:90].replace('\\\\','\\\\\\\\').replace('(','\\(').replace(')','\\)')}) Tj","T*","(Generated fallback PDF for human review.) Tj","T*","(Layout must be checked against the DOCX before submission.) Tj","T*"]
    for raw in lines[:52]:
        c=re.sub(r"\s+"," ",raw).strip()
        if not c:continue
        e=c[:96].replace("\\","\\\\").replace("(","\\(").replace(")","\\)")
        cl.append(f"({e}) Tj");cl.append("T*")
    cl.append("ET")
    sb="\n".join(cl).encode("utf-8",errors="replace")
    ob=[b"<< /Type /Catalog /Pages 2 0 R >>",b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",b"<< /Length "+str(len(sb)).encode("ascii")+b" >>\nstream\n"+sb+b"\nendstream"]
    data=bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    off=[0]
    for i,o in enumerate(ob,1):
        off.append(len(data))
        data.extend(f"{i} 0 obj\n".encode("ascii"));data.extend(o);data.extend(b"\nendobj\n")
    xo=len(data)
    data.extend(f"xref\n0 {len(ob)+1}\n".encode("ascii"))
    data.extend(b"0000000000 65535 f \n")
    for o in off[1:]:data.extend(f"{o:010d} 00000 n \n".encode("ascii"))
    data.extend(f"trailer\n<< /Size {len(ob)+1} /Root 1 0 R >>\nstartxref\n{xo}\n%%EOF\n".encode("ascii"))
    return bytes(data)

RESUME_DIR.mkdir(parents=True,exist_ok=True)
for dt in ["resume_ja","cv_ja"]:
    mp=RESUME_DIR/f"{BASENAME}_{dt}.md"
    if not mp.exists():print(f"WARNING: {mp} not found");continue
    md=mp.read_text("utf-8")
    title=f"{BASENAME} {dt}"
    db=make_docx(md,title)
    dp=RESUME_DIR/f"{BASENAME}_{dt}.docx"
    dp.write_bytes(db)
    print(f"DOCX: {dp} ({len(db)} bytes)")
    pb=make_pdf(db,dt)
    pp=RESUME_DIR/f"{BASENAME}_{dt}.pdf"
    pp.write_bytes(pb)
    print(f"PDF: {pp} ({len(pb)} bytes)")

now=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
dm={"job_basename":BASENAME,"export_type":"docx","status":"created","generated_files":[{"document_type":"resume_ja","source_markdown":f"outputs/resumes/{BASENAME}_resume_ja.md","output_docx":f"outputs/resumes/{BASENAME}_resume_ja.docx","status":"created"},{"document_type":"cv_ja","source_markdown":f"outputs/resumes/{BASENAME}_cv_ja.md","output_docx":f"outputs/resumes/{BASENAME}_cv_ja.docx","status":"created"}],"human_review_required":True,"notes":["Generated from Markdown artifacts.","DOCX files require human layout review before submission.","No application submission action was performed."],"created_at":now}
(RESUME_DIR/f"{BASENAME}_docx_export_manifest.json").write_text(json.dumps(dm,ensure_ascii=False,indent=2)+"\n","utf-8")
print(f"DOCX manifest written.")

pm={"job_basename":BASENAME,"export_type":"pdf","status":"created","converter":"stdlib_fallback","export_method":"stdlib_fallback","generated_files":[{"document_type":"resume_ja","source_docx":f"outputs/resumes/{BASENAME}_resume_ja.docx","output_pdf":f"outputs/resumes/{BASENAME}_resume_ja.pdf","status":"created","export_method":"stdlib_fallback"},{"document_type":"cv_ja","source_docx":f"outputs/resumes/{BASENAME}_cv_ja.docx","output_pdf":f"outputs/resumes/{BASENAME}_cv_ja.pdf","status":"created","export_method":"stdlib_fallback"}],"human_review_required":True,"notes":["Generated from DOCX resume artifacts.","stdlib fallback PDF used (LibreOffice not available).","PDF files require human visual review before submission.","No application submission action was performed."],"created_at":now}
(RESUME_DIR/f"{BASENAME}_pdf_export_manifest.json").write_text(json.dumps(pm,ensure_ascii=False,indent=2)+"\n","utf-8")
print(f"PDF manifest written.")
print("\n=== All exports complete ===")
