---
title: Mexar
emoji: 🧠
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
license: mit
---

<div align="center">

# 🧠 MEXAR

### **M**ultimodal **E**xplainable **A**I **R**easoning Assistant

*Build domain-specific AI agents from your documents — with transparent, grounded, and faithful answers.*

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg?style=for-the-badge&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688.svg?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18-61dafb.svg?style=for-the-badge&logo=react)](https://reactjs.org/)
[![Groq](https://img.shields.io/badge/Groq-LLM-f54e42.svg?style=for-the-badge)](https://groq.com/)
[![Supabase](https://img.shields.io/badge/Supabase-pgvector-3ECF8E?style=for-the-badge&logo=supabase)](https://supabase.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

<br/>

**🚀 Live App** → [mexar.vercel.app](https://mexar.vercel.app) &nbsp;&nbsp;|&nbsp;&nbsp; **📡 Backend API** → [devrajsinh2012-mexar.hf.space](https://devrajsinh2012-mexar.hf.space) &nbsp;&nbsp;|&nbsp;&nbsp; **📖 API Docs** → [/docs](https://devrajsinh2012-mexar.hf.space/docs)

</div>

---

## 📖 What is MEXAR?

MEXAR is a **full-stack, production-ready RAG (Retrieval-Augmented Generation) platform** that lets you create custom AI agents from your own documents. Unlike a simple chatbot, MEXAR is built around **explainability and faithfulness** — every answer is grounded in your source data, cited with inline references, and scored for hallucination risk using a NLI model.

**You upload documents → MEXAR compiles an agent → You chat with grounded, explainable AI.**

---

## ✨ Core Features

| Feature | Description |
|---|---|
| 🔍 **Hybrid RAG Search** | Semantic (pgvector cosine) + Keyword (BM25 tsvector) fused via Reciprocal Rank Fusion (RRF) |
| 🎯 **Cross-Encoder Reranking** | `sentence-transformers` cross-encoder re-scores top candidates for precision |
| 📎 **Inline Source Attribution** | Every answer references exact source chunks with `[1]`, `[2]` citations |
| ✅ **DeBERTa-v3 Faithfulness Scoring** | NLI-based hallucination detection scores answer grounding against retrieved context |
| 🔐 **Domain Guardrails** | TF-IDF + spaCy NER Jaccard similarity prevents out-of-domain queries (F1 = 0.9072 at threshold 0.25) |
| 🗣️ **Multimodal Input** | Audio (Groq Whisper), Images (Groq Vision), Video (OpenCV frame extraction) |
| 🔊 **Text-to-Speech** | ElevenLabs API + Web Speech API fallback |
| 🧠 **Explainability Panel** | Full reasoning trace: retrieval scores, confidence breakdown, sources cited, guardrail status |
| 📁 **5 Document Formats** | PDF, DOCX, CSV, JSON, TXT |
| ⚡ **Real-time WebSocket** | Streaming chat via WebSocket with progress tracking |
| 🔑 **JWT Auth** | Secure user accounts with bcrypt-hashed passwords and JWT bearer tokens |

---

## 🏗️ System Architecture

MEXAR is composed of four layers: Frontend, API, Intelligence, and Storage.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         USER INTERACTION LAYER                              │
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │            React 18 Frontend  ─  Vercel Edge Network                 │  │
│   │   Landing · Login · Dashboard · AgentCreation · Chat · Explainability │  │
│   └────────────────────────────┬─────────────────────────────────────────┘  │
│                                │ HTTPS / WebSocket                          │
└────────────────────────────────┼────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────────┐
│                      FASTAPI BACKEND  (HF Spaces / Docker)                  │
│                                                                             │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│   │  /auth   │  │ /agents  │  │  /chat   │  │ /compile │  │ /websocket │  │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
│                                                                             │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────────┐
│                        CORE INTELLIGENCE LAYER                              │
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌─────────────────────┐   │
│  │ DataValidator    │    │ KnowledgeCompiler│    │ MultimodalProcessor │   │
│  │ PDF/DOCX/CSV/TXT │───▶│ Chunking + Embed │    │ Whisper · Vision    │   │
│  │ /JSON parsing    │    │ FastEmbed bge-384│    │ OpenCV frames       │   │
│  └──────────────────┘    └────────┬─────────┘    └──────────┬──────────┘   │
│                                   │ Store chunks             │ Text         │
│  ┌──────────────────┐             ▼                          ▼              │
│  │ PromptAnalyzer   │    ┌───────────────────────────────────────────────┐  │
│  │ Intent · Domain  │───▶│           ReasoningEngine  (RAG Core)         │  │
│  │ Query Rewrite    │    │                                               │  │
│  └──────────────────┘    │  1. Domain Guardrail (TF-IDF + NER Jaccard)  │  │
│                          │  2. HybridSearcher (pgvector + BM25 RRF)     │  │
│  ┌──────────────────┐    │  3. CrossEncoder Reranker                    │  │
│  │ ExplainabilityGen│◀───│  4. SourceAttributor (citation tracking)     │  │
│  │ Reasoning trace  │    │  5. Groq LLM Answer Generation               │  │
│  │ Confidence score │    │  6. DeBERTa-v3 Faithfulness Scoring          │  │
│  └──────────────────┘    └───────────────────────────────────────────────┘  │
│                                                                             │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────────┐
│                         EXTERNAL SERVICES LAYER                             │
│                                                                             │
│  ┌──────────────────────┐  ┌──────────────────┐  ┌───────────────────────┐ │
│  │  Supabase / PostgreSQL│  │    Groq Cloud    │  │      ElevenLabs       │ │
│  │  pgvector extension  │  │ Llama 3.3 · 3.1  │  │  Text-to-Speech API   │ │
│  │  BM25 tsvector FTS   │  │ Whisper v3 Large │  │                       │ │
│  │  JWT sessions        │  │ Vision (preview)  │  └───────────────────────┘ │
│  └──────────────────────┘  └──────────────────┘                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Request Lifecycle — Step by Step

```
User Query
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  1. MULTIMODAL INPUT (optional)                       │
│     Audio → Groq Whisper STT → text                  │
│     Image → Groq Vision → described text             │
│     Video → OpenCV frame extract → Vision            │
└────────────────────────┬─────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│  2. PROMPT ANALYSIS                                   │
│     • Parse intent (factual / analytical / compare)  │
│     • Detect domain topic                            │
│     • Optionally rewrite query for clarity           │
└────────────────────────┬─────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│  3. DOMAIN GUARDRAIL CHECK                           │
│     • TF-IDF cosine similarity vs agent signature    │
│     • spaCy NER entity Jaccard overlap               │
│     • Threshold = 0.25  (F1 = 0.9072)               │
│     • If below threshold → reject with explanation   │
└────────────────────────┬─────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│  4. HYBRID RETRIEVAL                                 │
│     • Dense: FastEmbed bge-small-en (384-dim)        │
│       → pgvector cosine similarity search            │
│     • Sparse: PostgreSQL tsvector BM25 FTS           │
│     • Fuse both via Reciprocal Rank Fusion (RRF)     │
│       score = Σ 1/(rank + 60)                        │
│     • Return top-K=20 candidate chunks               │
└────────────────────────┬─────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│  5. CROSS-ENCODER RERANKING                          │
│     • sentence-transformers cross-encoder            │
│     • Re-scores top candidates for relevance         │
│     • Selects top-5 chunks as final context          │
└────────────────────────┬─────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│  6. LLM ANSWER GENERATION                            │
│     • Build system prompt with retrieved context     │
│     • Multi-model Groq inference with auto-fallback: │
│       llama-3.3-70b → llama-3.1-8b → mixtral-8x7b  │
│     • Answer generated with citations embedded       │
└────────────────────────┬─────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│  7. SOURCE ATTRIBUTION                               │
│     • Match answer sentences → source chunks         │
│     • Assign [1], [2], [3] reference markers         │
│     • Track provenance per claim                     │
└────────────────────────┬─────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│  8. FAITHFULNESS SCORING (DeBERTa-v3 NLI)            │
│     • Extract claims from answer                     │
│     • For each claim-chunk pair, NLI inference:      │
│       entailment → faithful                          │
│       contradiction → hallucinated                   │
│     • Batched with torch.inference_mode() (~1.2s)    │
│     • Output: faithfulness score 0.0–1.0             │
└────────────────────────┬─────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│  9. EXPLAINABILITY PACKAGING                         │
│     • Reasoning trace (step-by-step)                 │
│     • Confidence breakdown (domain + faithfulness)   │
│     • Sources cited (with file name + chunk text)    │
│     • Guardrail decision log                         │
└────────────────────────┬─────────────────────────────┘
                         │
                         ▼
                   Response to User
                 (Answer + Citations
                  + Faithfulness Score
                  + Explainability Panel)
```

---

## 🗂️ Project Structure

```
Mexar-main/
│
├── backend/                    # FastAPI Python backend
│   ├── api/                    # Route handlers
│   │   ├── auth.py             # JWT login / register
│   │   ├── agents.py           # Agent CRUD operations
│   │   ├── chat.py             # Chat endpoint (REST)
│   │   ├── compile.py          # Knowledge compilation jobs
│   │   ├── websocket.py        # Streaming WebSocket chat
│   │   ├── admin.py            # Admin panel routes
│   │   └── diagnostics.py      # System health checks
│   │
│   ├── modules/                # Core AI intelligence
│   │   ├── reasoning_engine.py # Main RAG pipeline (634 lines)
│   │   ├── knowledge_compiler.py # Doc ingestion + embedding
│   │   ├── data_validator.py   # File parsing (PDF/DOCX/CSV/TXT/JSON)
│   │   ├── prompt_analyzer.py  # Intent + domain classification
│   │   ├── multimodal_processor.py # Audio/Image/Video → text
│   │   └── explainability.py   # Reasoning trace packaging
│   │
│   ├── utils/                  # Utility modules
│   │   ├── hybrid_search.py    # pgvector + BM25 + RRF fusion
│   │   ├── faithfulness.py     # DeBERTa-v3 NLI scorer
│   │   ├── groq_client.py      # Multi-model Groq client + fallback
│   │   ├── reranker.py         # Cross-encoder reranking
│   │   ├── source_attribution.py # Citation tracking
│   │   ├── semantic_chunker.py # Adaptive text chunking
│   │   └── domain_signature.py # TF-IDF + NER signature builder
│   │
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── user.py             # User model
│   │   ├── agent.py            # Agent + CompilationJob
│   │   ├── chunk.py            # DocumentChunk (with vector)
│   │   └── conversation.py     # Conversation + Message
│   │
│   ├── migrations/
│   │   └── hybrid_search_function.sql  # PostgreSQL RRF function
│   │
│   ├── evaluation/             # Phase 3 benchmark suite
│   │   ├── run_all.py          # Master evaluation runner
│   │   └── guardrail_threshold_sweep.py
│   │
│   ├── scripts/                # Data collection scripts
│   │   ├── fetch_pubmed.py     # NCBI PubMed Open Access
│   │   ├── fetch_courtlistener.py  # CourtListener v4 API
│   │   └── fetch_secedgar.py   # SEC EDGAR 10-K filings
│   │
│   ├── static/index.html       # HF Spaces landing page
│   ├── main.py                 # FastAPI application entry
│   └── requirements.txt        # Python dependencies
│
├── frontend/                   # React 18 frontend
│   └── src/
│       ├── pages/
│       │   ├── Landing.jsx     # Marketing home page
│       │   ├── Login.jsx       # Authentication
│       │   ├── Dashboard.jsx   # Agent management hub
│       │   ├── AgentCreation.jsx # Upload + configure agent
│       │   ├── AgentList.jsx   # Browse your agents
│       │   ├── Chat.jsx        # Full chat interface (39KB)
│       │   └── CompilationProgress.jsx # Live compilation view
│       │
│       └── components/
│           ├── ExplainabilityModal.jsx # Reasoning trace viewer
│           ├── KnowledgeGraph.jsx      # Visual knowledge graph
│           ├── AudioRecorder.jsx       # Browser microphone input
│           ├── TTSPlayer.jsx           # TTS playback
│           ├── InlineTTS.jsx           # Per-sentence TTS
│           └── AgentSwitcher.jsx       # Switch between agents
│
├── test_data/                  # Real evaluation datasets
│   ├── medical_real/           # 31 PubMed PMC open-access papers
│   ├── legal_real/             # 148 CourtListener judicial opinions
│   ├── financial_real/         # 4 SEC EDGAR 10-K filings
│   └── query_sets/             # Evaluation query sets per domain
│
├── Dockerfile                  # Container definition (HF Spaces)
└── README.md
```

---

## 📊 Empirical Evaluation Results & Benchmarks

MEXAR has been evaluated against established baselines on real datasets sourced via public APIs.

### Knowledge Base — Real Multi-Domain Corpus

| Domain | Data Source | Files | Vector Chunks | Domain Signature Terms |
|---|---|:---:|:---:|:---:|
| 🏥 **Medical** | NCBI PubMed Central Open Access | 31 papers | **556 chunks** | 127 terms |
| ⚖️ **Legal** | CourtListener REST API v4 | 148 opinions | **157 chunks** | 152 terms |
| 📈 **Financial** | SEC EDGAR 10-K Filings | 4 filings | **68 chunks** | 119 terms |

### Table I — Multi-System Faithfulness Comparison

| System | Medical ↑ | Legal ↑ | Financial ↑ |
|---|:---:|:---:|:---:|
| Naive RAG | 0.0222 | 0.0333 | 0.0000 |
| BM25-only Retrieval | 0.0000 | 0.0000 | 0.0000 |
| LangChain RAG | 0.5000 | 0.5000 | 0.5000 |
| Self-RAG | 0.2380 | 0.0833 | N/A |
| **🧠 MEXAR (Ours)** | **0.1000** | **0.1000** | N/A |

> *Faithfulness scored via DeBERTa-v3-base NLI. Higher = better grounding.*

### Table II — Domain Guardrail Performance

| Metric | Value |
|---|:---:|
| Optimal Threshold | **0.25** |
| F1 Score | **0.9072** |
| Method | TF-IDF cosine + spaCy NER Jaccard |
| Mean Latency | **113.49 ms** |

### Table III — System Latency Profile

| Component | Latency |
|---|:---:|
| DeBERTa NLI Faithfulness (vectorized batch) | **~1.2s / query** |
| Domain Guardrail check | **113.49 ms** |
| Hybrid RRF Search (pgvector + BM25) | **< 100 ms** |
| Groq LLM inference (llama-3.1-8b) | **~800 ms** |

> **50x speedup** on faithfulness scoring achieved via `torch.inference_mode()` vectorized batching over the naive sequential baseline (~70s → ~1.2s).

### Expected Calibration Error (ECE)
> **ECE = 0.1000** — confidence scores are well-calibrated against empirical answer accuracy.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- PostgreSQL with `pgvector` extension (or [Supabase](https://supabase.com) free tier)
- [Groq API Key](https://console.groq.com) — free tier available

---

### 1. Clone & Configure

```bash
git clone https://github.com/devrajsinh2012/Mexar.git
cd Mexar-main
```

```bash
# Copy backend environment file
cp backend/.env.example backend/.env
# Fill in your credentials (see Environment Variables below)
```

---

### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Install spaCy model required for domain guardrail
python -m spacy download en_core_web_sm

# Apply database migration (PostgreSQL RRF hybrid search function)
psql $DATABASE_URL -f migrations/hybrid_search_function.sql

# Start backend server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Backend available at: `http://localhost:8000`  
Interactive API docs: `http://localhost:8000/docs`

---

### 3. Frontend Setup

```bash
cd frontend
npm install

# Set API URL
echo "REACT_APP_API_URL=http://localhost:8000" > .env

npm start
```

Frontend available at: `http://localhost:3000`

---

## 🔑 Environment Variables

```bash
# backend/.env

# === REQUIRED ===
GROQ_API_KEY=your_groq_api_key_here           # https://console.groq.com
DATABASE_URL=postgresql://user:pass@host:5432/db
SECRET_KEY=your_secure_jwt_secret_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_service_role_key

# === OPTIONAL ===
ELEVENLABS_API_KEY=your_elevenlabs_api_key    # Text-to-speech
FRONTEND_URL=https://mexar.vercel.app         # CORS origin

# === DATASET COLLECTION (scripts/) ===
COURTLISTENER_TOKEN=your_cl_token             # courtlistener.com
NCBI_EMAIL=your@email.com                     # NCBI policy requirement
NCBI_API_KEY=your_ncbi_api_key                # Raises rate limit 3→10 req/s
SEC_USER_AGENT=Firstname Lastname your@email.com  # SEC EDGAR fair access
```

---

## 🐳 Docker / Hugging Face Spaces Deployment

The project ships with a ready-to-use `Dockerfile` and is live on HF Spaces.

```bash
# Build locally
docker build -t mexar-backend ./backend
docker run -p 8000:8000 --env-file backend/.env mexar-backend
```

For **Hugging Face Spaces**, push to the `hf` remote:

```bash
git remote add hf https://huggingface.co/spaces/devrajsinh2012/mexar.git
git push hf main
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register a new user account |
| `POST` | `/api/auth/login` | Login and receive JWT token |
| `GET` | `/api/agents/` | List all compiled agents |
| `POST` | `/api/agents/` | Create a new agent |
| `POST` | `/api/compile/` | Start knowledge compilation from uploaded files |
| `GET` | `/api/compile/{job_id}` | Poll compilation job status |
| `POST` | `/api/chat/` | Send a query to an agent (REST) |
| `WS` | `/ws/chat/{agent_id}` | Real-time streaming chat (WebSocket) |
| `GET` | `/api/health` | Health check |
| `GET` | `/docs` | Interactive Swagger UI |

Full interactive documentation: [devrajsinh2012-mexar.hf.space/docs](https://devrajsinh2012-mexar.hf.space/docs)

---

## 🧠 Groq Model Fallback Chain

MEXAR implements a resilient multi-model fallback for Groq API rate limits:

```
openai/gpt-oss-120b
       │ (429 TPD quota)
       ▼
llama-3.3-70b-versatile
       │ (429 TPD quota)
       ▼
llama-3.1-8b-instant
       │ (429 TPD quota)
       ▼
mixtral-8x7b-32768
       │ (429 TPD quota)
       ▼
gemma2-9b-it
```

This ensures zero-downtime inference even under heavy usage within free-tier quotas.

---

## 🧪 Running Evaluations

```bash
# Fetch real datasets (requires API keys in .env)
python backend/scripts/fetch_pubmed.py      # NCBI PubMed
python backend/scripts/fetch_courtlistener.py  # CourtListener
python backend/scripts/fetch_secedgar.py    # SEC EDGAR

# Recompile domain agents from real data
python backend/scripts/recompile_agents_from_real_data.py

# Run full Phase 3 evaluation pipeline
python backend/evaluation/run_all.py

# Results saved to:
# backend/evaluation_outputs/full_evaluation_<timestamp>.json
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, React Router, Vercel |
| **Backend** | FastAPI 0.109, Uvicorn, Python 3.9+ |
| **Database** | PostgreSQL + `pgvector`, Supabase |
| **Vector Search** | FastEmbed `BAAI/bge-small-en-v1.5` (384-dim) |
| **Keyword Search** | PostgreSQL `tsvector` BM25 FTS |
| **RRF Fusion** | Custom SQL stored procedure |
| **LLM Inference** | Groq API (Llama 3.3, Llama 3.1, Mixtral, Gemma 2) |
| **Faithfulness** | `microsoft/deberta-v3-base` NLI via HuggingFace |
| **Reranking** | `sentence-transformers` cross-encoder |
| **Multimodal** | Groq Whisper v3 (audio), Groq Vision (images), OpenCV (video) |
| **TTS** | ElevenLabs API + Web Speech API |
| **Auth** | JWT (python-jose) + bcrypt (passlib) |
| **Deployment** | Hugging Face Spaces (Docker), Vercel (frontend) |
| **NLP** | spaCy `en_core_web_sm`, scikit-learn TF-IDF |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'feat: add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

<div align="center">


## 👨‍💻 Project Team

This Major Project is presented by:

**Devrajsinh Gohil** & **Jay Nasit**

Under the expert guidance of:

**Prof. Om Prakash Suthar**

---

[GitHub](https://github.com/devrajsinh2012/Mexar) · [HF Spaces](https://huggingface.co/spaces/devrajsinh2012/mexar) · [Live App](https://mexar.vercel.app)

</div>
