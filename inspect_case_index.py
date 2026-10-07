"""
inspect_case_index.py — READ-ONLY diagnostic for the chroma_cases duplication
investigation. Does not call add/upsert/delete/update on anything. Safe to
run against the live, production chroma_cases directory as many times as
you like.
"""

import json
from collections import Counter

import chromadb

CHROMA_PATH = "./chroma_cases"
COLLECTION_NAME = "langchain"  # langchain-chroma's default collection name


def main():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collections = client.list_collections()
    print(f"Collections found in {CHROMA_PATH}: {[c.name for c in collections]}")

    # Use whatever collection actually exists rather than assuming the name.
    collection = collections[0] if len(collections) == 1 else client.get_collection(COLLECTION_NAME)

    total_count = collection.count()
    print(f"\nTotal vector count (collection.count()): {total_count}")

    # Pull everything — ids, metadatas, documents. For ~4300 short-ish chunks
    # this is a few MB, fine to pull in one call.
    result = collection.get(include=["metadatas", "documents"])
    ids = result["ids"]
    metadatas = result["metadatas"]
    documents = result["documents"]

    print(f"IDs returned: {len(ids)}")
    print(f"Unique IDs: {len(set(ids))}  (should equal total count if IDs are correctly unique)")

    # Group by (case_id, chunk_index) — this is the TRUE logical identity of
    # a chunk. If duplication is the "ran the build twice" bug, each
    # (case_id, chunk_index) pair should appear exactly 2x, under two
    # different random Chroma IDs.
    logical_keys = [(m.get("case_id"), m.get("chunk_index")) for m in metadatas]
    key_counts = Counter(logical_keys)

    unique_logical_chunks = len(key_counts)
    duplicated_keys = {k: c for k, c in key_counts.items() if c > 1}

    print(f"\nUnique logical chunks (case_id, chunk_index): {unique_logical_chunks}")
    print(f"Logical keys that appear more than once: {len(duplicated_keys)}")
    if duplicated_keys:
        counts_distribution = Counter(duplicated_keys.values())
        print(f"Distribution of duplicate counts (e.g. {{2: N}} means N chunks appear exactly twice): "
              f"{dict(counts_distribution)}")

    # Confirm duplicates are byte-identical content, not coincidentally
    # matching metadata with different text.
    if duplicated_keys:
        sample_key = next(iter(duplicated_keys))
        sample_indices = [i for i, k in enumerate(logical_keys) if k == sample_key]
        sample_texts = [documents[i] for i in sample_indices]
        sample_ids = [ids[i] for i in sample_indices]
        all_identical = len(set(sample_texts)) == 1
        print(f"\nSample duplicate group — logical key {sample_key}:")
        print(f"  Chroma IDs involved: {sample_ids}")
        print(f"  All copies have byte-identical page_content: {all_identical}")
        if not all_identical:
            print("  WARNING: copies differ in content — this would NOT be the simple "
                  "re-run-without-clearing bug, investigate further before cleaning up.")

    # Cross-check against the source dataset to compute the CORRECT expected
    # count (per Step 4's instruction: don't just assume 2150).
    try:
        with open("case_law_master.json", "r", encoding="utf-8") as f:
            source_cases = json.load(f)
        print(f"\ncase_law_master.json contains {len(source_cases)} case records "
              f"(cross-check this against build_indices.py's chunking to confirm "
              f"the expected chunk count independently).")
    except FileNotFoundError:
        print("\n(case_law_master.json not found in current directory — run this "
              "script from the project root to get the cross-check.)")

    print("\n--- SUMMARY ---")
    print(f"Total vectors: {total_count}")
    print(f"Unique logical chunks: {unique_logical_chunks}")
    print(f"Duplication confirmed: {total_count > unique_logical_chunks}")
    if total_count > 0 and unique_logical_chunks > 0:
        print(f"Ratio: {total_count / unique_logical_chunks:.2f}x")


if __name__ == "__main__":
    main()
