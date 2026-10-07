"""
regression_test_case_cleanup.py — run this AFTER the case-index cleanup
(Step 4) to verify retrieval still works and counts are correct.

Does not modify anything — read-only retrieval calls only.
"""

import chromadb
from rag_engine import retrieve_legal_context

QUERIES = [
    "My landlord is refusing to return my security deposit even though I left the apartment in good condition.",
    "Can police arrest a person without following the required procedure?",
    "My employer terminated me without giving notice.",
]


def main():
    client = chromadb.PersistentClient(path="./chroma_cases")
    collections = client.list_collections()
    coll = collections[0]
    print(f"chroma_cases collection count: {coll.count()}  (expected: 2150)")

    import pickle
    with open("bm25_cases.pkl", "rb") as f:
        bm25_data = pickle.load(f)
    print(f"bm25_cases.pkl document count: {len(bm25_data['documents'])}  (expected: 2150)")

    for query in QUERIES:
        print(f"\n{'='*80}\nQUERY: {query}\n{'='*80}")
        context = retrieve_legal_context(query, law_k=5, case_k=5)

        case_ids_seen = [c["case_id"] for c in context["cases"]]
        duplicates_in_result = len(case_ids_seen) != len(set(case_ids_seen))

        print(f"Retrieved {len(context['laws'])} laws, {len(context['cases'])} cases")
        print(f"Duplicate case_ids within this single result set: {duplicates_in_result}")
        for c in context["cases"]:
            print(f"  [{c['ref_id']}] case_id={c['case_id']} | {c['case_name'][:60]} | score={c['retrieval_score']}")


if __name__ == "__main__":
    main()
