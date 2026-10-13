"""
build_indices.py — builds TWO separate hybrid (vector + BM25) indices:
  1. Laws index   (from indian_legal_acts_master.json)   -> chroma_laws/, bm25_laws.pkl
  2. Cases index  (from case_law_master.json)             -> chroma_cases/, bm25_cases.pkl

Kept deliberately separate (rather than one merged index) so retrieval can
target "relevant law" and "relevant precedent" independently, which is what
both Module 1 and Module 2 need to show as distinct, separately-labeled
sections in the UI.

Adapted from the user's original build_index.py — same embedding model
(sentence-transformers/all-MiniLM-L6-v2, local/free, no API cost) and same
BM25Okapi sparse index, just parameterized over two datasets instead of one,
and case documents are chunked (they're full judgments, often 5-200k chars —
far too long to embed as a single vector) while law sections are not (they're
already short, self-contained provisions).

IDEMPOTENCY FIX (Phase 5 cleanup, post-hoc): build_case_index() previously
let Chroma.from_documents() assign a random UUID to every chunk on every
run. Since the installed langchain-chroma (1.1.0) already upserts internally,
re-running the build against an already-populated chroma_cases silently
appended a full duplicate copy (confirmed: 2150 -> 4300 vectors from one
extra run) rather than overwriting anything, because there was never a
matching ID to upsert against. Fixed by computing a deterministic
f"case_{case_id}_chunk{i}" id for every chunk and passing it explicitly, so
a rerun now overwrites each chunk in place. build_law_index() was NOT
touched — same latent pattern likely exists there, but that's out of scope
for this fix (law index change was not requested here).
"""

import argparse
import json
import os
import pickle
import re

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from langchain_chroma import Chroma
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi
from rag_engine import get_embeddings
CASE_CHUNK_SIZE = 1500       # chars per chunk for long judgment texts
CASE_CHUNK_OVERLAP = 200


def _tokenize_words(text):
    """Regex word tokenizer (strips punctuation) — used for the LAW BM25
    index only (Phase 4 fix: E. BM25 tokenization). The CASE index keeps the
    original .lower().split() tokenization completely unchanged, per explicit
    instruction not to alter case retrieval behavior — query-time tokenization
    in rag_engine.py must match whichever scheme built each index."""
    return re.findall(r"\b\w+\b", text.lower())


def chunk_text(text, size=CASE_CHUNK_SIZE, overlap=CASE_CHUNK_OVERLAP):
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return chunks


def build_law_index():
    print("=== Building LAW index ===")
    with open("indian_legal_acts_master.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    documents, corpus_for_bm25 = [], []
    for item in data:
        full_text = f"Act: {item['act']} | Section: {item['section']} | Title: {item['title']}\nContent: {item['content']}"
        doc = Document(
            page_content=full_text,
            metadata={
                "act": item["act"],
                "section": item["section"],
                "title": item["title"],
                "category": item["category"],
                "source": item.get("source", ""),  # new: preserved for the 9 new provisions; empty for older records that predate this field
            },
        )
        documents.append(doc)
        corpus_for_bm25.append(_tokenize_words(full_text))

    print(f"  {len(documents)} law documents to embed...")
    embeddings = get_embeddings()
    Chroma.from_documents(documents=documents, embedding=embeddings, persist_directory="./chroma_laws")
    print("  Vector DB persisted to './chroma_laws'")

    bm25 = BM25Okapi(corpus_for_bm25)
    with open("bm25_laws.pkl", "wb") as f:
        pickle.dump({"bm25": bm25, "documents": documents}, f)
    print("  BM25 index saved to 'bm25_laws.pkl'")


def build_case_index():
    print("=== Building CASE-LAW index ===")
    with open("case_law_master.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    documents, corpus_for_bm25, ids = [], [], []
    for item in data:
        chunks = chunk_text(item["full_text"])
        for i, chunk in enumerate(chunks):
            full_text = f"Case: {item['case_name']}\nSummary: {item['summary']}\nExcerpt: {chunk}"
            doc = Document(
                page_content=full_text,
                metadata={
                    "case_id": item["case_id"],
                    "case_name": item["case_name"],
                    "domain": item["domain"],
                    "source": item["source"],
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            )
            documents.append(doc)
            corpus_for_bm25.append(full_text.lower().split())
            # Deterministic ID — THE fix for the 2150->4300 duplication bug.
            # Without this, Chroma.from_documents() assigns a fresh random
            # UUID to every chunk on every run; langchain-chroma 1.1.0's
            # add_texts() already calls collection.upsert() internally, so a
            # STABLE id is the only thing needed to make re-running this
            # build idempotent (re-running overwrites each chunk in place
            # instead of adding a duplicate under a new random id).
            ids.append(f"case_{item['case_id']}_chunk{i}")

    print(f"  {len(documents)} case chunks to embed (from {len(data)} cases)...")
    embeddings = get_embeddings()
    Chroma.from_documents(documents=documents, embedding=embeddings, ids=ids, persist_directory="./chroma_cases")
    print("  Vector DB persisted to './chroma_cases'")

    bm25 = BM25Okapi(corpus_for_bm25)
    with open("bm25_cases.pkl", "wb") as f:
        pickle.dump({"bm25": bm25, "documents": documents}, f)
    print("  BM25 index saved to 'bm25_cases.pkl'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build law and/or case retrieval indices.")
    parser.add_argument("--laws-only", action="store_true",
                         help="Build/rebuild ONLY the law index (chroma_laws, bm25_laws.pkl). "
                              "Case index (chroma_cases, bm25_cases.pkl) is left completely untouched.")
    parser.add_argument("--cases-only", action="store_true",
                         help="Build/rebuild ONLY the case index. Law index is left untouched.")
    args = parser.parse_args()

    if args.laws_only and args.cases_only:
        raise SystemExit("Pass at most one of --laws-only / --cases-only (or neither, to build both).")

    if args.cases_only:
        build_case_index()
    elif args.laws_only:
        build_law_index()
    else:
        build_law_index()
        build_case_index()

    print("\nDone.")
