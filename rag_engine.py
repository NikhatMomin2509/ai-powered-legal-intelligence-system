"""
rag_engine.py — shared retrieval engine for both Module 1 (Document Risk
Analyzer) and Module 2 (Legal Issue Analyzer).

Loads the Phase 3 artifacts (chroma_laws/, chroma_cases/, bm25_laws.pkl,
bm25_cases.pkl) ONCE at import time and exposes retrieval functions. Does
NOT rebuild any index — if these files are missing or empty, functions here
raise a clear error rather than silently returning nothing or fabricating
results.

Retrieval strategy: hybrid = dense (Chroma/MiniLM) + sparse (BM25), combined
with Reciprocal Rank Fusion (RRF, k=60 — a standard, parameter-light fusion
method: it only needs rank order from each method, not comparable score
scales, which matters here since BM25 scores and cosine-distance scores are
not on the same scale).

Every returned result carries its real source metadata (act/section/title
for laws; case_name/case_id/domain/source for cases) pulled directly from
the Phase 3 datasets — never invented.
"""

import os
import pickle
import re
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DATA_DIR = os.path.dirname(os.path.abspath(__file__))

RRF_K = 60  # standard RRF constant


class RAGEngineError(RuntimeError):
    """Raised when Phase 3 index artifacts are missing or unusable."""
    pass


def _require_file(path, what):
    if not os.path.exists(path):
        raise RAGEngineError(
            f"{what} not found at '{path}'. Run build_indices.py first (Phase 3) — "
            f"rag_engine.py does not build or fabricate indices."
        )


class RAGEngine:
    def __init__(self, data_dir=DATA_DIR):
        law_chroma_path = os.path.join(data_dir, "chroma_laws")
        case_chroma_path = os.path.join(data_dir, "chroma_cases")
        law_bm25_path = os.path.join(data_dir, "bm25_laws.pkl")
        case_bm25_path = os.path.join(data_dir, "bm25_cases.pkl")

        for path, label in [
            (law_chroma_path, "Law Chroma index"),
            (case_chroma_path, "Case Chroma index"),
            (law_bm25_path, "Law BM25 index"),
            (case_bm25_path, "Case BM25 index"),
        ]:
            _require_file(path, label)

        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

        self.chroma_laws = Chroma(persist_directory=law_chroma_path, embedding_function=self.embeddings)
        self.chroma_cases = Chroma(persist_directory=case_chroma_path, embedding_function=self.embeddings)

        with open(law_bm25_path, "rb") as f:
            self.bm25_laws = pickle.load(f)  # {"bm25":..., "documents":[Document,...]}
        with open(case_bm25_path, "rb") as f:
            self.bm25_cases = pickle.load(f)

        law_count = self.chroma_laws._collection.count()
        case_count = self.chroma_cases._collection.count()
        if law_count == 0:
            raise RAGEngineError("Law Chroma index exists but is EMPTY (0 documents). Not usable.")
        if case_count == 0:
            raise RAGEngineError("Case Chroma index exists but is EMPTY (0 documents). Not usable.")

        print(f"[rag_engine] Loaded: {law_count} law vectors, {case_count} case vectors, "
              f"{len(self.bm25_laws['documents'])} law BM25 docs, "
              f"{len(self.bm25_cases['documents'])} case BM25 docs.")

    # ---------- low-level: single-method retrieval ----------

    def _vector_search(self, chroma_db, query, top_k):
        results = chroma_db.similarity_search_with_score(query, k=top_k)
        return [(doc, score, "vector") for doc, score in results]

    def _bm25_search(self, bm25_data, query, top_k, tokenize_mode="simple"):
        # Phase 4 fix: the LAW index was rebuilt with a punctuation-stripping
        # regex tokenizer (build_indices.py's _tokenize_words). Query-time
        # tokenization here MUST match whatever built the index being queried,
        # or BM25 scores are meaningless. The CASE index's tokenization is
        # UNCHANGED (still .lower().split()) — left exactly as it was, per
        # instruction not to alter case retrieval behavior.
        if tokenize_mode == "words":
            tokens = re.findall(r"\b\w+\b", query.lower())
        else:
            tokens = query.lower().split()
        scores = bm25_data["bm25"].get_scores(tokens)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [(bm25_data["documents"][i], scores[i], "bm25") for i in ranked]

    def retrieve_laws(self, query, top_k=5):
        """Vector-only retrieval over the law index."""
        return self._vector_search(self.chroma_laws, query, top_k)

    def retrieve_cases(self, query, top_k=5):
        """Vector-only retrieval over the case index."""
        return self._vector_search(self.chroma_cases, query, top_k)

    # ---------- hybrid: RRF fusion of vector + BM25 ----------

    def _rrf_fuse(self, bm25_ranked, vector_ranked, dedup_key_fn, top_n):
        scores = {}
        doc_lookup = {}
        for rank, (doc, _, _) in enumerate(bm25_ranked):
            key = dedup_key_fn(doc)
            scores[key] = scores.get(key, 0.0) + 1.0 / (RRF_K + rank + 1)
            doc_lookup.setdefault(key, doc)
        for rank, (doc, _, _) in enumerate(vector_ranked):
            key = dedup_key_fn(doc)
            scores[key] = scores.get(key, 0.0) + 1.0 / (RRF_K + rank + 1)
            doc_lookup.setdefault(key, doc)
        ranked_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)[:top_n]
        return [(doc_lookup[k], scores[k], "hybrid") for k in ranked_keys]

    def hybrid_retrieve_laws(self, query, top_k=5, candidate_k=25):
        # candidate_k widened 15 -> 25 (Phase 4 fix C): with the law index now
        # dominated by 574 IPC sections against ~12 non-IPC provisions, a
        # narrow candidate pool from each method was more likely to be
        # entirely IPC before fusion even got a chance to surface the
        # correct (but numerically rare) non-IPC provision. This is a
        # parameter-only change — no re-embedding, no index rebuild, safe to
        # try and easy to revert. It widens recall; it does not fix ranking
        # quality by itself, which would need either a reranker or more
        # non-IPC coverage (both out of scope for this fix).
        bm25_ranked = self._bm25_search(self.bm25_laws, query, candidate_k, tokenize_mode="words")
        vector_ranked = self._vector_search(self.chroma_laws, query, candidate_k)
        # dedup by (act, section) — the real identity of a legal provision
        key_fn = lambda doc: (doc.metadata.get("act"), doc.metadata.get("section"))
        return self._rrf_fuse(bm25_ranked, vector_ranked, key_fn, top_k)

    def hybrid_retrieve_cases(self, query, top_k=5, candidate_k=20):
        bm25_ranked = self._bm25_search(self.bm25_cases, query, candidate_k)
        vector_ranked = self._vector_search(self.chroma_cases, query, candidate_k)
        # dedup by case_id — multiple chunks of the SAME case must collapse to one hit
        key_fn = lambda doc: doc.metadata.get("case_id")
        return self._rrf_fuse(bm25_ranked, vector_ranked, key_fn, top_k)

    # ---------- top-level: structured context for the LLM layer ----------

    def retrieve_legal_context(self, query, law_k=5, case_k=5):
        """
        Returns a dict with fully-structured, metadata-preserved results:
          {
            "laws": [{"ref_id": "L1", "act":..., "section":..., "title":...,
                       "category":..., "content":..., "score":...}, ...],
            "cases": [{"ref_id": "C1", "case_id":..., "case_name":...,
                        "domain":..., "source":..., "excerpt":..., "score":...}, ...]
          }
        ref_id is used so the LLM cites results by a stable short handle
        (L1, C2, ...) instead of having to reproduce section numbers or case
        names from memory — this is the main anti-hallucination mechanism:
        the LLM never needs to "recall" a citation, it only needs to point
        at one we already retrieved.
        """
        law_hits = self.hybrid_retrieve_laws(query, top_k=law_k)
        case_hits = self.hybrid_retrieve_cases(query, top_k=case_k)

        laws = []
        for i, (doc, score, method) in enumerate(law_hits, start=1):
            m = doc.metadata
            laws.append({
                "ref_id": f"L{i}",
                "act": m.get("act"),
                "section": m.get("section"),
                "title": m.get("title"),
                "category": m.get("category"),
                "source": m.get("source", ""),
                "content": doc.page_content,
                "retrieval_score": round(float(score), 4),
            })

        cases = []
        for i, (doc, score, method) in enumerate(case_hits, start=1):
            m = doc.metadata
            cases.append({
                "ref_id": f"C{i}",
                "case_id": m.get("case_id"),
                "case_name": m.get("case_name"),
                "domain": m.get("domain"),
                "source": m.get("source"),
                "excerpt": doc.page_content,
                "retrieval_score": round(float(score), 4),
            })

        return {"laws": laws, "cases": cases}


_engine_singleton = None


def get_engine():
    global _engine_singleton
    if _engine_singleton is None:
        _engine_singleton = RAGEngine()
    return _engine_singleton


# Module-level convenience functions matching the requested API surface.
def retrieve_laws(query, top_k=5):
    return get_engine().retrieve_laws(query, top_k)


def retrieve_cases(query, top_k=5):
    return get_engine().retrieve_cases(query, top_k)


def hybrid_retrieve_laws(query, top_k=5):
    return get_engine().hybrid_retrieve_laws(query, top_k)


def hybrid_retrieve_cases(query, top_k=5):
    return get_engine().hybrid_retrieve_cases(query, top_k)


def retrieve_legal_context(query, law_k=5, case_k=5):
    return get_engine().retrieve_legal_context(query, law_k, case_k)
