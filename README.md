# ResuMatch AI — Local RAG-Powered Resume Analyzer & Chrome Extension

<p align="center">
  <img src="chrome-extension/icon128.png" alt="ResuMatch AI" width="80">
</p>

<p align="center">
  <strong>AI-powered resume-to-job matching that runs 100% on your machine.</strong><br>
  No API keys. No cloud. No data leaves your laptop.
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#how-it-works">How It Works</a> •
  <a href="#chrome-extension">Chrome Extension</a> •
  <a href="#api-reference">API Reference</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#hosting">Free Hosting Options</a>
</p>

---

## What Is ResuMatch AI?

ResuMatch AI is a **local RAG (Retrieval-Augmented Generation) pipeline** with a **Chrome extension** that analyzes job descriptions on LinkedIn, Indeed, Glassdoor, Naukri, and other job boards — and tells you:

- ✅ **Which resume to use** (compares multiple resumes)
- 📊 **ATS compatibility score** (keyword match, skill clusters, contextual placement, quantification)
- 🔍 **Why your resume doesn't fit** (gap analysis with specific missing skills)
- ✏️ **How to tailor it** (actionable suggestions to improve your match)
- ⚖️ **APPLY / MAYBE / SKIP** verdict with confidence scoring

All powered by HuggingFace models running locally on your machine.

---

## Features

### 2026-Grade ATS Scoring Engine
Mirrors how modern ATS platforms (Greenhouse, Workday, Lever, Taleo) evaluate resumes:

| Signal | Weight | Description |
|--------|--------|-------------|
| Keyword Match | 25% | Synonym-expanded matching (GenAI ↔ Generative AI, k8s ↔ Kubernetes) |
| Contextual Placement | 20% | Summary/Title: 3x weight, Skills: 2x, Recent roles: 1.5x |
| Skill Clusters | 20% | Groups related skills (PyTorch + TensorFlow → "Deep Learning") |
| Skill Categories | 15% | Hard skills, certifications, management, soft skills scored separately |
| Quantification | 10% | Detects $, %, numbers, multipliers, action verbs |
| Recency | 10% | Recent role keywords weighted higher |

### Multi-Resume Comparison
Drop multiple PDF resumes and the system compares each against the JD, recommending the best match.

### Smart JD Extraction
The Chrome extension has site-specific parsers for:
- **LinkedIn** — extracts "About the job" section, strips company boilerplate
- **Indeed** — targets `#jobDescriptionText`
- **Glassdoor, Naukri, Lever, Greenhouse, Workday** — dedicated selectors
- **Any site** — generic fallback with intelligent content detection

### Enterprise-Grade Pipeline
</p>

```
┌──────────────────────────────────────────────────────────────────┐
│  PRESENTATION — FastAPI routes, Pydantic schemas                 │
├──────────────────────────────────────────────────────────────────┤
│  SERVICES — Analysis orchestration, JD cleaning, LLM inference   │
├──────────────────────────────────────────────────────────────────┤
│  A) KNOWLEDGE LAYER                                              │
│     PII redaction before embedding, RBAC tagging, metadata       │
│  B) RETRIEVAL LAYER                                              │
│     FAISS + namespace isolation, query sanitization, ACL         │
│  C) VALIDATION LAYER                                             │
│     Guardrails, confidence scoring, output sanitization, audit   │
├──────────────────────────────────────────────────────────────────┤
│  OBSERVABILITY — Metrics, KPI dashboard, feedback loop           │
├──────────────────────────────────────────────────────────────────┤
│  DATA ACCESS — HuggingFace model loading, resume file I/O        │
└──────────────────────────────────────────────────────────────────┘
```

- **PII Redaction** — emails, phones, SSNs, Aadhaar, PAN numbers stripped before embedding
- **Governance Engine** — configurable policy rules, approval gates, threshold enforcement
- **Audit Logging** — every request logged with anomaly detection
- **Confidence Scoring** — falls back to rule-based analysis when LLM confidence is low
- **Output Sanitization** — score clamping, LLM artifact removal, PII leak prevention

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/resumatch-ai.git
cd resumatch-ai/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Add Your Resumes

Drop your PDF resume(s) into `backend/resume_data/`:

```bash
cp ~/Downloads/MyResume.pdf backend/resume_data/
cp ~/Downloads/MyResume_v2.pdf backend/resume_data/
```

### 3. Start the Backend

```bash
cd backend
source venv/bin/activate
python main.py
```

First run downloads models (~1GB). Server starts at `http://localhost:8000`.

### 4. Install the Chrome Extension

1. Open `chrome://extensions/`
2. Enable **Developer mode**
3. Click **Load unpacked** → select the `chrome-extension/` folder
4. Pin the extension to your toolbar

### 5. Analyze a Job

1. Open any job posting (LinkedIn, Indeed, etc.)
2. Click the ResuMatch AI extension icon
3. Hit **Analyze This Job Posting**
4. Get your verdict, scores, and tailoring suggestions

---

## How It Works

```
LinkedIn/Indeed/Glassdoor
        │
        ▼
┌─ Chrome Extension ──────────────┐
│ Smart JD extraction             │
│ (site-specific parsers)         │
└────────────┬────────────────────┘
             │ POST /analyze
             ▼
┌─ FastAPI Backend ───────────────┐
│                                 │
│  Input Guardrails               │
│       ↓                         │
│  JD Boilerplate Cleaning        │
│       ↓                         │
│  ┌─ Per Resume ──────────────┐  │
│  │ ATS Scoring (6 signals)   │  │
│  │ FAISS Retrieval + ACL     │  │
│  │ LLM Analysis (flan-t5)    │  │
│  │ Gap Summary               │  │
│  │ Tailoring Suggestions     │  │
│  └───────────────────────────┘  │
│       ↓                         │
│  Governance Evaluation          │
│  Output Sanitization            │
│  Audit Logging                  │
│       ↓                         │
│  JSON Response                  │
└─────────────────────────────────┘
```

---

## Chrome Extension

### Supported Job Boards

| Platform | Extraction Method |
|----------|------------------|
| LinkedIn | "About the job" section parser + CSS selectors |
| Indeed | `#jobDescriptionText` container |
| Glassdoor | `[class*="jobDescription"]` |
| Naukri | `.job-desc` / `.dang-inner-html` |
| Lever | `[class*="posting-"]` |
| Greenhouse | `#content` |
| Workday | `[data-automation-id="jobPostingDescription"]` |
| Any other | Generic `article` / `main` / `[role="main"]` fallback |

### Extension Settings

Right-click the extension → **Options** to configure the backend API URL (default: `http://localhost:8000`).

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/analyze` | Analyze a JD against all resumes |
| `POST` | `/upload-resume` | Upload a resume file (.pdf/.txt) |
| `GET` | `/health` | Health check + resume count |
| `GET` | `/dashboard` | Full KPI dashboard |
| `GET` | `/metrics` | Pipeline performance metrics |
| `GET` | `/audit` | Recent audit log entries |
| `GET` | `/governance/policy` | View governance policy |
| `PATCH` | `/governance/policy` | Update governance thresholds |
| `POST` | `/feedback` | Submit user feedback |
| `GET` | `/feedback/stats` | Feedback accuracy stats |

### Example

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"job_description": "Senior Python developer with AWS and React experience..."}'
```

---

## Architecture

```
resumatch-ai/
├── backend/
│   ├── main.py                     # Entry point
│   ├── config.py                   # Configuration
│   ├── ats_scorer.py               # 2026 ATS scoring engine
│   ├── presentation/               # Layer 1: API
│   │   ├── routes.py               # FastAPI endpoints
│   │   └── schemas.py              # Pydantic models
│   ├── services/                   # Layer 2: Business Logic
│   │   ├── analysis_service.py     # Pipeline orchestrator
│   │   ├── jd_cleaner.py           # JD boilerplate removal
│   │   └── llm_service.py          # LLM inference + gap/tailoring
│   ├── knowledge/                  # Layer A: Knowledge
│   │   ├── ingestion.py            # Document ingestion + chunking
│   │   ├── pii_redactor.py         # PII detection & redaction
│   │   └── access_control.py       # RBAC tags
│   ├── retrieval/                  # Layer B: Retrieval
│   │   ├── vector_store.py         # FAISS + namespace isolation
│   │   ├── query_engine.py         # Top-k + ACL + domain filters
│   │   └── query_sanitizer.py      # Query input sanitization
│   ├── validation/                 # Layer C: Validation
│   │   ├── guardrails.py           # PII + policy enforcement
│   │   ├── confidence.py           # Confidence scoring + fallback
│   │   ├── output_sanitizer.py     # Output cleaning
│   │   ├── governance.py           # Policy rules + approval gates
│   │   └── audit_logger.py         # Audit logging + anomaly detection
│   ├── observability/              # Cross-cutting
│   │   ├── metrics.py              # Latency, precision tracking
│   │   ├── success_metrics.py      # KPI dashboard
│   │   └── feedback.py             # Feedback loop
│   └── data/                       # Data Access
│       ├── model_repository.py     # HuggingFace model loading
│       └── resume_repository.py    # Resume file I/O + PDF extraction
│
└── chrome-extension/
    ├── manifest.json               # Chrome MV3 manifest
    ├── popup.html / popup.js       # Extension popup + drawer UI
    ├── styles.css                  # Premium glassmorphism UI
    ├── options.html / options.js   # Settings page
    └── icon48.png / icon128.png    # Extension icons
```

---

## Models Used

| Model | Purpose | Size | License |
|-------|---------|------|---------|
| `sentence-transformers/all-MiniLM-L6-v2` | Embeddings | ~90MB | Apache 2.0 |
| `google/flan-t5-base` | LLM (text generation) | ~950MB | Apache 2.0 |

Both models run locally on CPU. No GPU required. No API keys needed.

### Upgrading Models

Edit `backend/config.py`:

```python
# Better quality (needs ~4GB RAM)
LLM_MODEL = "google/flan-t5-large"

# Even better (needs ~8GB RAM)
LLM_MODEL = "google/flan-t5-xl"
```

---

## Free Hosting Options

Since this runs HuggingFace models locally, you need a host with enough RAM and CPU. Here are the best free options:

| Platform | Free Tier | RAM | Best For |
|----------|-----------|-----|----------|
| **[Hugging Face Spaces](https://huggingface.co/spaces)** | Free (CPU) | 16GB | Best option — native HF model support, Docker/Gradio/FastAPI, auto-sleeps when idle |
| **[Render](https://render.com)** | Free web service | 512MB (too low for flan-t5-base) | Only works with flan-t5-small or API-based LLMs |
| **[Railway](https://railway.app)** | $5 free credit/month | 8GB max | Good for flan-t5-base, auto-deploy from GitHub |
| **[Google Colab](https://colab.research.google.com)** | Free GPU | 12GB | Great for testing, not for always-on hosting |
| **[Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/)** | Always free | 24GB ARM VM | Best for always-on — 4 ARM cores, 24GB RAM, free forever |
| **[Fly.io](https://fly.io)** | 3 shared VMs free | 256MB each | Too small for LLM, but works for embedding-only mode |

### Recommended: Hugging Face Spaces (Docker)

The best free option for this stack. Create a `Dockerfile` in the repo root:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend/ .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 7860
CMD ["python", "main.py"]
```

Update `config.py` to use port 7860 (HF Spaces default), push to HF, and your API is live.

### Recommended: Oracle Cloud (Always-On)

If you want 24/7 uptime for free:
1. Sign up for Oracle Cloud Free Tier
2. Create an ARM-based VM (Ampere A1 — 4 cores, 24GB RAM, always free)
3. SSH in, clone the repo, install Python, run `python main.py`
4. The VM never sleeps and has enough RAM for flan-t5-large

---

## Publishing to Chrome Web Store

### Prerequisites
1. [Chrome Developer account](https://chrome.google.com/webstore/devconsole) ($5 one-time fee)
2. Screenshots of the extension in action (popup + drawer)
3. A 440x280 promo tile image
4. Privacy policy (since the extension reads page content)

### Store Listing SEO

**Title:** ResuMatch AI — ATS Resume Analyzer for Job Seekers

**Short description (132 chars max):**
AI-powered resume analyzer. Get ATS scores, skill gap analysis, and tailoring suggestions for any job posting. 100% local & private.

**Detailed description:**
```
ResuMatch AI analyzes job descriptions on LinkedIn, Indeed, Glassdoor, Naukri, and 
other job boards — and tells you if your resume is a match.

🎯 WHAT IT DOES
• Compares your resume(s) against any job posting with one click
• Gives you an ATS compatibility score using 2026 scoring algorithms
• Shows which resume to use when you have multiple versions
• Explains WHY your resume doesn't fit with specific gap analysis
• Provides actionable suggestions to tailor your resume

📊 SCORING ENGINE
• Keyword matching with synonym expansion (GenAI ↔ Generative AI)
• Skill cluster analysis (groups related skills like real ATS systems)
• Contextual placement scoring (Summary keywords weighted 3x)
• Quantified achievement detection ($, %, numbers)
• Semantic similarity using AI embeddings

🔒 100% PRIVATE
• All processing happens on YOUR machine
• No data is sent to any cloud service
• No API keys required
• Your resume never leaves your laptop

💼 SUPPORTED JOB BOARDS
LinkedIn, Indeed, Glassdoor, Naukri, Lever, Greenhouse, Workday, and any other site

⚡ HOW TO USE
1. Install the extension
2. Start the local backend (one command)
3. Open any job posting
4. Click the extension icon
5. Get your analysis in seconds
```

**Category:** Productivity

**Tags/Keywords:** resume analyzer, ATS score, job search, resume checker, LinkedIn, 
career tools, resume optimization, job matching, AI resume, applicant tracking system

---

## Privacy Policy

ResuMatch AI processes all data locally on the user's machine. The extension:
- Reads the text content of the active tab (job posting) when the user clicks "Analyze"
- Sends the extracted text to a locally-running backend server (localhost)
- Does not transmit any data to external servers
- Does not collect, store, or share any personal information
- Does not use cookies or tracking

---

## Contributing

PRs welcome. Please open an issue first to discuss what you'd like to change.

## License

MIT

---

<p align="center">
  Built with ❤️ using HuggingFace Transformers, FAISS, LangChain, and FastAPI
</p>
