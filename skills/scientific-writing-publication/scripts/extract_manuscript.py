#!/usr/bin/env python3
"""Extract an existing manuscript (DOCX, PDF, DOC/ODT/RTF, MD/TXT) into a
paragraph-numbered content inventory for revision.

Outputs (in --out-dir, default: alongside the input):
  <name>.inventory.md    readable text, every block prefixed with its ID [P0001]
  <name>.inventory.json  blocks with id, type, section, style, text, comments,
                         tracked changes, plus figures, tables, warnings, stats

The inventory is the basis for revision: every block ID must later be either
used in the revised manuscript (<!-- src: P0001 -->) or listed as discarded
with a reason (see compare_versions.py).

DOCX is parsed with the standard library (headings, lists, tables, captions,
comments, tracked insertions/deletions, footnotes/endnotes, equations,
reference-manager fields, document metadata).
PDF needs one of: pdftotext (poppler), pypdf, or pdfplumber.
DOC/ODT/RTF are converted to DOCX with LibreOffice (soffice) if installed.

Usage:
  python3 extract_manuscript.py paper.docx [--out-dir DIR]
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manuscript_checks import SECTION_NAMES, canonical  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
DC = "{http://purl.org/dc/elements/1.1/}"
CP = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"
REF_FIELD_MARKERS = {
    "ZOTERO_ITEM": "Zotero", "ZOTERO_BIBL": "Zotero", "EN.CITE": "EndNote",
    "EN.REFLIST": "EndNote", "CSL_CITATION": "Mendeley/CSL", "MENDELEY": "Mendeley",
    "CITAVI": "Citavi", "PAPERPILE": "Paperpile",
}
CAPTION_RE = re.compile(r"^\s*(fig(ure)?\.?|abb(ildung)?\.?|table|tab(elle)?\.?)\s*\d+", re.I)


# ---------------- DOCX ----------------

def _read_xml(zf, name):
    try:
        return ET.fromstring(zf.read(name))
    except KeyError:
        return None


def _style_map(zf):
    """styleId -> (name, outline level or None)."""
    root = _read_xml(zf, "word/styles.xml")
    styles = {}
    if root is None:
        return styles
    for st in root.iter(W + "style"):
        sid = st.get(W + "styleId")
        name_el = st.find(W + "name")
        name = name_el.get(W + "val") if name_el is not None else sid
        lvl_el = st.find(f"{W}pPr/{W}outlineLvl")
        lvl = int(lvl_el.get(W + "val")) + 1 if lvl_el is not None else None
        styles[sid] = (name or "", lvl)
    return styles


def _run_text(el, record):
    """Text of a paragraph/cell, tracking insertions, deletions and fields."""
    parts = []
    for node in el.iter():
        tag = node.tag
        if tag == W + "t":
            parts.append(node.text or "")
        elif tag == W + "tab":
            parts.append("\t")
        elif tag in (W + "br", W + "cr"):
            parts.append("\n")
        elif tag == W + "delText":
            record["deleted"].append(node.text or "")
        elif tag == W + "instrText":
            instr = node.text or ""
            for marker, tool in REF_FIELD_MARKERS.items():
                if marker in instr.upper():
                    record["ref_fields"].add(tool)
        elif tag == M + "oMath":
            record["equations"] += 1
        elif tag == W + "footnoteReference":
            parts.append(f"[^fn{node.get(W + 'id')}]")
        elif tag == W + "endnoteReference":
            parts.append(f"[^en{node.get(W + 'id')}]")
        elif tag == W + "drawing" or tag == W + "pict":
            record["images"] += 1
    for ins in el.iter(W + "ins"):
        txt = "".join(t.text or "" for t in ins.iter(W + "t"))
        if txt:
            record["inserted"].append(txt)
    text = "".join(parts)
    return re.sub(r"[  ]+", " ", text).strip()


def _notes(zf, name, prefix):
    root = _read_xml(zf, name)
    notes = {}
    if root is None:
        return notes
    tag = W + ("footnote" if prefix == "fn" else "endnote")
    for note in root.iter(tag):
        nid = note.get(W + "id")
        if nid in ("-1", "0") or note.get(W + "type") in ("separator", "continuationSeparator"):
            continue
        text = " ".join("".join(t.text or "" for t in p.iter(W + "t")) for p in note.iter(W + "p")).strip()
        if text:
            notes[f"{prefix}{nid}"] = text
    return notes


def _comments(zf):
    root = _read_xml(zf, "word/comments.xml")
    out = {}
    if root is None:
        return out
    for c in root.iter(W + "comment"):
        text = " ".join("".join(t.text or "" for t in p.iter(W + "t")) for p in c.iter(W + "p")).strip()
        out[c.get(W + "id")] = {"author_initials": (c.get(W + "initials") or "")[:4], "text": text}
    return out


def _metadata(zf):
    root = _read_xml(zf, "docProps/core.xml")
    meta = {}
    if root is None:
        return meta
    for key, tag in (("title", DC + "title"), ("creator", DC + "creator"),
                     ("last_modified_by", CP + "lastModifiedBy")):
        el = root.find(tag)
        if el is not None and el.text:
            meta[key] = el.text
    return meta


def _looks_like_section_heading(text):
    plain = re.sub(r"^\d+(\.\d+)*\.?\s+", "", text or "").strip().rstrip(":").strip()
    return 0 < len(plain) < 60 and canonical(plain.lower()) in SECTION_NAMES


def _body_children(body):
    """Body-level paragraphs and tables, unwrapping content controls (w:sdt)."""
    for child in body:
        if child.tag == W + "sdt":
            content = child.find(W + "sdtContent")
            if content is not None:
                yield from _body_children(content)
        else:
            yield child


def extract_docx(path):
    with zipfile.ZipFile(path) as zf:
        doc = _read_xml(zf, "word/document.xml")
        if doc is None:
            raise ValueError("not a valid DOCX (word/document.xml missing)")
        styles = _style_map(zf)
        comments = _comments(zf)
        notes = {**_notes(zf, "word/footnotes.xml", "fn"), **_notes(zf, "word/endnotes.xml", "en")}
        meta = _metadata(zf)
        media = [n for n in zf.namelist() if n.startswith("word/media/")]

    body = doc.find(W + "body")
    blocks = []
    totals = {"deleted": 0, "inserted": 0, "equations": 0, "images": 0}
    ref_fields = set()
    for child in _body_children(body):
        record = {"deleted": [], "inserted": [], "ref_fields": set(), "equations": 0, "images": 0}
        if child.tag == W + "p":
            text = _run_text(child, record)
            style_el = child.find(f"{W}pPr/{W}pStyle")
            sid = style_el.get(W + "val") if style_el is not None else ""
            sname, slvl = styles.get(sid, (sid, None))
            lvl_el = child.find(f"{W}pPr/{W}outlineLvl")
            level = int(lvl_el.get(W + "val")) + 1 if lvl_el is not None else slvl
            m = re.match(r"^(heading|überschrift)\s*(\d)", sname or "", re.I)
            if m:
                level = int(m.group(2))
            kind = "paragraph"
            if (sname or "").lower() == "title":
                kind, level = "title", 0
            elif level and level <= 6 and text:
                kind = "heading"
            elif (sname or "").lower() in ("caption", "beschriftung") or CAPTION_RE.match(text):
                kind = "caption"
            elif child.find(f"{W}pPr/{W}numPr") is not None or (sname or "").lower().startswith("list"):
                kind = "list_item"
            if kind == "paragraph" and _looks_like_section_heading(text):
                kind, level = "heading", 1  # section name typed as normal (often bold) text
            anchors = [c.get(W + "id") for c in child.iter(W + "commentRangeStart")]
            anchors += [c.get(W + "id") for c in child.iter(W + "commentReference")]
            block = {"type": kind, "style": sname, "text": text}
            if kind == "heading":
                block["level"] = level
            cm = [comments[a] for a in dict.fromkeys(anchors) if a in comments]
            if cm:
                block["comments"] = cm
            if record["deleted"] or record["inserted"]:
                block["tracked"] = {"inserted": record["inserted"], "deleted": record["deleted"]}
            if record["equations"]:
                block["equations"] = record["equations"]
                block["text"] = (text + " [EQUATION]").strip()
            if text or record["images"] or record["equations"]:
                if not text and record["images"]:
                    block["type"], block["text"] = "figure", "[IMAGE]"
                blocks.append(block)
        elif child.tag == W + "tbl":
            rows = []
            for tr in child.iter(W + "tr"):
                rows.append([_run_text(tc, record) for tc in tr.iter(W + "tc")])
            blocks.append({"type": "table", "rows": rows,
                           "text": "\n".join(" | ".join(r) for r in rows)})
        for key in ("equations", "images"):
            totals[key] += record[key]
        totals["deleted"] += len(record["deleted"])
        totals["inserted"] += len(record["inserted"])
        ref_fields |= record["ref_fields"]

    warnings = []
    if totals["deleted"] or totals["inserted"]:
        warnings.append(f"document contains unaccepted tracked changes "
                        f"({totals['inserted']} insertions, {totals['deleted']} deletions); "
                        "inventory uses the text with insertions kept and deletions removed; "
                        "ask the authors whether changes are accepted")
    if comments:
        warnings.append(f"{len(comments)} reviewer/author comment(s) found; treat as open tasks")
    if ref_fields:
        warnings.append("citations are live reference-manager fields (" + ", ".join(sorted(ref_fields))
                        + "); a rebuilt document loses the field links; re-insert citations with the "
                        "reference manager after revision or keep the manuscript's citation keys")
    if totals["equations"]:
        warnings.append(f"{totals['equations']} equation(s) extracted only as [EQUATION] placeholders; check manually")
    if meta.get("creator") or meta.get("last_modified_by"):
        warnings.append("document metadata contains author names; remove for double-blind review")
    return blocks, {"media_files": len(media), "footnotes_endnotes": notes, "metadata_fields": sorted(meta),
                    "warnings": warnings, "extraction": "docx-native", "confidence": "high"}


# ---------------- PDF ----------------

def _safe_import(name):
    """Import an optional backend; broken native dependencies must not crash extraction."""
    try:
        return __import__(name)
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException:  # ImportError, or e.g. a panicking native extension
        return None


def _pdf_pages(path):
    if shutil.which("pdftotext"):
        out = subprocess.run(["pdftotext", "-enc", "UTF-8", path, "-"], capture_output=True, timeout=120)
        if out.returncode == 0:
            return out.stdout.decode("utf-8", "replace").split("\f"), "pdftotext"
    pypdf = _safe_import("pypdf")
    if pypdf is not None:
        reader = pypdf.PdfReader(path)
        return [p.extract_text() or "" for p in reader.pages], "pypdf"
    pdfplumber = _safe_import("pdfplumber")
    if pdfplumber is not None:
        with pdfplumber.open(path) as pdf:
            return [p.extract_text() or "" for p in pdf.pages], "pdfplumber"
    raise RuntimeError("no PDF text backend available: install poppler-utils (pdftotext) or "
                       "`pip install pypdf`, or use the host's PDF skill, or ask the user for the DOCX")


def clean_pdf_pages(pages):
    """Remove running headers/footers, page numbers, line numbers; fix hyphenation."""
    line_counts = Counter()
    split_pages = [p.splitlines() for p in pages]
    for lines in split_pages:
        for line in {l.strip() for l in lines if l.strip()}:
            line_counts[line] += 1
    n_pages = max(len(pages), 1)
    repeated = {l for l, c in line_counts.items() if n_pages >= 3 and c >= 0.5 * n_pages and len(l) < 120}
    all_lines = [l for lines in split_pages for l in lines
                 if l.strip() and l.strip() not in repeated and not re.fullmatch(r"\s*\d{1,4}\s*", l)]
    numbered = sum(1 for l in all_lines if re.match(r"^\s*\d{1,4}\s+\S", l))
    strip_line_numbers = bool(all_lines) and numbered / len(all_lines) > 0.6
    text_lines = []
    for lines in split_pages:
        for line in lines:
            s = line.strip()
            if s in repeated or re.fullmatch(r"(page\s*)?\d{1,4}(\s*(of|/)\s*\d{1,4})?", s, re.I):
                continue
            if strip_line_numbers:
                s = re.sub(r"^\d{1,4}\s+", "", s)
            text_lines.append(s)
        text_lines.append("")
    text = "\n".join(text_lines)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)          # hyphenated line breaks
    return text, {"removed_repeated_lines": len(repeated), "stripped_line_numbers": strip_line_numbers}


def _pdf_heading(line):
    s = line.strip()
    if not s or len(s) > 90 or s.endswith((".", ",", ";")):
        return None
    plain = re.sub(r"^\d+(\.\d+)*\.?\s+", "", s).rstrip(":").strip()
    if canonical(plain.lower()) in SECTION_NAMES:
        return 1
    if re.match(r"^\d+(\.\d+)+\.?\s+[A-ZÄÖÜ]", s) and len(s.split()) <= 12:
        return 2
    return None


def extract_pdf(path):
    pages, backend = _pdf_pages(path)
    chars = [len(p.strip()) for p in pages]
    text, info = clean_pdf_pages(pages)
    blocks = []
    all_lengths = sorted(len(l.strip()) for l in text.splitlines() if l.strip())
    typical = all_lengths[len(all_lengths) // 2] if all_lengths else 80
    for para in re.split(r"\n\s*\n", text):
        buffer = []

        def flush():
            if buffer:
                joined = re.sub(r"\s+", " ", " ".join(buffer)).strip()
                kind = "caption" if CAPTION_RE.match(joined) else "paragraph"
                blocks.append({"type": kind, "text": joined})
                buffer.clear()

        for line in (l.strip() for l in para.splitlines()):
            if not line:
                continue
            level = _pdf_heading(line)
            if not level and _looks_like_section_heading(line):
                level = 1
            if level:
                flush()
                blocks.append({"type": "heading", "level": level, "text": line})
                continue
            buffer.append(line)
            # short line ending a sentence: probable paragraph end (backends without blank lines)
            if line.endswith((".", "!", "?", ":")) and len(line) < 0.7 * typical:
                flush()
        flush()

    warnings = ["PDF extraction loses tables, superscript citations, and some paragraph boundaries; "
                "ask the authors for the DOCX source if available",
                "check tables and figures against the original PDF; tables are not reconstructed"]
    low = sum(1 for c in chars if c < 50)
    confidence = "medium"
    if pages and low / len(pages) > 0.5:
        warnings.append("most pages contain little text: probably a scanned PDF; OCR is required "
                        "(e.g. tesseract/ocrmypdf) before revision")
        confidence = "low"
    if info["stripped_line_numbers"]:
        warnings.append("line numbers were detected and removed")
    return blocks, {"pages": len(pages), "warnings": warnings, "extraction": f"pdf-{backend}",
                    "confidence": confidence, **info}


# ---------------- other formats ----------------

def convert_with_soffice(path, tmpdir):
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise RuntimeError("LibreOffice (soffice) not available to convert this format; ask for DOCX or PDF")
    subprocess.run([soffice, "--headless", "--convert-to", "docx", "--outdir", tmpdir, path],
                   capture_output=True, timeout=180, check=True)
    out = os.path.join(tmpdir, os.path.splitext(os.path.basename(path))[0] + ".docx")
    if not os.path.exists(out):
        raise RuntimeError("LibreOffice conversion failed")
    return out


def extract_text_file(path):
    with open(path, encoding="utf-8-sig") as fh:
        text = fh.read()
    blocks = []
    for para in re.split(r"\n\s*\n", text):
        s = para.strip()
        if not s:
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", s)
        if m and "\n" not in s:
            blocks.append({"type": "heading", "level": len(m.group(1)), "text": m.group(2).strip()})
        elif "\n" not in s and _looks_like_section_heading(s):
            blocks.append({"type": "heading", "level": 1, "text": s})
        else:
            blocks.append({"type": "caption" if CAPTION_RE.match(s) else "paragraph", "text": s})
    return blocks, {"warnings": [], "extraction": "text", "confidence": "high"}


# ---------------- inventory ----------------

def assign_ids_and_sections(blocks):
    section = "_front_matter"
    counters = Counter()
    for block in blocks:
        if block["type"] == "heading":
            name = re.sub(r"^\d+(\.\d+)*\.?\s+", "", block["text"]).strip().rstrip(":").lower()
            canon = canonical(name)
            if canon in SECTION_NAMES:
                section = canon
            elif block.get("level", 1) <= 1 and section == "_front_matter":
                section = "_front_matter"
        prefix = {"table": "T", "figure": "F", "caption": "C"}.get(block["type"], "P")
        counters[prefix] += 1
        block["id"] = f"{prefix}{counters[prefix]:04d}"
        block["section"] = section
        block["words"] = len(re.findall(r"\w+", block.get("text", "")))
    return blocks


def structure_summary(blocks):
    order, words = [], Counter()
    for b in blocks:
        if b["section"] not in order:
            order.append(b["section"])
        words[b["section"]] += b["words"]
    return [{"section": s, "words": words[s]} for s in order]


def render_markdown(blocks, meta):
    out = [f"<!-- inventory: extraction={meta.get('extraction')} confidence={meta.get('confidence')} -->", ""]
    for w in meta.get("warnings", []):
        out.append(f"> WARNING: {w}")
    if meta.get("warnings"):
        out.append("")
    for b in blocks:
        if b["type"] == "heading":
            out.append(f"{'#' * max(1, min(b.get('level') or 1, 6))} [{b['id']}] {b['text']}")
        elif b["type"] == "title":
            out.append(f"# [{b['id']}] {b['text']}")
        elif b["type"] == "table":
            rows = b["rows"]
            out.append(f"[{b['id']}] TABLE")
            if rows:
                width = max(len(r) for r in rows)
                norm = [r + [""] * (width - len(r)) for r in rows]
                out.append("| " + " | ".join(c.replace("|", "/") for c in norm[0]) + " |")
                out.append("|" + "---|" * width)
                for r in norm[1:]:
                    out.append("| " + " | ".join(c.replace("|", "/").replace("\n", " ") for c in r) + " |")
        else:
            prefix = "- " if b["type"] == "list_item" else ""
            out.append(f"{prefix}[{b['id']}] {b['text']}")
        for c in b.get("comments", []):
            out.append(f"  > COMMENT ({c['author_initials'] or '?'}): {c['text']}")
        if b.get("tracked"):
            out.append(f"  > TRACKED: +{len(b['tracked']['inserted'])} / -{len(b['tracked']['deleted'])}")
        out.append("")
    notes = meta.get("footnotes_endnotes") or {}
    if notes:
        out.append("## Footnotes / endnotes")
        out.extend(f"[^{k}]: {v}" for k, v in notes.items())
    return "\n".join(out) + "\n"


def render_clean_markdown(blocks):
    """Plain Markdown without block IDs, for manuscript_checks.py / check_citations.py."""
    out = []
    for b in blocks:
        if b["type"] in ("heading", "title"):
            out.append("#" * max(1, min(b.get("level") or 1, 6)) + " " + b["text"])
        elif b["type"] == "table":
            rows = [[c.replace("\n", "; ").replace("|", "/") for c in r] for r in b["rows"]]
            if rows:
                width = max(len(r) for r in rows)
                rows = [r + [""] * (width - len(r)) for r in rows]
                out.append("\n".join(["| " + " | ".join(rows[0]) + " |", "|" + "---|" * width]
                                     + ["| " + " | ".join(r) + " |" for r in rows[1:]]))
        elif b["type"] != "figure":
            out.append(("- " if b["type"] == "list_item" else "") + b["text"])
    return "\n\n".join(out) + "\n"


def extract(path):
    ext = os.path.splitext(path)[1].lower()
    with tempfile.TemporaryDirectory() as tmp:
        if ext == ".docx":
            blocks, meta = extract_docx(path)
        elif ext == ".pdf":
            blocks, meta = extract_pdf(path)
        elif ext in (".doc", ".odt", ".rtf"):
            blocks, meta = extract_docx(convert_with_soffice(path, tmp))
            meta["extraction"] = f"soffice->{meta['extraction']}"
        elif ext in (".md", ".txt", ".markdown"):
            blocks, meta = extract_text_file(path)
        else:
            raise RuntimeError(f"unsupported format {ext}; supported: docx, pdf, doc, odt, rtf, md, txt")
    blocks = assign_ids_and_sections(blocks)
    known = {b["section"] for b in blocks}
    missing = [s for s in ("abstract", "introduction", "methods", "results", "discussion", "references")
               if s not in known and not (s == "methods" and known & {"materials and methods", "patients and methods", "methodology"})]
    meta["structure"] = structure_summary(blocks)
    meta["standard_sections_not_detected"] = missing
    meta["counts"] = dict(Counter(b["type"] for b in blocks))
    return blocks, meta


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manuscript")
    ap.add_argument("--out-dir")
    args = ap.parse_args(argv)
    try:
        blocks, meta = extract(args.manuscript)
    except (RuntimeError, ValueError, zipfile.BadZipFile, subprocess.SubprocessError) as err:
        print(f"[extract_manuscript] {err}", file=sys.stderr)
        return 3
    out_dir = args.out_dir or os.path.dirname(os.path.abspath(args.manuscript))
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.join(out_dir, os.path.splitext(os.path.basename(args.manuscript))[0])
    with open(stem + ".inventory.json", "w", encoding="utf-8") as fh:
        json.dump({"source": os.path.basename(args.manuscript), "meta": meta, "blocks": blocks},
                  fh, indent=2, ensure_ascii=False)
    with open(stem + ".inventory.md", "w", encoding="utf-8") as fh:
        fh.write(render_markdown(blocks, meta))
    with open(stem + ".clean.md", "w", encoding="utf-8") as fh:
        fh.write(render_clean_markdown(blocks))
    print(f"blocks: {meta['counts']}")
    print("structure: " + " > ".join(f"{s['section']}({s['words']})" for s in meta["structure"]))
    if meta["standard_sections_not_detected"]:
        print("standard sections not detected: " + ", ".join(meta["standard_sections_not_detected"]))
    for w in meta["warnings"]:
        print(f"WARNING: {w}")
    print(f"written: {stem}.inventory.md, {stem}.inventory.json, {stem}.clean.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
