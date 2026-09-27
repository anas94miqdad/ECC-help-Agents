#!/usr/bin/env python3
"""Build a Word manuscript (.docx) from revised Markdown (standard library only).

Supported Markdown subset:
  # / ## / ### headings, paragraphs, blank-line separation
  **bold**, *italic*, ^superscript^, ~subscript~
  "- " bullet items, pipe tables (| a | b |)
  [MISSING: ...] placeholders       -> highlighted yellow
  {>>comment text<<}                -> Word comment on that paragraph
  <!-- ... --> (e.g. src markers)   -> removed from the output

Options for submission formatting: --double-spacing, --line-numbers, --font.
Document metadata (author) is left empty so the file is safe for double-blind review.

To give authors a tracked-changes view, open the ORIGINAL in Word and use
Review > Compare with the generated file (LibreOffice: Edit > Track Changes > Compare).

Usage:
  python3 build_docx.py revised.md --out revised.docx [--double-spacing] [--line-numbers]
"""

import argparse
import datetime
import re
import sys
import zipfile
from xml.sax.saxutils import escape

COMMENT_AUTHOR = "AI revision assistant"
INLINE_RE = re.compile(r"(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|\^[^^\s]+\^|~[^~\s]+~|\[MISSING[^\]]*\])")
COMMENT_RE = re.compile(r"\{>>(.*?)<<\}", re.S)


def _run(text, bold=False, italic=False, vert=None, highlight=False):
    props = ""
    if bold:
        props += "<w:b/>"
    if italic:
        props += "<w:i/>"
    if highlight:
        props += '<w:highlight w:val="yellow"/>'
    if vert:
        props += f'<w:vertAlign w:val="{vert}"/>'
    rpr = f"<w:rPr>{props}</w:rPr>" if props else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def inline_runs(text):
    runs = []
    for part in INLINE_RE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            runs.append(_run(part[2:-2], bold=True))
        elif part.startswith("[MISSING"):
            runs.append(_run(part, bold=True, highlight=True))
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            runs.append(_run(part[1:-1], italic=True))
        elif part.startswith("^") and part.endswith("^") and len(part) > 2:
            runs.append(_run(part[1:-1], vert="superscript"))
        elif part.startswith("~") and part.endswith("~") and len(part) > 2:
            runs.append(_run(part[1:-1], vert="subscript"))
        else:
            runs.append(_run(part))
    return "".join(runs)


class Builder:
    def __init__(self):
        self.body = []
        self.comments = []

    def paragraph(self, text, style=None):
        notes = [c.strip() for c in COMMENT_RE.findall(text)]
        text = COMMENT_RE.sub("", text).strip()
        ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
        runs = inline_runs(text)
        if notes:
            start = end = ""
            refs = ""
            for note in notes:
                cid = len(self.comments)
                self.comments.append(note)
                start += f'<w:commentRangeStart w:id="{cid}"/>'
                end += f'<w:commentRangeEnd w:id="{cid}"/>'
                refs += (f'<w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr>'
                         f'<w:commentReference w:id="{cid}"/></w:r>')
            runs = start + runs + end + refs
        self.body.append(f"<w:p>{ppr}{runs}</w:p>")

    def table(self, rows):
        width = max(len(r) for r in rows)
        border = ('<w:tblBorders>' + "".join(
            f'<w:{side} w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
            for side in ("top", "left", "bottom", "right", "insideH", "insideV")) + '</w:tblBorders>')
        xml = [f'<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/>{border}</w:tblPr><w:tblGrid>'
               + "".join('<w:gridCol/>' for _ in range(width)) + "</w:tblGrid>"]
        for i, row in enumerate(rows):
            cells = row + [""] * (width - len(row))
            xml.append("<w:tr>")
            for cell in cells:
                cell = COMMENT_RE.sub("", cell).strip()
                content = _run(cell.replace("**", ""), bold=True) if i == 0 else inline_runs(cell)
                xml.append(f'<w:tc><w:p><w:pPr><w:pStyle w:val="TableText"/></w:pPr>{content}</w:p></w:tc>')
            xml.append("</w:tr>")
        xml.append("</w:tbl>")
        self.body.append("".join(xml))
        self.body.append("<w:p/>")


def parse_markdown(md, builder):
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    blocks = re.split(r"\n\s*\n", md.strip())
    for block in blocks:
        lines = [l.rstrip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        if all(l.lstrip().startswith("|") for l in lines):
            rows = []
            for l in lines:
                cells = [c.strip() for c in l.strip().strip("|").split("|")]
                if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    continue
                rows.append(cells)
            if rows:
                builder.table(rows)
            continue
        buffer = []

        def flush():
            if buffer:
                builder.paragraph(" ".join(buffer))
                buffer.clear()

        for line in lines:
            h = re.match(r"^(#{1,6})\s+(.*)", line)
            if h:
                flush()
                builder.paragraph(h.group(2).strip(), style=f"Heading{min(len(h.group(1)), 3)}")
            elif re.match(r"^\s*[-*]\s+", line):
                flush()
                builder.paragraph("• " + re.sub(r"^\s*[-*]\s+", "", line), style="ListBullet")
            else:
                buffer.append(line.strip())
        flush()


STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}" w:eastAsia="{font}"/>
<w:sz w:val="{size}"/><w:szCs w:val="{size}"/><w:lang w:val="en-GB"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="{line}" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="240" w:after="120"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="200" w:after="80"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:spacing w:before="160" w:after="60"/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:i/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListBullet"><w:name w:val="List Bullet"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="360" w:hanging="360"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="TableText"><w:name w:val="Table Text"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:rPr><w:sz w:val="20"/></w:rPr></w:style>
<w:style w:type="character" w:styleId="CommentReference"><w:name w:val="annotation reference"/><w:rPr><w:sz w:val="16"/></w:rPr></w:style>
</w:styles>"""

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
{comments_ct}<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>"""


def build(md, out_path, font="Times New Roman", size_pt=12, double_spacing=False, line_numbers=False,
          title=""):
    builder = Builder()
    parse_markdown(md, builder)
    ln = '<w:lnNumType w:countBy="1" w:restart="continuous"/>' if line_numbers else ""
    sect = (f'<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
            f'<w:pgMar w:top="1418" w:right="1418" w:bottom="1418" w:left="1418" w:header="709" w:footer="709" w:gutter="0"/>'
            f'{ln}</w:sectPr>')
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                f'<w:body>{"".join(builder.body)}{sect}</w:body></w:document>')
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{escape(title)}</dc:title><dc:creator></dc:creator>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created></cp:coreProperties>')
    doc_rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>']
    comments_ct = ""
    comments_xml = None
    if builder.comments:
        doc_rels.append('<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="comments.xml"/>')
        comments_ct = ('<Override PartName="/word/comments.xml" '
                       'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/>\n')
        items = "".join(
            f'<w:comment w:id="{i}" w:author="{COMMENT_AUTHOR}" w:initials="AI" w:date="{now}">'
            f'<w:p>{_run(text)}</w:p></w:comment>' for i, text in enumerate(builder.comments))
        comments_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                        f'<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">{items}</w:comments>')
    doc_rels.append("</Relationships>")
    styles = (STYLES.replace("{font}", escape(font)).replace("{size}", str(size_pt * 2))
              .replace("{line}", "480" if double_spacing else "360"))
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES.replace("{comments_ct}", comments_ct))
        zf.writestr("_rels/.rels", ROOT_RELS)
        zf.writestr("docProps/core.xml", core)
        zf.writestr("word/document.xml", document)
        zf.writestr("word/styles.xml", styles)
        zf.writestr("word/_rels/document.xml.rels", "".join(doc_rels))
        if comments_xml:
            zf.writestr("word/comments.xml", comments_xml)
    return {"paragraphs_and_tables": len(builder.body), "comments": len(builder.comments)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("markdown")
    ap.add_argument("--out", required=True)
    ap.add_argument("--font", default="Times New Roman")
    ap.add_argument("--size", type=int, default=12)
    ap.add_argument("--double-spacing", action="store_true")
    ap.add_argument("--line-numbers", action="store_true")
    ap.add_argument("--title", default="")
    args = ap.parse_args(argv)
    with open(args.markdown, encoding="utf-8-sig") as fh:
        md = fh.read()
    info = build(md, args.out, args.font, args.size, args.double_spacing, args.line_numbers, args.title)
    print(f"written {args.out}: {info['paragraphs_and_tables']} blocks, {info['comments']} comment(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
