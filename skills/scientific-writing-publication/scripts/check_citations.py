#!/usr/bin/env python3
"""Check in-text citations against the reference list (standard library only).

Numeric styles (Vancouver, AMA, IEEE): citations like [1], [1,3], [2-5], [2–5].
Author-year styles (APA, Harvard): citations like (Smith et al., 2020; Doe, 2019).

Reports: citations without a reference entry, entries never cited, numbering
out of first-appearance order (numeric), and duplicate entries (same DOI or
near-identical text).

Usage:
  python3 check_citations.py manuscript.md [--refs references.txt]
                             [--style numeric|author-year] [--json]

Without --refs, the reference list is taken from the section headed
References / Bibliography / Literatur / Literaturverzeichnis in the manuscript.
"""

import argparse
import difflib
import json
import re
import sys

REF_HEADING = re.compile(
    r"^\s*(#+\s*)?(\d+\.?\s*)?(references|bibliography|literature cited|literatur|literaturverzeichnis)\s*:?\s*$",
    re.I)
NUMERIC_CITE = re.compile(r"\[(\d+(?:\s*[-–,;]\s*\d+)*)\]")
ENTRY_START = re.compile(r"^\s*(?:\[(\d+)\]|(\d+)[.)])\s+(.*)")
AUTHOR_YEAR_CITE = re.compile(r"\(([^()]*?\b(?:19|20)\d{2}[a-z]?)\)")
DOI_IN_TEXT = re.compile(r"10\.\d{4,9}/[^\s;,]+", re.I)


def split_manuscript(text):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if REF_HEADING.match(line):
            return "\n".join(lines[:i]), "\n".join(lines[i + 1:])
    return text, ""


def expand_numeric(group):
    nums = []
    for part in re.split(r"\s*[,;]\s*", group):
        rng = re.split(r"\s*[-–]\s*", part)
        if len(rng) == 2 and rng[0].isdigit() and rng[1].isdigit():
            lo, hi = int(rng[0]), int(rng[1])
            if lo <= hi and hi - lo < 200:
                nums.extend(range(lo, hi + 1))
                continue
        if part.strip().isdigit():
            nums.append(int(part))
    return nums


def numeric_citations(body):
    order = []
    for match in NUMERIC_CITE.finditer(body):
        order.extend(expand_numeric(match.group(1)))
    return order


def parse_numbered_entries(refs_text):
    entries = {}
    current = None
    for line in refs_text.splitlines():
        m = ENTRY_START.match(line)
        if m:
            current = int(m.group(1) or m.group(2))
            entries[current] = m.group(3).strip()
        elif current is not None and line.strip():
            entries[current] += " " + line.strip()
    return entries


def parse_unnumbered_entries(refs_text):
    entries, buf = [], []
    for line in refs_text.splitlines():
        if line.strip():
            buf.append(line.strip())
        elif buf:
            entries.append(" ".join(buf))
            buf = []
    if buf:
        entries.append(" ".join(buf))
    # single-spaced lists: one entry per line
    if len(entries) == 1 and len(refs_text.strip().splitlines()) > 1:
        entries = [l.strip() for l in refs_text.splitlines() if l.strip()]
    return entries


def find_duplicates(entries):
    """entries: list of (key, text). Returns list of (key_a, key_b, reason)."""
    dups = []
    dois = {}
    for key, text in entries:
        for doi in DOI_IN_TEXT.findall(text):
            doi = doi.rstrip(".").lower()
            if doi in dois:
                dups.append((dois[doi], key, f"same DOI {doi}"))
            else:
                dois[doi] = key
    norm = [(k, re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()) for k, t in entries]
    for i in range(len(norm)):
        for j in range(i + 1, len(norm)):
            if norm[i][1] and difflib.SequenceMatcher(None, norm[i][1], norm[j][1]).ratio() > 0.92:
                pair = (norm[i][0], norm[j][0])
                if not any((a, b) == pair for a, b, _ in dups):
                    dups.append((pair[0], pair[1], "near-identical entry text"))
    return dups


def check_numeric(body, refs_text):
    cited = numeric_citations(body)
    entries = parse_numbered_entries(refs_text)
    first_seen = []
    for n in cited:
        if n not in first_seen:
            first_seen.append(n)
    out_of_order = [n for i, n in enumerate(first_seen) if n != i + 1]
    return {
        "style": "numeric",
        "citations_found": len(cited),
        "entries_found": len(entries),
        "missing_entries": sorted(set(cited) - set(entries)),
        "uncited_entries": sorted(set(entries) - set(cited)),
        "first_appearance_order_ok": not out_of_order,
        "first_out_of_order": out_of_order[:1],
        "duplicates": find_duplicates(sorted(entries.items())),
    }


def author_year_keys(body):
    keys = []
    for match in AUTHOR_YEAR_CITE.finditer(body):
        for part in match.group(1).split(";"):
            m = re.search(r"([A-Z][A-Za-zÀ-ſ'\-]+)[^;]*?\b((?:19|20)\d{2}[a-z]?)", part)
            if m:
                keys.append((m.group(1).lower(), m.group(2)))
    # narrative citations: Smith et al. (2020), Smith and Doe (2019)
    for m in re.finditer(r"\b([A-Z][A-Za-zÀ-ſ'\-]+)(?: et al\.| and [A-Z][\w\-]+| & [A-Z][\w\-]+)? \(((?:19|20)\d{2}[a-z]?)\)", body):
        keys.append((m.group(1).lower(), m.group(2)))
    return keys


def entry_key(text):
    author = re.match(r"\s*([A-Z][A-Za-zÀ-ſ'\-]+)", text)
    year = re.search(r"\b((?:19|20)\d{2}[a-z]?)\b", text)
    if author and year:
        return (author.group(1).lower(), year.group(1))
    return None


def check_author_year(body, refs_text):
    cited = author_year_keys(body)
    entries = parse_unnumbered_entries(refs_text)
    keyed = [(entry_key(e), e) for e in entries]
    entry_keys = {k for k, _ in keyed if k}
    return {
        "style": "author-year",
        "citations_found": len(cited),
        "entries_found": len(entries),
        "missing_entries": sorted({f"{a.title()} {y}" for a, y in cited if (a, y) not in entry_keys}),
        "uncited_entries": sorted({f"{k[0].title()} {k[1]}" for k, _ in keyed if k and k not in set(cited)}),
        "unparsed_entries": [e[:80] for k, e in keyed if not k],
        "duplicates": find_duplicates([(f"entry {i + 1}", e) for i, e in enumerate(entries)]),
    }


def detect_style(body):
    return "numeric" if len(NUMERIC_CITE.findall(body)) >= len(AUTHOR_YEAR_CITE.findall(body)) else "author-year"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manuscript")
    ap.add_argument("--refs")
    ap.add_argument("--style", choices=["numeric", "author-year"])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    with open(args.manuscript, encoding="utf-8-sig") as fh:
        body, refs_text = split_manuscript(fh.read())
    if args.refs:
        with open(args.refs, encoding="utf-8-sig") as fh:
            refs_text = fh.read()
    if not refs_text.strip():
        print("No reference list found. Pass --refs or add a 'References' heading.", file=sys.stderr)
        return 2

    style = args.style or detect_style(body)
    report = check_numeric(body, refs_text) if style == "numeric" else check_author_year(body, refs_text)
    problems = bool(report["missing_entries"] or report["uncited_entries"] or report["duplicates"]
                    or not report.get("first_appearance_order_ok", True))
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for key, value in report.items():
            print(f"{key}: {value}")
        print("RESULT: " + ("ISSUES FOUND" if problems else "PASS"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
