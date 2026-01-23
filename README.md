# MEXAR Ultimate 🧠

**Multimodal Explainable AI Reasoning Assistant**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-61dafb.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.109-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

MEXAR is an explainable AI system that creates domain-specific intelligent agents from your data. It uses **RAG (Retrieval-Augmented Generation)** with source attribution and faithfulness scoring to provide transparent, verifiable answers.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔍 **Hybrid Search** | Combines semantic (vector) + keyword search with RRF fusion |
| 🎯 **Cross-Encoder Reranking** | Improves retrieval precision using sentence-transformers |
| 📊 **Source Attribution** | Inline citations `[1]`, `[2]` linking answers to sources |
| ✅ **Faithfulness Scoring** | Measures how well answers are grounded in context |
| 🗣️ **Multimodal Input** | Audio (Whisper), Images (Vision), Video support |
| 🔐 **Domain Guardrails** | Prevents hallucinations outside knowledge base |
| 🔊 **Text-to-Speech** | ElevenLabs + Web Speech API support |
| 📁 **5 File Types** | CSV, PDF, DOCX, JSON, TXT |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MEXAR Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│   [User] ──► [React Frontend]                                     │
│                    │                                              │
│                    ▼                                              │
│   [FastAPI Backend]                                               │
│         │                                                         │
│         ├──► Data Validator (CSV/PDF/DOCX/JSON/TXT)              │
│         ├──► Prompt Analyzer (LLM-based domain extraction)       │
│         ├──► Knowledge Compiler (FastEmbed → pgvector)           │
│         └──► Reasoning Engine                                     │
│                    │                                              │
│                    ├──► Hybrid Search (semantic + keyword)        │
│                    ├──► Reranker (cross-encoder)                  │
│                    ├──► Source Attribution (inline citations)     │
│                    └──► Faithfulness Scorer (claim verification)  │
│                                                                   │
│   [External Services]                                             │
│         ├──► Supabase (PostgreSQL + Storage)                     │
│         ├──► Groq API (LLM + Whisper + Vision)                   │
│         └──► ElevenLabs (Text-to-Speech)                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** with pip
- **Node.js 18+** with npm
- **PostgreSQL** with `pgvector` extension (or use Supabase)
- **Groq API Key** - Get free at [console.groq.com](https://console.groq.com)

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Configure Environment Variables:**

Create `backend/.env`:
```env
# Required
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=postgresql://user:password@host:5432/database
SECRET_KEY=your_secure_secret_key

# Supabase Storage
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_service_role_key

# Optional: ElevenLabs TTS
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```

**Run Server:**
```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 📁 Project Structure

```
mexar_ultimate/
├── backend/
│   ├── api/                    # REST API endpoints
│   │   ├── auth.py            # Authentication (JWT)
│   │   ├── agents.py          # Agent CRUD
│   │   ├── chat.py            # Chat + multimodal
│   │   ├── compile.py         # Knowledge compilation
│   │   └── websocket.py       # Real-time updates
│   ├── core/                   # Core configuration
│   │   ├── config.py          # Settings
│   │   ├── database.py        # SQLAlchemy setup
│   │   └── security.py        # JWT handling
│   ├── models/                 # Database models
│   │   ├── user.py            # User model
│   │   ├── agent.py           # Agent + CompilationJob
│   │   ├── chunk.py           # DocumentChunk (pgvector)
│   │   └── conversation.py    # Chat history
│   ├── modules/                # Core AI modules
│   │   ├── data_validator.py  # File parsing
│   │   ├── prompt_analyzer.py # Domain extraction
│   │   ├── knowledge_compiler.py # Vector embeddings
│   │   ├── reasoning_engine.py # RAG pipeline
│   │   ├── multimodal_processor.py # Audio/Image/Video
│   │   └── explainability.py  # UI formatting
│   ├── utils/                  # Utility modules
│   │   ├── groq_client.py     # Groq API wrapper
│   │   ├── hybrid_search.py   # RRF search fusion
│   │   ├── reranker.py        # Cross-encoder
│   │   ├── faithfulness.py    # Claim verification
│   │   └── source_attribution.py # Citation extraction
│   ├── services/               # External services
│   │   ├── tts_service.py     # Text-to-speech
│   │   └── storage_service.py # Supabase storage
│   ├── main.py                 # FastAPI app entry
│   └── requirements.txt        # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── pages/             # React pages
│   │   │   ├── Landing.jsx    # Home page
│   │   │   ├── Login.jsx      # Authentication
│   │   │   ├── Dashboard.jsx  # User dashboard
│   │   │   ├── AgentCreation.jsx # Create agent
│   │   │   ├── CompilationProgress.jsx # Build progress
│   │   │   └── Chat.jsx       # Chat interface
│   │   ├── components/        # Reusable UI
│   │   ├── contexts/          # React contexts
│   │   ├── api/               # API client
│   │   └── App.jsx            # Main component
│   └── package.json           # Node dependencies
│
└── README.md
```

---

## 🔧 API Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login (returns JWT) |
| GET | `/api/auth/me` | Get current user |

### Agents
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/agents/` | List all agents |
| GET | `/api/agents/{name}` | Get agent details |
| DELETE | `/api/agents/{name}` | Delete agent |

### Compilation
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/compile/` | Start compilation (multipart) |
| GET | `/api/compile/{name}/status` | Check compilation status |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/` | Send message |
| POST | `/api/chat/multimodal` | Send with audio/image |
| GET | `/api/chat/{agent}/history` | Get chat history |
| POST | `/api/chat/transcribe` | Transcribe audio |

---

## 🧪 Technologies

### Backend
- **FastAPI** - Modern async Python web framework
- **SQLAlchemy** - ORM for PostgreSQL
- **pgvector** - Vector similarity search
- **FastEmbed** - Local embedding generation (BAAI/bge-small-en-v1.5)
- **sentence-transformers** - Cross-encoder reranking
- **Groq API** - LLM (Llama 3.1/3.3), Whisper (audio), Vision (images)

### Frontend
- **React 18** - UI framework
- **Material-UI** - Component library
- **React Router** - Navigation
- **Axios** - HTTP client

### External Services
- **Supabase** - Managed PostgreSQL + Storage
- **Groq** - Fast AI inference
- **ElevenLabs** - Text-to-Speech (optional)

---

## 📊 How It Works

### 1. Agent Creation
```
User uploads files → DataValidator parses → PromptAnalyzer extracts domain
                                         → KnowledgeCompiler creates embeddings
                                         → Stored in pgvector
```

### 2. Query Processing
```
User query → Domain Guardrail check
          → Hybrid Search (semantic + keyword)
          → Cross-Encoder Reranking (top 5)
          → LLM Generation with context
          → Source Attribution (citations)
          → Faithfulness Scoring
          → Explainability formatting
```

### 3. Confidence Scoring
Confidence is calculated from:
- **Retrieval Quality** (35%) - How relevant the retrieved chunks are
- **Rerank Score** (30%) - Cross-encoder confidence
- **Faithfulness** (25%) - How grounded the answer is
- **Base Floor** (10%) - For in-domain queries

---

## 🌐 Deployment

See [implementation_plan.md](./implementation_plan.md) for detailed deployment instructions covering:
- GitHub repository setup
- Vercel (frontend)
- Render.com (backend)
- Neon PostgreSQL (database)

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- [Groq](https://groq.com) - Fast AI inference
- [Supabase](https://supabase.com) - Postgres + Storage
- [FastEmbed](https://github.com/qdrant/fastembed) - Embeddings
- [sentence-transformers](https://www.sbert.net) - Reranking models
