import json
import pickle
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi


def load_data():
    with open("indian_legal_acts_master.json", "r", encoding="utf-8") as f:
        return json.load(f)


def build_indices():
    data = load_data()
    documents = []
    corpus_for_bm25 = []

    for item in data:
        full_text = f"Act: {item['act']} | Section: {item['section']} | Title: {item['title']}\nContent: {item['content']}"

        doc = Document(
            page_content=full_text,
            metadata={
                "act": item["act"],
                "section": item["section"],
                "title": item["title"],
                "category": item["category"]
            }
        )
        documents.append(doc)
        corpus_for_bm25.append(full_text.lower().split())

    # 1. Dense Vector Database (ChromaDB)
    print("Generating HuggingFace Embeddings & Chroma Vector DB...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory="./chroma_db"
    )
    print("Vector DB persisted to './chroma_db'")

    # 2. Sparse BM25 Index
    print("Building BM25 Sparse Index...")
    bm25 = BM25Okapi(corpus_for_bm25)

    with open("bm25_index.pkl", "wb") as f:
        pickle.dump({"bm25": bm25, "documents": documents}, f)
    print("BM25 Index saved to 'bm25_index.pkl'")


if __name__ == "__main__":
    build_indices()