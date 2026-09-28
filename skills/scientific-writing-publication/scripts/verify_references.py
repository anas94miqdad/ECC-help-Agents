#!/usr/bin/env python3
"""Verify references against Crossref and PubMed (standard library only).

Input: a CSV with any of the columns id, doi, pmid, title, year, first_author,
or a plain text file with one DOI or PMID per line.

For each reference the script looks up the authoritative record, compares
title, year and first author, and checks for retraction/correction notices.
It never invents metadata: anything it cannot confirm is reported as such.

Usage:
  python3 verify_references.py refs.csv [--out report.csv] [--json]

Environment:
  CROSSREF_MAILTO  contact address for the Crossref polite pool (recommended)
  NCBI_API_KEY     optional NCBI key for higher PubMed rate limits
"""

import argparse
import csv
import datetime
import difflib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

CROSSREF = "https://api.crossref.org"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TIMEOUT = 20
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
RETRACTION_TYPES = {"retraction", "withdrawal", "removal"}
CORRECTION_TYPES = {"correction", "erratum", "corrigendum", "expression_of_concern",
                    "expression-of-concern", "addendum", "clarification"}


# ---------- pure helpers (unit-tested, no network) ----------

def normalize_doi(value):
    if not value:
        return ""
    doi = value.strip()
    doi = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", doi, flags=re.I)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.I)
    return doi.rstrip(".").lower()


def is_valid_doi(doi):
    return bool(DOI_RE.match(doi or ""))


def fold(text):
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"<[^>]+>", " ", text)  # Crossref titles may contain markup
    text = re.sub(r"[^a-z0-9 ]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def title_similarity(a, b):
    a, b = fold(a), fold(b)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def surname(name):
    """Return the folded surname from 'Smith J', 'Smith, John', or 'John Smith'."""
    name = (name or "").strip()
    if not name:
        return ""
    if "," in name:
        return fold(name.split(",")[0])
    parts = name.split()
    # 'Smith J' / 'Smith JA' (PubMed style): initials come last
    if len(parts) > 1 and re.fullmatch(r"[A-Z]{1,3}\.?", parts[-1]):
        return fold(" ".join(parts[:-1]))
    return fold(parts[-1])


def compare(claimed, record):
    """Compare claimed metadata with an authoritative record.

    Returns (status, reasons). Status is VERIFIED, PARTIALLY_VERIFIED,
    REJECTED or RETRACTED.
    """
    reasons = []
    mismatches = 0
    hard_fail = False

    if claimed.get("title"):
        sim = title_similarity(claimed["title"], record.get("title", ""))
        if sim >= 0.9:
            pass
        elif sim >= 0.7:
            mismatches += 1
            reasons.append(f"title similarity {sim:.2f} (partial match)")
        else:
            hard_fail = True
            reasons.append(f"title mismatch (similarity {sim:.2f}): record title is "
                           f"'{record.get('title', '')}'")

    if claimed.get("year") and record.get("year"):
        try:
            diff = abs(int(str(claimed["year"])[:4]) - int(record["year"]))
        except ValueError:
            diff = None
        if diff is None:
            reasons.append("claimed year not parseable")
            mismatches += 1
        elif diff == 1:
            mismatches += 1
            reasons.append(f"year differs by 1 (record {record['year']}; online vs print?)")
        elif diff > 1:
            mismatches += 1
            reasons.append(f"year mismatch (record {record['year']})")

    if claimed.get("first_author") and record.get("first_author"):
        if surname(claimed["first_author"]) != surname(record["first_author"]):
            mismatches += 1
            reasons.append(f"first author mismatch (record {record['first_author']})")

    if record.get("retracted"):
        return "RETRACTED", reasons + ["retraction/withdrawal notice found"]
    if hard_fail:
        return "REJECTED", reasons
    if mismatches:
        return "PARTIALLY_VERIFIED", reasons
    if not any(claimed.get(k) for k in ("title", "year", "first_author")):
        return "PARTIALLY_VERIFIED", ["identifier resolves, but no claimed metadata to compare"]
    return "VERIFIED", reasons


def parse_crossref_work(message):
    title = (message.get("title") or [""])[0]
    year = None
    for key in ("published-print", "published-online", "issued", "created"):
        parts = (message.get(key) or {}).get("date-parts") or [[None]]
        if parts and parts[0] and parts[0][0]:
            year = int(parts[0][0])
            break
    authors = message.get("author") or []
    first = ""
    if authors:
        first = authors[0].get("family") or authors[0].get("name") or ""
    notices = []
    for upd in message.get("updated-by") or []:
        notices.append((upd.get("type") or "").lower())
    return {
        "title": title,
        "year": year,
        "first_author": first,
        "journal": (message.get("container-title") or [""])[0],
        "type": message.get("type", ""),
        "notices": notices,
    }


def notices_from_update_items(items, doi):
    """Extract notice types from works whose 'update-to' targets doi."""
    found = []
    for item in items:
        for upd in item.get("update-to") or []:
            if normalize_doi(upd.get("DOI")) == doi:
                found.append((upd.get("type") or "").lower())
    return found


def parse_pubmed_summary(result, pmid):
    doc = result.get(str(pmid)) or {}
    if not doc or doc.get("error"):
        return None
    year = None
    match = re.match(r"(\d{4})", doc.get("pubdate") or doc.get("epubdate") or "")
    if match:
        year = int(match.group(1))
    authors = doc.get("authors") or []
    doi = ""
    for aid in doc.get("articleids") or []:
        if aid.get("idtype") == "doi":
            doi = normalize_doi(aid.get("value"))
    pubtypes = [p.lower() for p in doc.get("pubtype") or []]
    return {
        "title": doc.get("title", ""),
        "year": year,
        "first_author": authors[0]["name"] if authors else "",
        "journal": doc.get("fulljournalname") or doc.get("source", ""),
        "doi": doi,
        "pubtypes": pubtypes,
        "retracted": "retracted publication" in pubtypes,
    }


def classify_notices(notices):
    retracted = any(n in RETRACTION_TYPES for n in notices)
    corrected = sorted({n for n in notices if n in CORRECTION_TYPES})
    return retracted, corrected


# ---------- network ----------

def _get_json(url):
    headers = {"User-Agent": "scientific-writing-publication-skill/2.0"}
    mailto = os.environ.get("CROSSREF_MAILTO")
    if mailto and url.startswith(CROSSREF):
        headers["User-Agent"] += f" (mailto:{mailto})"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def crossref_lookup(doi):
    msg = _get_json(f"{CROSSREF}/works/{urllib.parse.quote(doi)}")["message"]
    rec = parse_crossref_work(msg)
    try:
        q = urllib.parse.urlencode({"filter": f"updates:{doi}", "rows": 20})
        items = _get_json(f"{CROSSREF}/works?{q}")["message"].get("items", [])
        rec["notices"] += notices_from_update_items(items, doi)
        rec["notice_check"] = "ok"
    except (urllib.error.URLError, KeyError, ValueError, TimeoutError):
        rec["notice_check"] = "failed"
    rec["retracted"], rec["corrections"] = classify_notices(rec["notices"])
    return rec


def parse_handle_response(data):
    """Target URL from a doi.org handle API response, or None if not registered."""
    if not data or data.get("responseCode") != 1:
        return None
    for value in data.get("values", []):
        if value.get("type") == "URL":
            return value.get("data", {}).get("value", "")
    return ""


def doi_handle_target(doi):
    """None = not registered at doi.org; "" = could not check; else the target URL."""
    try:
        return parse_handle_response(_get_json(f"https://doi.org/api/handles/{urllib.parse.quote(doi)}"))
    except urllib.error.HTTPError as err:
        return None if err.code == 404 else ""
    except (urllib.error.URLError, TimeoutError, ValueError):
        return ""


def _eutils_params(extra):
    params = dict(extra, retmode="json")
    if os.environ.get("NCBI_API_KEY"):
        params["api_key"] = os.environ["NCBI_API_KEY"]
    return urllib.parse.urlencode(params)


def pubmed_lookup(pmid):
    data = _get_json(f"{EUTILS}/esummary.fcgi?" + _eutils_params({"db": "pubmed", "id": pmid}))
    return parse_pubmed_summary(data.get("result", {}), pmid)


def pubmed_pmid_for_doi(doi):
    data = _get_json(f"{EUTILS}/esearch.fcgi?" + _eutils_params({"db": "pubmed", "term": f"{doi}[doi]"}))
    ids = data.get("esearchresult", {}).get("idlist", [])
    return ids[0] if len(ids) == 1 else ""


# ---------- driver ----------

def load_references(path):
    with open(path, encoding="utf-8-sig") as fh:
        text = fh.read()
    first = text.splitlines()[0].lower() if text.strip() else ""
    if "," in first and any(k in first for k in ("doi", "pmid", "title")):
        rows = list(csv.DictReader(text.splitlines()))
        return [{k.strip().lower(): (v or "").strip() for k, v in r.items() if k} for r in rows]
    refs = []
    for i, line in enumerate(l.strip() for l in text.splitlines()):
        if not line or line.startswith("#"):
            continue
        key = "pmid" if line.isdigit() else "doi"
        refs.append({"id": str(i + 1), key: line})
    return refs


def verify_one(ref):
    today = datetime.date.today().isoformat()
    out = {"id": ref.get("id", ""), "doi": normalize_doi(ref.get("doi")), "pmid": ref.get("pmid", ""),
           "status": "UNVERIFIED", "verified_with": "", "verified_on": today,
           "record_title": "", "record_year": "", "record_first_author": "",
           "retraction_or_correction": "", "reasons": ""}
    reasons = []
    records = []

    if out["doi"]:
        if not is_valid_doi(out["doi"]):
            out["status"] = "REJECTED"
            out["reasons"] = "invalid DOI syntax"
            return out
        try:
            records.append(("Crossref", crossref_lookup(out["doi"])))
        except urllib.error.HTTPError as err:
            if err.code == 404:
                target = doi_handle_target(out["doi"])
                if target is None:
                    out["status"] = "REJECTED"
                    out["reasons"] = "DOI not found in Crossref and not registered at doi.org"
                    return out
                if target == "":
                    reasons.append("DOI not in Crossref; doi.org handle check not possible")
                else:
                    out["status"] = "PARTIALLY_VERIFIED"
                    out["verified_with"] = "doi.org"
                    out["reasons"] = ("DOI registered at doi.org with a non-Crossref agency (resolves to "
                                      f"{target}); metadata not compared, check title and year on the landing page")
                    out["retraction_or_correction"] = "notice check not possible"
                    return out
            reasons.append(f"Crossref HTTP {err.code}")
        except (urllib.error.URLError, TimeoutError, ValueError) as err:
            reasons.append(f"Crossref unreachable: {err}")
        if not out["pmid"]:
            try:
                out["pmid"] = pubmed_pmid_for_doi(out["doi"])
            except (urllib.error.URLError, TimeoutError, ValueError):
                pass

    if out["pmid"]:
        try:
            time.sleep(0.12 if os.environ.get("NCBI_API_KEY") else 0.35)
            rec = pubmed_lookup(out["pmid"])
            if rec is None:
                reasons.append("PMID not found in PubMed")
                if not records:
                    out["status"] = "REJECTED"
            else:
                if out["doi"] and rec.get("doi") and rec["doi"] != out["doi"]:
                    reasons.append(f"PubMed DOI {rec['doi']} differs from claimed DOI")
                records.append(("PubMed", rec))
        except (urllib.error.URLError, TimeoutError, ValueError) as err:
            reasons.append(f"PubMed unreachable: {err}")

    if not records:
        out["reasons"] = "; ".join(reasons) or "no DOI or PMID supplied"
        return out

    source, primary = records[0]
    retracted = any(r.get("retracted") for _, r in records)
    corrections = sorted({c for _, r in records for c in r.get("corrections", [])})
    primary = dict(primary, retracted=retracted)
    status, cmp_reasons = compare(ref, primary)
    if reasons and status == "VERIFIED":
        status = "PARTIALLY_VERIFIED"
    out.update({
        "status": status,
        "verified_with": "+".join(s for s, _ in records),
        "record_title": primary.get("title", ""),
        "record_year": primary.get("year") or "",
        "record_first_author": primary.get("first_author", ""),
    })
    flags = []
    if retracted:
        flags.append("RETRACTED")
    flags += corrections
    if not flags:
        checked = [s for s, r in records if s == "PubMed" or r.get("notice_check") == "ok"]
        flags.append(f"no notice found in {'+'.join(checked)} on {today}" if checked
                     else "notice check not possible")
    out["retraction_or_correction"] = "; ".join(flags)
    out["reasons"] = "; ".join(cmp_reasons + reasons)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("references")
    ap.add_argument("--out", help="write CSV report to this path")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args = ap.parse_args(argv)

    results = [verify_one(r) for r in load_references(args.references)]
    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(results[0].keys()) if results else ["id"])
            writer.writeheader()
            writer.writerows(results)
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            print(f"[{r['status']}] {r['id']} {r['doi'] or r['pmid']} :: {r['retraction_or_correction']}"
                  + (f" :: {r['reasons']}" if r["reasons"] else ""))
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("summary: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())), file=sys.stderr)
    return 1 if any(r["status"] in ("REJECTED", "RETRACTED") for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
