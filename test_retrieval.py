"""
test_retrieval.py — Phase 3 validation. Run this AFTER build_indices.py has
successfully created chroma_laws/, chroma_cases/, bm25_laws.pkl, bm25_cases.pkl.

For each test query, prints BM25-only, vector-only, and simple hybrid
(reciprocal rank fusion, k=60) results side by side, with full source
metadata, so results can be visually checked against the real datasets
(no fabricated content is possible here — everything printed is pulled
directly from indian_legal_acts_master.json / case_law_master.json content
that was embedded/indexed).
"""

import pickle
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

TEST_QUERIES = [
    "landlord refusing to return security deposit",
    "employee terminated without notice",
    "property dispute between landlord and tenant",
]


def load_bm25(path):
    with open(path, "rb") as f:
        return pickle.load(f)  # {"bm25":..., "documents":[Document,...]}


def bm25_search(bm25_data, query, k=5):
    tokenized_query = query.lower().split()
    scores = bm25_data["bm25"].get_scores(tokenized_query)
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
    return [(bm25_data["documents"][i], scores[i]) for i in ranked]


def vector_search(chroma_db, query, k=5):
    return chroma_db.similarity_search_with_score(query, k=k)


def reciprocal_rank_fusion(bm25_ranked_docs, vector_ranked_docs, k=60, top_n=5):
    """bm25_ranked_docs / vector_ranked_docs: list of (Document, score) in rank order."""
    scores = {}
    doc_lookup = {}
    for rank, (doc, _) in enumerate(bm25_ranked_docs):
        key = doc.page_content[:200]
        scores[key] = scores.get(key, 0) + 1.0 / (k + rank + 1)
        doc_lookup[key] = doc
    for rank, (doc, _) in enumerate(vector_ranked_docs):
        key = doc.page_content[:200]
        scores[key] = scores.get(key, 0) + 1.0 / (k + rank + 1)
        doc_lookup[key] = doc
    ranked_keys = sorted(scores.keys(), key=lambda k_: scores[k_], reverse=True)[:top_n]
    return [(doc_lookup[k_], scores[k_]) for k_ in ranked_keys]


def print_results(label, results):
    print(f"  --- {label} ---")
    for doc, score in results[:3]:
        meta = doc.metadata
        preview = doc.page_content[:140].replace("\n", " ")
        print(f"    score={score:.4f} | meta={meta} | {preview}...")


def main():
    print("Loading embeddings model (must match the one used to build the index)...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    chroma_laws = Chroma(persist_directory="./chroma_laws", embedding_function=embeddings)
    chroma_cases = Chroma(persist_directory="./chroma_cases", embedding_function=embeddings)
    bm25_laws = load_bm25("bm25_laws.pkl")
    bm25_cases = load_bm25("bm25_cases.pkl")

    print(f"\nLaw Chroma collection count: {chroma_laws._collection.count()}")
    print(f"Case Chroma collection count: {chroma_cases._collection.count()}")
    print(f"Law BM25 doc count: {len(bm25_laws['documents'])}")
    print(f"Case BM25 doc count: {len(bm25_cases['documents'])}")

    for query in TEST_QUERIES:
        print(f"\n{'='*80}\nQUERY: {query}\n{'='*80}")

        print("\n[LAWS]")
        bm25_res = bm25_search(bm25_laws, query)
        vec_res = vector_search(chroma_laws, query)
        hybrid_res = reciprocal_rank_fusion(bm25_res, vec_res)
        print_results("BM25", bm25_res)
        print_results("VECTOR", vec_res)
        print_results("HYBRID (RRF)", hybrid_res)

        print("\n[CASES]")
        bm25_res_c = bm25_search(bm25_cases, query)
        vec_res_c = vector_search(chroma_cases, query)
        hybrid_res_c = reciprocal_rank_fusion(bm25_res_c, vec_res_c)
        print_results("BM25", bm25_res_c)
        print_results("VECTOR", vec_res_c)
        print_results("HYBRID (RRF)", hybrid_res_c)


if __name__ == "__main__":
    main()
