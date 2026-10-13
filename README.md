# AI-Powered Legal Intelligence System (Vidhi-AI)

An end-to-end, privacy-respecting AI legal intelligence platform for Indian law, featuring dual-module hybrid RAG (Retrieval-Augmented Generation), clause-by-clause contract risk analysis, multi-turn legal consultation case threads, and tamper-evident PDF export.

## 🚀 Live Deployments

- **Frontend (Vercel):** [https://ai-powered-legal-intelligence-syste.vercel.app/](https://ai-powered-legal-intelligence-syste.vercel.app/)
- **Backend (Render):** [https://legal-ai-backend-tep5.onrender.com](https://legal-ai-backend-tep5.onrender.com)
- **Interactive API Documentation:** [https://legal-ai-backend-tep5.onrender.com/docs](https://legal-ai-backend-tep5.onrender.com/docs)
- **API Health Check:** [https://legal-ai-backend-tep5.onrender.com/api/health](https://legal-ai-backend-tep5.onrender.com/api/health)

---

## 🏛️ System Architecture & Highlights

### 1. Dual-Module Intelligence
- **Legal Issue Analyzer (Module 1):** Translates layperson legal queries into structured legal assessments with key facts, missing facts, applicable statutes, relevant Supreme Court precedents, and tactical considerations. Supports continuous multi-turn case consultation threads with pinned composer and history resumption.
- **Document & Contract Risk Analyzer (Module 2):** Extracts text from uploaded contracts (PDF, DOCX, TXT, images with OCR fallback) and analyzes clauses individually for risk level, legal hazards, missing standard safeguards, and statutory compliance.

### 2. High-Performance Hybrid RAG Engine
- **Dense Vector Search:** Uses lightweight quantized ONNX embeddings (`sentence-transformers/all-MiniLM-L6-v2`) via `onnxruntime` and fast Rust `tokenizers` (<25 MB total memory footprint, eliminating heavy PyTorch/CUDA overhead and cloud timeouts).
- **Sparse BM25 Search:** Token-level keyword retrieval across statutory acts and Supreme Court judgments.
- **Reciprocal Rank Fusion (RRF):** Fuses dense vector scores and sparse BM25 ranks with dynamic metadata verification to guarantee zero hallucinations and verifiable citations.

### 3. Privacy & Authentication
- **Anonymous One-Time Allowance:** Unregistered visitors can test an analysis once without an account; enforced securely via server-side hashed identifier tracking.
- **Full User Accounts:** JWT session tokens with HTTP-only cookies, bcrypt password hashing, and encrypted database records for full conversation and document history.
- **Data Minimization:** Uploaded documents are analyzed and raw files are purged immediately from disk after processing.
- **Client-Side Export Isolation:** Anonymous PDF reports are assembled purely in the browser memory, preventing data leaks.

---

## 📂 Project Directory Structure

```text
legal_rag_project/
├── backend/
│   ├── app/
│   │   ├── fonts/              # Custom TrueType fonts for PDF generation
│   │   ├── models/             # SQLAlchemy ORM models (User, Document, Case, Issue)
│   │   ├── routers/            # FastAPI endpoints (auth, issues, documents, cases, health)
│   │   ├── schemas/            # Pydantic v2 validation models
│   │   ├── services/           # Business logic (RAG pipeline, risk engine, PDF builder, auth)
│   │   ├── config.py           # Environment and app configuration
│   │   ├── database.py         # SQLite / PostgreSQL database connection session
│   │   ├── deps.py             # FastAPI dependency injections (JWT auth, DB session)
│   │   └── main.py             # FastAPI application entrypoint with lifespan pre-warming
│   ├── requirements.txt        # Backend standalone pip specifications
│   ├── test_auth_privacy.py    # Automated test suite for authentication & privacy
│   └── test_cases_and_reports.py # Automated test suite for case threads & reports
├── chroma_cases/               # ChromaDB vector index for Indian Supreme Court case law
├── chroma_laws/                # ChromaDB vector index for Indian statutory bare acts
├── embedding_model/            # Quantized ONNX model & tokenizer assets (all-MiniLM-L6-v2)
├── frontend/
│   ├── src/
│   │   ├── components/         # Modular React UI components (cards, gauges, auth modal, layout)
│   │   ├── context/            # React AuthContext provider
│   │   ├── pages/              # Core pages (Dashboard, IssueAnalyzer, DocumentAnalyzer, History)
│   │   ├── services/           # Axios API client and response normalization
│   │   ├── App.jsx             # React router setup and backend dyno pre-wake
│   │   └── index.css           # Tailwind CSS design system tokens
│   ├── package.json            # Node dependencies
│   ├── vercel.json             # Vercel deployment and routing rules
│   └── vite.config.js          # Vite build configuration
├── bm25_cases.pkl              # BM25 sparse index for Supreme Court case judgments
├── bm25_laws.pkl               # BM25 sparse index for statutory bare acts
├── build_case_dataset.py       # Sourcing and cleaning script for Supreme Court case corpus
├── build_dataset.py            # Sourcing and cleaning script for Indian bare acts corpus
├── build_indices.py            # Generates ChromaDB vectors and BM25 pickles from JSON data
├── case_law_master.json        # Normalized master dataset of 105+ Supreme Court cases
├── indian_legal_acts_master.json # Normalized master dataset of 825+ statutory sections
├── e2e_auth_ui.py              # Playwright E2E browser tests for auth flows
├── e2e_cookie_samesite.py      # Playwright E2E browser test for anonymous cookie enforcement
├── e2e_features_ab.py          # Playwright E2E browser test for multi-turn threads & PDF export
├── issue_analyzer.py           # Structured legal reasoning engine using Groq LLM
├── llm_client.py               # Robust Groq client with retry and error boundaries
├── rag_engine.py               # Unified ONNX hybrid retrieval engine (Dense + Sparse RRF)
├── render.yaml                 # Infrastructure as Code deployment blueprint for Render
├── requirements.txt            # Production dependencies for Render cloud container
├── test_rag.py                 # Retrieval and prompt generation unit tests
└── test_retrieval.py           # Hybrid retrieval benchmark tests
```

---

## 🛠️ Local Development Setup

### 1. Backend Setup
```bash
# Clone the repository
git clone https://github.com/NikhatMomin2509/ai-powered-legal-intelligence-system.git
cd legal_rag_project

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # On Linux/macOS
# or .venv\Scripts\activate      # On Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
# Create a .env file with:
# GROQ_API_KEY=your_groq_api_key
# JWT_SECRET_KEY=your_secure_secret_key
# ENVIRONMENT=development

# Start the FastAPI server
uvicorn backend.app.main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```

Visit `http://localhost:5173` in your browser.

---

## 🧪 Testing Suite

- **RAG & Hybrid Retrieval Test:** `python test_retrieval.py`
- **End-to-End Pipeline Test:** `python test_rag.py`
- **Backend API & Auth Test:** `python backend/test_auth_privacy.py`
- **Multi-Turn Case & PDF Export Test:** `python e2e_features_ab.py`

---

## 📄 License
MIT License. Built for Smart India Hackathon (SIH).
