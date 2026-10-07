import pickle
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


def load_bm25_index():
    with open("bm25_index.pkl", "rb") as f:
        data = pickle.load(f)
    return data["bm25"], data["documents"]


def hybrid_retrieval(query, top_k=3):
    # 1. Vector Search (ChromaDB)
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    vector_results = vector_db.similarity_search(query, k=top_k)

    # 2. Keyword Search (BM25)
    bm25, documents = load_bm25_index()
    tokenized_query = query.lower().split()
    bm25_scores = bm25.get_scores(tokenized_query)

    # Sort top BM25 results
    top_bm25_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:top_k]
    bm25_results = [documents[i] for i in top_bm25_indices]

    # Combine & Deduplicate Results
    combined_docs = {}
    for doc in vector_results + bm25_results:
        key = (doc.metadata.get("act"), doc.metadata.get("section"))
        if key not in combined_docs:
            combined_docs[key] = doc

    return list(combined_docs.values())


def generate_rag_prompt(query, retrieved_docs):
    context = "\n\n".join(
        [f"[{doc.metadata['act']} Section {doc.metadata['section']}]: {doc.page_content}" for doc in retrieved_docs])

    prompt = f"""You are an expert Indian Legal AI Assistant. Answer the user's legal question based ONLY on the provided context below. Cite the specific Act and Section in your answer.

CONTEXT:
{context}

USER QUESTION:
{query}

ANSWER:"""
    return prompt


if __name__ == "__main__":
    sample_query = "What is the punishment for cheating by personation using a computer?"

    print(f"Querying: '{sample_query}'\n")
    retrieved_docs = hybrid_retrieval(sample_query, top_k=2)

    print("--- RETRIEVED LEGAL SECTIONS ---")
    for idx, doc in enumerate(retrieved_docs, 1):
        print(f"\nResult {idx}:")
        print(f"Act: {doc.metadata.get('act')} | Section: {doc.metadata.get('section')}")
        print(f"Content: {doc.page_content[:150]}...")

    print("\n--- FORMATTED RAG PROMPT ---")
    prompt = generate_rag_prompt(sample_query, retrieved_docs)
    print(prompt)