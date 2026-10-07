"""
build_case_dataset.py — Case-law knowledge base builder.

Source: 105 real, full-length Indian Supreme Court judgments (1950s-2000s era,
predominantly tenancy/eviction/property/constitutional law), sourced from the
MIT-licensed open-source project "JusticeRAG" (github.com/sassysohom48/JusticeRAG),
whose own README states these were parsed from real Supreme Court judgment text
(originally via the Supreme Court's public judgment corpus).

This is NOT a synthetic dataset — every case_name is a real, verifiable citation
(e.g. "V. Dhanapal Chettiar v. Yesodai Ammal (1979) 4 SCC 214") and the `text`
field is the actual judgment text, not a generated summary.

Attribution is preserved in every record's `source` field per the requirement
that every retrieved case shown to the user must be traceable.
"""

import json

SOURCE_ATTRIBUTION = (
    "JusticeRAG open dataset (MIT License), github.com/sassysohom48/JusticeRAG — "
    "real Indian Supreme Court judgment text"
)

# Lightweight domain tagging so case retrieval can be filtered/cross-referenced
# with law categories, using the same heuristic style as build_dataset.py.
DOMAIN_KEYWORDS = {
    "Property / Rental Dispute": ["tenant", "landlord", "eviction", "rent", "lease", "tenancy", "premises"],
    "Property / Land": ["land acquisition", "possession", "title", "property", "evacuee"],
    "Employment / Labour": ["workman", "employer", "employee", "retrenchment", "wages", "industrial dispute"],
    "Constitutional / Fundamental Rights": ["article 14", "article 19", "article 21", "constitution", "fundamental right"],
    "Contract / Commercial": ["contract", "agreement", "breach", "damages", "sale"],
}


def determine_domain(text):
    text_l = text.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(kw in text_l for kw in keywords):
            return domain
    return "General Civil / Other"


def build():
    with open("case_law_raw.json", "r", encoding="utf-8") as f:
        raw = json.load(f)

    processed = []
    for item in raw:
        full_text = item.get("text", "").strip()
        if not full_text:
            continue
        processed.append({
            "case_id": item.get("id"),
            "case_name": item.get("case_name", "").strip(),
            "summary": item.get("summary", "").strip(),
            "full_text": full_text,
            "domain": determine_domain(item.get("summary", "") + " " + full_text[:1000]),
            "source": SOURCE_ATTRIBUTION,
        })

    with open("case_law_master.json", "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=2, ensure_ascii=False)

    print(f"SUCCESS! Created 'case_law_master.json' with {len(processed)} real case records.")
    return processed


if __name__ == "__main__":
    build()
