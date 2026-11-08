#!/usr/bin/env python3
"""Bibliographic lookup helper (Crossref REST API + DOI content negotiation).
Usage:
  crossref.py search "<title words>" [rows]   -> top matches (title, authors, venue, year, DOI, type)
  crossref.py doi <DOI>                         -> full verified metadata + BibTeX from doi.org
Only prints what the registries return; never fills gaps."""
import sys, json, urllib.request, urllib.parse

UA = {"User-Agent": "pbti-literature-check/1.0 (research tooling)"}

def get(url, accept="application/json"):
    req = urllib.request.Request(url, headers={**UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")

def fmt(it):
    au = "; ".join(f"{a.get('family','?')}, {a.get('given','')}".strip() for a in it.get("author", []))
    yr = None
    for k in ("published-print", "published-online", "issued", "created"):
        dp = it.get(k, {}).get("date-parts")
        if dp and dp[0] and dp[0][0]:
            yr = dp[0]; break
    return {
        "title": (it.get("title") or [""])[0],
        "authors": au,
        "container": (it.get("container-title") or [""])[0],
        "type": it.get("type"),
        "date": yr,
        "volume": it.get("volume"), "issue": it.get("issue"),
        "page": it.get("page"), "article-number": it.get("article-number"),
        "publisher": it.get("publisher"), "DOI": it.get("DOI"),
        "published-online": it.get("published-online", {}).get("date-parts"),
        "published-print": it.get("published-print", {}).get("date-parts"),
    }

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "search":
        rows = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        q = urllib.parse.quote(sys.argv[2])
        data = json.loads(get(f"https://api.crossref.org/works?query.bibliographic={q}&rows={rows}"))
        for it in data["message"]["items"]:
            print(json.dumps(fmt(it), ensure_ascii=False))
    elif cmd == "doi":
        doi = sys.argv[2]
        data = json.loads(get(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"))
        print(json.dumps(fmt(data["message"]), ensure_ascii=False, indent=1))
        try:
            print(get(f"https://doi.org/{doi}", accept="application/x-bibtex"))
        except Exception as e:
            print("BIBTEX-NEGOTIATION-FAILED", e)
