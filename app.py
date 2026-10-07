import os
import pickle
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def load_bm25_index():
    with open("bm25_index.pkl", "rb") as f:
        data = pickle.load(f)
    return data["bm25"], data["documents"]


def hybrid_retrieval(query, vector_db, bm25, documents, top_k=3):
    # Vector Search
    vector_results = vector_db.similarity_search(query, k=top_k)

    # BM25 Search
    tokenized_query = query.lower().split()
    bm25_scores = bm25.get_scores(tokenized_query)
    top_bm25_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:top_k]
    bm25_results = [documents[i] for i in top_bm25_indices]

    # Combine & Deduplicate
    combined_docs = {}
    for doc in vector_results + bm25_results:
        key = (doc.metadata.get("act"), doc.metadata.get("section"))
        if key not in combined_docs:
            combined_docs[key] = doc

    return list(combined_docs.values())


def main():
    print("Initializing Legal RAG Assistant...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    bm25, documents = load_bm25_index()
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.1)

    print("\n--- Indian Legal RAG AI Assistant Ready (Type 'exit' to quit) ---")

    while True:
        query = input("\nAsk a legal question: ").strip()
        if query.lower() in ["exit", "quit", "q"]:
            print("Exiting application.")
            break
        if not query:
            continue

        retrieved_docs = hybrid_retrieval(query, vector_db, bm25, documents, top_k=3)
        context = "\n\n".join(
            [f"[{doc.metadata['act']} Section {doc.metadata['section']}]: {doc.page_content}" for doc in
             retrieved_docs])

        prompt = f"""You are an expert Indian Legal AI Assistant. 
Answer the user's legal question based on the provided context below. 
If the exact provision is found in the context, cite the specific Act and Section.
If the context does not contain enough information to give a definitive answer, explain what relevant legal concept applies (e.g., Theft under IPC/BNS) based on general legal knowledge while stating that the specific section was not retrieved in the context.

CONTEXT:
{context}

USER QUESTION:
{query}

ANSWER:"""

        response = llm.invoke(prompt)
        print("\n" + "=" * 50)
        print(response.content)
        print("=" * 50)


if __name__ == "__main__":
    main()