#!/usr/bin/env python3
"""Content-preservation check between an original manuscript inventory and a
revised Markdown manuscript (standard library only).

The revised Markdown marks where each paragraph came from:

  <!-- src: P0012, P0013 -->   paragraph rewritten from these original blocks
  <!-- src: NEW -->            new text (must be sourced or a [MISSING: ...] placeholder)

and lists deliberately removed original blocks once, anywhere in the file:

  <!-- discarded: P0020 = duplicate of P0012; P0031 = out of scope -->

Checks:
  1. coverage     every original content block is used (src) or discarded with a reason
  2. new numbers  numbers in the revision that occur neither in the original nor in
                  the supplied data files (possible fabrication or unsourced change)
  3. lost results numbers from original Abstract/Results that no longer appear
  4. references   DOIs / reference entries removed or added
  5. new text     paragraphs marked NEW, for author review

Usage:
  python3 compare_versions.py original.inventory.json revised.md
                              [--data results.csv ...] [--json]
Exit code 1 if blocks are uncovered or unexplained new numbers exist.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manuscript_checks import NUMBER_RE, norm_number, split_sections  # noqa: E402

SRC_RE = re.compile(r"<!--\s*src:\s*(.*?)\s*-->", re.I | re.S)
DISCARD_RE = re.compile(r"<!--\s*discarded:\s*(.*?)\s*-->", re.I | re.S)
BLOCK_ID_RE = re.compile(r"\b([PTFC]\d{4})\b")
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s;,)\]]+", re.I)
CITATION_BRACKET_RE = re.compile(r"\[(\d+(?:\s*[-–,;]\s*\d+)*)\]")
LABEL_NUMBER_RE = re.compile(
    r"\b(fig(?:ure)?s?\.?|tables?|abb(?:ildung)?\.?|tab(?:elle)?\.?|section|abschnitt|supplementary)\s*S?\d+[a-z]?",
    re.I)
REF_SECTIONS = {"references", "bibliography"}


def numbers_in(text):
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"\[MISSING[^\]]*\]", " ", text)
    text = CITATION_BRACKET_RE.sub(" ", text)
    text = LABEL_NUMBER_RE.sub(" ", text)
    text = DOI_RE.sub(" ", text)
    text = re.sub(r"^\s*#+\s*\d+(\.\d+)*\.?", " ", text, flags=re.M)   # numbered headings
    # plain-text numbered headings ("2.1 Data collection"); a decimal followed by
    # anything other than a capitalized word (e.g. "3.63 (3.00-4.25)") is data
    text = re.sub(r"^\s*\d+(\.\d+)+\.?[ \t]+(?=[A-Z][a-z])", " ", text, flags=re.M)
    return {norm_number(t) for t in NUMBER_RE.findall(text)}


def load_inventory(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return data["blocks"]


def content_blocks(blocks):
    """Blocks that carry content and therefore need a destination."""
    return [b for b in blocks
            if b["type"] not in ("heading", "title") and b.get("text", "").strip()
            and b.get("section") not in REF_SECTIONS]


def reference_entries(blocks):
    return [b["text"] for b in blocks if b.get("section") in REF_SECTIONS and b["type"] != "heading"]


def parse_revision(md):
    used, new_paragraphs = set(), []
    for m in SRC_RE.finditer(md):
        ids = set(BLOCK_ID_RE.findall(m.group(1)))
        used |= ids
        if "NEW" in m.group(1).upper():
            tail = md[m.end():].lstrip()
            new_paragraphs.append(re.split(r"\n\s*\n", tail, maxsplit=1)[0][:160])
    discarded = {}
    for m in DISCARD_RE.finditer(md):
        for item in re.split(r"\s*;\s*", m.group(1)):
            ids = BLOCK_ID_RE.findall(item)
            reason = item.split("=", 1)[1].strip() if "=" in item else ""
            for bid in ids:
                discarded[bid] = reason
    return used, discarded, new_paragraphs


def traceability_rows(md):
    """(revised_section, excerpt, source_ids) for every src marker."""
    rows, section = [], ""
    for m in re.finditer(r"^#{1,6}[ \t]+([^\n]*)$|<!--\s*src:\s*(.*?)\s*-->", md, flags=re.M | re.S | re.I):
        if m.group(1) is not None:
            section = m.group(1).strip()
            continue
        tail = md[m.end():].lstrip()
        excerpt = re.sub(r"\s+", " ", re.split(r"\n\s*\n", tail, maxsplit=1)[0])[:100]
        rows.append((section, excerpt, m.group(2).strip()))
    return rows


def revised_body_and_refs(md):
    sections = split_sections(md)
    body = "\n".join(t for n, t in sections if n not in REF_SECTIONS)
    refs = "\n".join(t for n, t in sections if n in REF_SECTIONS)
    return body, refs


def _norm_ref(text):
    text = re.sub(r"^\s*(\[\d+\]|\d+[.)])\s*", "", text)
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()[:60]


def compare(blocks, md, data_texts=()):
    used, discarded, new_paragraphs = parse_revision(md)
    needs_home = content_blocks(blocks)
    uncovered = [b["id"] for b in needs_home if b["id"] not in used and b["id"] not in discarded]
    discarded_without_reason = sorted(k for k, v in discarded.items() if not v)
    unknown_ids = sorted((used | set(discarded)) - {b["id"] for b in blocks})

    original_text = "\n".join(b.get("text", "") for b in blocks if b.get("section") not in REF_SECTIONS)
    allowed = numbers_in(original_text)
    for t in data_texts:
        allowed |= {norm_number(x) for x in NUMBER_RE.findall(t)}
    body, revised_refs = revised_body_and_refs(md)
    revised_numbers = numbers_in(body)
    new_numbers = sorted(revised_numbers - allowed, key=lambda x: (len(x), x))

    result_text = "\n".join(b.get("text", "") for b in blocks if b.get("section") in ("abstract", "results"))
    lost_results = sorted(numbers_in(result_text) - revised_numbers, key=lambda x: (len(x), x))

    orig_refs = reference_entries(blocks)
    orig_dois = {d.rstrip(".").lower() for r in orig_refs for d in DOI_RE.findall(r)}
    rev_dois = {d.rstrip(".").lower() for d in DOI_RE.findall(revised_refs)}
    rev_keys = {_norm_ref(l) for l in revised_refs.splitlines() if _norm_ref(l)}
    removed_no_doi = [r[:80] for r in orig_refs if not DOI_RE.search(r) and _norm_ref(r) not in rev_keys]

    return {
        "original_content_blocks": len(needs_home),
        "used_blocks": len(used & {b["id"] for b in needs_home}),
        "discarded_blocks": len(discarded),
        "uncovered_blocks": uncovered,
        "discarded_without_reason": discarded_without_reason,
        "unknown_block_ids": unknown_ids,
        "new_numbers_without_source": new_numbers,
        "original_result_numbers_missing": lost_results,
        "references": {
            "original_entries": len(orig_refs),
            "revised_entries": len(rev_keys),
            "dois_removed": sorted(orig_dois - rev_dois),
            "dois_added_need_verification": sorted(rev_dois - orig_dois),
            "entries_without_doi_possibly_removed": removed_no_doi[:50],
        },
        "new_paragraphs_for_author_review": new_paragraphs,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inventory", help="<name>.inventory.json from extract_manuscript.py")
    ap.add_argument("revised", help="revised Markdown with src/discarded markers")
    ap.add_argument("--data", nargs="*", default=[], help="data files whose numbers are allowed (csv/txt/md)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--traceability", help="write revised-paragraph -> source-block CSV to this path")
    args = ap.parse_args(argv)
    blocks = load_inventory(args.inventory)
    with open(args.revised, encoding="utf-8-sig") as fh:
        md = fh.read()
    if args.traceability:
        import csv
        with open(args.traceability, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["revised_section", "revised_paragraph_start", "source_blocks"])
            writer.writerows(traceability_rows(md))
    data_texts = []
    for path in args.data:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            data_texts.append(fh.read())
    report = compare(blocks, md, data_texts)
    fail = bool(report["uncovered_blocks"] or report["new_numbers_without_source"]
                or report["discarded_without_reason"] or report["unknown_block_ids"])
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for key, value in report.items():
            print(f"{key}: {value}")
        print("RESULT: " + ("ISSUES FOUND" if fail else "PASS"))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
