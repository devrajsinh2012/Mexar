# MEXAR Ultimate 🧠

**Multimodal Explainable AI Reasoning Assistant**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-61dafb.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.109-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Deployed](https://img.shields.io/badge/status-live-brightgreen.svg)](https://mexar.vercel.app)

> Create domain-specific intelligent agents from your data with transparent, explainable AI responses using RAG (Retrieval-Augmented Generation) with source attribution and faithfulness scoring.

**🚀 Live Demo**: [https://mexar.vercel.app](https://mexar.vercel.app)  
**📡 Backend API**: [https://devrajsinh2012-mexar.hf.space](https://devrajsinh2012-mexar.hf.space)

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔍 **Hybrid Search** | Combines semantic (vector) + keyword search with RRF fusion for optimal retrieval |
| 🎯 **Cross-Encoder Reranking** | Improves retrieval precision using sentence-transformers |
| 📊 **Source Attribution** | Inline citations `[1]`, `[2]` linking answers to source data |
| ✅ **Faithfulness Scoring** | Measures how well answers are grounded in retrieved context |
| 🗣️ **Multimodal Input** | Audio (Whisper), Images (Vision), Video support |
| 🔐 **Domain Guardrails** | Prevents hallucinations outside knowledge base |
| 🔊 **Text-to-Speech** | ElevenLabs + Web Speech API integration |
| 📁 **5 File Types** | CSV, PDF, DOCX, JSON, TXT |

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              MEXAR Ultimate Stack                          │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│            ┌────────────────────────────────────────────┐                  │
│            │        React Frontend (Vercel)             │                  │
│            └────────────────────────────────────────────┘                  │
│                               │                                            │
│                               ▼                                            │
│            ┌────────────────────────────────────────────┐                  │
│            │     FastAPI Backend (Hugging Face Spaces)  │                  │
│            └────────────────────────────────────────────┘                  │
│                               │                                            │
│                               ▼                                            │
│   ┌────────────────────────────────────────────────────────────────────┐   │
│   │                        Core Intelligence Layer                     │   │
│   │                                                                    │   │
│   │   🔄 Data Validator        (PDF / DOCX / CSV / TXT / JSON)         │   │
│   │   🤖 Prompt Analyzer       (LLM-based Intent Parsing)              │   │
│   │   📦 Knowledge Compiler    (FastEmbed + Chunking)                  │   │
│   │   🧠 Reasoning Engine                                              │   │
│   │      ├─ Hybrid Search       (Dense + Sparse)                       │   │
│   │      ├─ Cross-Encoder       (Re-ranking)                           │   │
│   │      ├─ Source Attribution  (Citation Tracking)                    │   │
│   │      └─ Faithfulness Scorer (Hallucination Control)                │   │
│   │                                                                    │   │
│   └────────────────────────────────────────────────────────────────────┘   │
│                               │                                            │
│                               ▼                                            │
│   ┌────────────────────────────────────────────────────────────────────┐   │
│   │                        External Services Layer                     │   │
│   │                                                                    │   │
│   │   🗄 Supabase   → PostgreSQL + pgvector + File Storage             │   │
│   │   ⚡ Groq API   → LLM Inference + Whisper + Vision                │   │
│   │   🔊 ElevenLabs → Text-to-Speech                                  │   │
│   │                                                                    │   │
│   └────────────────────────────────────────────────────────────────────┘   │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘

```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** with pip
- **Node.js 18+** with npm
- **PostgreSQL** with `pgvector` extension (or use Supabase)
- **Groq API Key** - Get free at [console.groq.com](https://console.groq.com)

### Local Development

#### 1. Backend Setup

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

# Configure environment
cp .env.example .env
# Edit .env and add your API keys

# Run server
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Backend will run at**: [http://localhost:8000](http://localhost:8000)

#### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

**Frontend will run at**: [http://localhost:3000](http://localhost:3000)

---

## 📁 Project Structure

```
mexar_ultimate/
├── backend/                    # FastAPI Backend
│   ├── api/                   # REST API endpoints
│   │   ├── auth.py           # Authentication (JWT)
│   │   ├── agents.py         # Agent CRUD
│   │   ├── chat.py           # Chat + multimodal
│   │   ├── compile.py        # Knowledge compilation
│   │   └── websocket.py      # Real-time updates
│   ├── core/                  # Core configuration
│   │   ├── config.py         # Settings
│   │   ├── database.py       # SQLAlchemy setup
│   │   └── security.py       # JWT handling
│   ├── models/                # Database models
│   │   ├── user.py           # User model
│   │   ├── agent.py          # Agent + CompilationJob
│   │   ├── chunk.py          # DocumentChunk (pgvector)
│   │   └── conversation.py   # Chat history
│   ├── modules/               # Core AI modules
│   │   ├── data_validator.py # File parsing
│   │   ├── prompt_analyzer.py # Domain extraction
│   │   ├── knowledge_compiler.py # Vector embeddings
│   │   ├── reasoning_engine.py # RAG pipeline
│   │   └── explainability.py # UI formatting
│   ├── utils/                 # Utilities
│   │   ├── groq_client.py    # Groq API wrapper
│   │   ├── hybrid_search.py  # RRF search fusion
│   │   ├── reranker.py       # Cross-encoder
│   │   ├── faithfulness.py   # Claim verification
│   │   └── source_attribution.py # Citation extraction
│   ├── main.py               # FastAPI entry point
│   └── requirements.txt      # Python dependencies
│
├── frontend/                  # React Frontend
│   ├── src/
│   │   ├── pages/            # React pages
│   │   │   ├── Landing.jsx   # Home page
│   │   │   ├── Login.jsx     # Authentication
│   │   │   ├── Dashboard.jsx # User dashboard
│   │   │   ├── AgentCreation.jsx # Create agent
│   │   │   ├── CompilationProgress.jsx # Build progress
│   │   │   └── Chat.jsx      # Chat interface
│   │   ├── components/       # Reusable UI
│   │   ├── contexts/         # React contexts
│   │   ├── api/              # API client
│   │   └── App.jsx           # Main component
│   ├── package.json          # Node dependencies
│   └── vercel.json           # Vercel config
│
├── Dockerfile                 # Docker config for HF Spaces
└── README.md                  # This file
```

---

## 🌐 Deployment

### Current Deployment (Free Tier)

- **Frontend**: Vercel - [https://mexar.vercel.app](https://mexar.vercel.app)
- **Backend**: Hugging Face Spaces - [https://devrajsinh2012-mexar.hf.space](https://devrajsinh2012-mexar.hf.space)
- **Database**: Supabase (PostgreSQL with pgvector)
- **Storage**: Supabase Storage
- **Total Cost**: $0/month

### Deploy Your Own Instance

#### Deploy Backend to Hugging Face Spaces

1. Fork this repository
2. Create a new Space at [huggingface.co/new-space](https://huggingface.co/new-space)
3. Select **Docker** as SDK
4. Connect your GitHub repository
5. Add Repository Secrets:
   - `GROQ_API_KEY`
   - `DATABASE_URL`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `SECRET_KEY`
   - `FRONTEND_URL`

#### Deploy Frontend to Vercel

1. Import repository at [vercel.com](https://vercel.com)
2. Set **Root Directory** to `frontend`
3. Add Environment Variable:
   - `REACT_APP_API_URL` = Your HF Spaces URL

---

## 🔧 Environment Variables

### Backend (`backend/.env`)

```env
# Required: Get from console.groq.com
GROQ_API_KEY=your_groq_api_key_here

# Supabase Database
DATABASE_URL=postgresql://user:password@host:5432/database

# JWT Security
SECRET_KEY=generate-a-secure-random-key

# Supabase Storage
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_service_role_key

# Optional: ElevenLabs TTS
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Frontend URL for CORS
FRONTEND_URL=https://mexar.vercel.app
```

### Frontend (`frontend/.env`)

```env
# Backend API URL
REACT_APP_API_URL=https://your-backend.hf.space
```

---

## 🔍 API Documentation

Once the backend is running, interactive API docs are available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login (returns JWT) |
| GET | `/api/agents/` | List all agents |
| POST | `/api/compile/` | Start agent compilation |
| GET | `/api/compile/{name}/status` | Check compilation status |
| POST | `/api/chat/` | Send message to agent |
| POST | `/api/chat/multimodal` | Send with audio/image |

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
- **Material-UI (MUI)** - Component library
- **React Router** - Navigation
- **Axios** - HTTP client

### External Services
- **Supabase** - Managed PostgreSQL + Storage
- **Groq** - Fast AI inference (LPU architecture)
- **ElevenLabs** - Text-to-Speech (optional)

---

## 📊 How It Works

### 1. Agent Creation Flow
```
User uploads files → DataValidator parses content
                  → PromptAnalyzer extracts domain & keywords
                  → KnowledgeCompiler creates embeddings
                  → Stored in pgvector database
```

### 2. Query Processing Flow
```
User query → Domain Guardrail check
          → Hybrid Search (semantic + keyword)
          → Cross-Encoder Reranking (top 5 results)
          → LLM Generation with retrieved context
          → Source Attribution (extract citations)
          → Faithfulness Scoring (verify grounding)
          → Explainability Formatting
```

### 3. Confidence Calculation
Confidence score is calculated from:
- **Retrieval Quality** (35%) - Relevance of retrieved chunks
- **Rerank Score** (30%) - Cross-encoder confidence
- **Faithfulness** (25%) - Answer grounding in context
- **Base Floor** (10%) - For in-domain queries

---

## ⚠️ Known Limitations (Free Tier)

1. **Cold Start Delay**: First request after 15 min idle takes 45-90 seconds
2. **Model Download**: Initial startup takes 3-5 minutes (FastEmbed caching)
3. **Groq Rate Limits**: 30 requests/min, 14,400/day (free tier)
4. **Concurrent Users**: 1-2 recommended on free tier (2GB RAM limit)
5. **Ephemeral Storage**: HF Spaces `/tmp` data lost on restart (Supabase used for persistence)

**Production Migration**: Upgrade to paid tiers for ~$54/month (persistent instances, higher limits)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Groq](https://groq.com) - Fast AI inference with LPU technology
- [Supabase](https://supabase.com) - PostgreSQL + Storage platform
- [FastEmbed](https://github.com/qdrant/fastembed) - Lightweight embeddings library
- [sentence-transformers](https://www.sbert.net) - Reranking models
- [Hugging Face](https://huggingface.co) - Free ML model hosting

---

## 🤝 Contribution

This project is built by Devrajsinh Gohil and Jay Nasit under the guidance of Prof OM Prakash Suthar.

**Built with ❤️ using modern AI technologies**
