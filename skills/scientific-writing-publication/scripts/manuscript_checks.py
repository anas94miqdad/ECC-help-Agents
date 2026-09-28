#!/usr/bin/env python3
"""Deterministic manuscript checks (standard library only).

- word counts per section, abstract, and main text
- numbers in the abstract that do not appear in the main text
- leftover placeholders ([MISSING: ...], TODO, XXX, [REF], [citation needed])
- promotional / hype terms
- figure and table references: gaps and first-mention order

Sections are detected from Markdown headings (#, ##) or from lines that consist
only of a common section name (Abstract, Introduction, Methods, ...).

Usage:
  python3 manuscript_checks.py manuscript.md [--abstract-limit 250]
                              [--main-limit 3500] [--json]
"""

import argparse
import json
import re
import sys

SECTION_NAMES = [
    "abstract", "summary", "background", "introduction", "methods",
    "materials and methods", "patients and methods", "methodology", "results",
    "discussion", "conclusion", "conclusions", "limitations", "references",
    "bibliography", "acknowledgments", "acknowledgements", "declarations",
    "funding", "supplementary material", "appendix", "keywords", "figure legends",
    "tables", "data availability", "author contributions", "conflicts of interest",
]
# German (and common variant) headings mapped to canonical English names
SECTION_ALIASES = {
    "zusammenfassung": "abstract", "kurzfassung": "abstract", "hintergrund": "background",
    "einleitung": "introduction", "einführung": "introduction", "methoden": "methods",
    "methodik": "methodology", "material und methoden": "materials and methods",
    "material and methods": "materials and methods", "data and methods": "methods",
    "methods and materials": "materials and methods", "study design and methods": "methods", "patienten und methoden": "patients and methods",
    "ergebnisse": "results", "diskussion": "discussion", "schlussfolgerung": "conclusion",
    "schlussfolgerungen": "conclusions", "fazit": "conclusion", "limitationen": "limitations",
    "limitations of the study": "limitations", "literatur": "references",
    "literaturverzeichnis": "references", "quellen": "references", "danksagung": "acknowledgments",
    "schlüsselwörter": "keywords", "key words": "keywords", "abbildungslegenden": "figure legends",
}
MAIN_TEXT = {"introduction", "background", "methods", "materials and methods",
             "patients and methods", "methodology", "results", "discussion",
             "conclusion", "conclusions", "limitations"}
NON_BODY = {"abstract", "summary", "keywords", "references", "bibliography"}
PLACEHOLDER_RE = re.compile(
    r"\[MISSING[^\]]*\]|\bTODO\b|\bTBD\b|\bXXX+\b|\[REF\]|\[citation needed\]|\?\?\?", re.I)
HYPE_TERMS = [
    "groundbreaking", "ground-breaking", "revolutionary", "remarkable", "unprecedented",
    "highly innovative", "game-changing", "game changer", "paradigm shift", "cutting-edge",
    "state-of-the-art performance", "breakthrough", "perfect accuracy",
    "it is important to note", "plays a crucial role", "in today's world", "delve",
]
NUMBER_RE = re.compile(r"(?<![\w.])[-−]?\d+(?:[.,]\d+)?(?![\w])")
FIG_RE = re.compile(r"\b(Fig(?:ure)?s?\.?|Table)s?\s+(\d+)", re.I)


def heading_name(line):
    stripped = line.strip()
    md = re.match(r"^#{1,6}\s+(.*)$", stripped)
    text = md.group(1) if md else stripped
    text = re.sub(r"^\d+(\.\d+)*\.?\s+", "", text).strip().rstrip(":").strip()
    lower = text.lower()
    if md:
        return lower if lower else None
    return lower if canonical(lower) in SECTION_NAMES else None


def split_sections(text):
    sections = [("_preamble", [])]
    for line in text.splitlines():
        name = heading_name(line)
        # subsection headings (e.g. "### 2.1 Data") stay inside their parent section
        if name is not None and canonical(name) in SECTION_NAMES:
            sections.append((canonical(name), []))
        else:
            sections[-1][1].append(line)
    merged = {}
    order = []
    for name, lines in sections:
        base = canonical(name)
        if base not in merged:
            merged[base] = []
            order.append(base)
        merged[base].extend(lines)
    return [(n, "\n".join(merged[n])) for n in order]


def canonical(name):
    name = SECTION_ALIASES.get(name, name)
    for known in SECTION_NAMES:
        if name == known or name.startswith(known + " "):
            return known
    return name


def words(text):
    return len(re.findall(r"[A-Za-zÀ-ſ0-9]+(?:[-'.][A-Za-z0-9]+)*", text))


def norm_number(tok):
    tok = tok.replace("−", "-").replace(",", ".")
    try:
        val = float(tok)
    except ValueError:
        return tok
    return f"{val:g}"


def abstract_numbers_missing(abstract, body):
    body_nums = {norm_number(t) for t in NUMBER_RE.findall(body)}
    missing = []
    for tok in NUMBER_RE.findall(abstract):
        n = norm_number(tok)
        if n not in body_nums and n not in missing:
            missing.append(n)
    return missing


CAPTION_LINE_RE = re.compile(r"^[\s*_]*(fig(?:ure)?s?\.?|table)\s+\d+[a-z]?[\s*_]*[.:|]", re.I | re.M)


def figure_table_refs(body, full_text=None):
    """Figure/table numbers cited in running text; caption lines do not count."""
    # captions may sit after the reference list (typical for journal submissions)
    raw_body = full_text if full_text is not None else body
    body = CAPTION_LINE_RE.sub(" ", body)
    firsts = {"figure": [], "table": []}
    for kind, num in FIG_RE.findall(body):
        key = "table" if kind.lower().startswith("table") else "figure"
        n = int(num)
        if n not in firsts[key]:
            firsts[key].append(n)
    captioned = {"figure": set(), "table": set()}
    for m in CAPTION_LINE_RE.finditer(raw_body):
        num = int(re.search(r"\d+", m.group(0)).group(0))
        captioned["table" if m.group(1).lower().startswith("table") else "figure"].add(num)
    report = {}
    for key in firsts:
        seq = firsts[key]
        if not seq and not captioned[key]:
            continue
        expected = list(range(1, max(seq + sorted(captioned[key])) + 1))
        report[key] = {
            "mentioned": sorted(seq),
            "gaps": [n for n in expected if n not in seq and n not in captioned[key]],
            "captions_not_cited": sorted(captioned[key] - set(seq)),
            "first_mention_order_ok": seq == sorted(seq),
        }
    return report


def run_checks(text, abstract_limit=None, main_limit=None):
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)  # traceability markers
    sections = split_sections(text)
    counts = {name: words(body) for name, body in sections if name != "_preamble" or body.strip()}
    abstract = "\n".join(b for n, b in sections if n in ("abstract", "summary"))
    # keywords typed inside the abstract section do not count towards the abstract
    abstract = re.split(r"^[\s*_]*(key ?words|schlüsselwörter)\b", abstract, maxsplit=1, flags=re.I | re.M)[0]
    body = "\n".join(b for n, b in sections if n not in NON_BODY and n != "_preamble")
    main_words = sum(words(b) for n, b in sections if n in MAIN_TEXT)
    lower = text.lower()
    hype = sorted({t for t in HYPE_TERMS if re.search(r"\b" + re.escape(t) + r"\b", lower)})
    placeholders = PLACEHOLDER_RE.findall(text)
    report = {
        "section_word_counts": counts,
        "abstract_words": words(abstract),
        "main_text_words": main_words,
        "abstract_numbers_not_in_main_text": abstract_numbers_missing(abstract, body) if abstract else [],
        "placeholders": placeholders,
        "hype_terms": hype,
        "figure_table_references": figure_table_refs(body, text),
        "issues": [],
    }
    issues = report["issues"]
    if not abstract:
        issues.append("no Abstract section detected")
    if abstract_limit and report["abstract_words"] > abstract_limit:
        issues.append(f"abstract {report['abstract_words']} words > limit {abstract_limit}")
    if main_limit and main_words > main_limit:
        issues.append(f"main text {main_words} words > limit {main_limit}")
    if report["abstract_numbers_not_in_main_text"]:
        issues.append("abstract contains numbers not found in main text: "
                      + ", ".join(report["abstract_numbers_not_in_main_text"]))
    if placeholders:
        issues.append(f"{len(placeholders)} placeholder(s) left")
    if hype:
        issues.append("promotional terms: " + ", ".join(hype))
    for key, info in report["figure_table_references"].items():
        if info["gaps"]:
            issues.append(f"{key} numbers never mentioned: {info['gaps']}")
        if info.get("captions_not_cited"):
            issues.append(f"{key} caption(s) never cited in the text: {info['captions_not_cited']}")
        if not info["first_mention_order_ok"]:
            issues.append(f"{key}s are not first mentioned in numerical order")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manuscript")
    ap.add_argument("--abstract-limit", type=int)
    ap.add_argument("--main-limit", type=int)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    with open(args.manuscript, encoding="utf-8-sig") as fh:
        report = run_checks(fh.read(), args.abstract_limit, args.main_limit)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for key, value in report.items():
            if key != "issues":
                print(f"{key}: {value}")
        print("ISSUES:" if report["issues"] else "ISSUES: none")
        for issue in report["issues"]:
            print(f"  - {issue}")
    return 1 if report["issues"] else 0


if __name__ == "__main__":
    sys.exit(main())
