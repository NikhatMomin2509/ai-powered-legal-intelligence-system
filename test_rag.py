"""
test_rag.py — Phase 4 validation.

Run this AFTER Phase 3 indices exist and .env has a real GROQ_API_KEY.

For each test query, prints:
  QUERY
  RETRIEVED LAWS       (real metadata: act, section, title, score)
  RETRIEVED CASES      (real metadata: case_name, domain, score)
  FINAL STRUCTURED RESPONSE (the full analyze_legal_issue() output)

This script does NOT judge relevance for you — that's an honest human
judgment call per query (see PHASE4.md "Evaluation" section for the
questions to ask). It only proves the pipeline runs end-to-end on real
data and shows you exactly what came back, so you can make that judgment.
"""

import json
from rag_engine import retrieve_legal_context
from issue_analyzer import analyze_legal_issue

TEST_QUERIES = {
    "A. Property/rental issue": "My landlord is refusing to return my security deposit even though I left the apartment in good condition.",
    "B. Employment issue": "My employer has not paid my salary for the last three months despite repeated requests.",
    "C. Consumer issue": "I bought a defective product online and the seller is refusing to replace it or give a refund.",
    "D. General legal question": "What are my rights if I am arrested by the police in India?",
}


def print_section(title):
    print(f"\n{'='*90}\n{title}\n{'='*90}")


def run_test(label, query):
    print_section(f"{label}\nQUERY: {query}")

    context = retrieve_legal_context(query, law_k=7, case_k=5)

    print("\n--- RETRIEVED LAWS (hybrid, top 7) ---")
    if not context["laws"]:
        print("  (none retrieved)")
    for law in context["laws"]:
        print(f"  [{law['ref_id']}] {law['act']} Sec {law['section']} — {law['title']} "
              f"(category={law['category']}, score={law['retrieval_score']})")

    print("\n--- RETRIEVED CASES (hybrid, top 5) ---")
    if not context["cases"]:
        print("  (none retrieved)")
    for case in context["cases"]:
        print(f"  [{case['ref_id']}] {case['case_name']} "
              f"(domain={case['domain']}, score={case['retrieval_score']})")

    print("\n--- FINAL STRUCTURED RESPONSE ---")
    try:
        result = analyze_legal_issue(query)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"  ERROR during analyze_legal_issue: {type(e).__name__}: {e}")


if __name__ == "__main__":
    for label, query in TEST_QUERIES.items():
        run_test(label, query)

    print_section("DONE — review each section above against PHASE4.md's evaluation checklist")
