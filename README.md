# TestSmith-AI

An autonomous QA agent that builds a documentation-grounded "testing brain" to generate test cases and Python Selenium scripts for a target checkout page.

- Backend: FastAPI
- UI: Streamlit
- Vector store: lightweight lexical store (JSON under `data/kb_store.json`)
- Retrieval: simple token-overlap RAG (no heavy ML dependencies)
- LLM: Groq API (free-tier) — Llama 3.1 8B Instant by default

## 1) Prerequisites
- Python 3.10+ (3.11 recommended)
- Google Chrome (for running generated Selenium scripts)
- Git

Optional:
- ChromeDriver on PATH (or use webdriver-manager manually if desired)

## 2) Setup
```bash
# from repo root
python -m venv .venv
# Windows PowerShell
.\\.venv\\Scripts\\Activate.ps1
# or cmd.exe: .venv\\Scripts\\activate.bat

pip install -r requirements.txt
```

### Environment variables (free keys)
Set these before running the services:
- GROQ_API_KEY: required (free). Create at: https://console.groq.com/keys
- GROQ_MODEL: optional (default: `llama-3.1-8b-instant`)
- EMBED_MODEL: (optional; currently not used since retrieval is lexical)

Examples (PowerShell):
```powershell
$env:GROQ_API_KEY = "{{GROQ_API_KEY}}"  # replace with your key
$env:GROQ_MODEL = "llama-3.1-8b-instant"
```

### Note on vector DB vs lexical store
Originally the project used a true vector database (Chroma + SentenceTransformers embeddings) for semantic retrieval.
On Python 3.13 and Windows this caused dependency conflicts and build issues:
- `chromadb` required `numpy<2.0.0`, while other libraries (e.g. Streamlit) required `numpy>=2`.
- Some ML packages had no prebuilt wheels for Python 3.13, triggering Visual Studio build tool errors.

To keep the assignment easy to run and focus on the agent/RAG behaviour, the implementation now uses a
lightweight lexical store backed by `data/kb_store.json`:
- Documents are chunked and stored with metadata (`source_document`).
- Retrieval ranks chunks by token overlap with the user query.
- Retrieved chunks are passed into the LLM as context (RAG), and are surfaced in the UI as grounding snippets.

The design is intentionally layered: `backend.vector_store` can later be swapped for Chroma/FAISS/Qdrant without
changing the rest of the pipeline if you want a full vector DB in a more permissive environment.

## 3) Run
In two terminals (both with venv activated):

Terminal A – FastAPI:
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal B – Streamlit UI:
```bash
streamlit run ui/app.py
```

Open the UI at the URL Streamlit prints (typically http://localhost:8501).

The API serves the checkout page at http://127.0.0.1:8000/checkout (uses your uploaded/pasted HTML if available; falls back to assets/checkout.html). Generated Selenium scripts will open this URL.

Live demo (Streamlit Cloud): https://testsmith-ai.streamlit.app/

## 4) Usage
1. Build Knowledge Base
   - Upload 3–5 support documents (e.g., `docs/product_specs.md`, `docs/ui_ux_guide.txt`, `docs/api_endpoints.json`).
   - Upload or paste the `checkout.html` contents. A sample page is under `assets/checkout.html`.
   - Click “Build Knowledge Base”. The system chunks, embeds, and stores the documents with metadata.

2. Generate Test Cases (RAG)
   - Enter an instruction (e.g., "Generate all positive and negative test cases for the discount code feature.").
   - Click “Generate Test Cases”. The agent retrieves relevant context and asks the LLM to produce JSON test cases grounded in your docs.

3. Generate Selenium Script
   - Select one of the structured test cases.
   - Click “Generate Selenium Script”. The agent provides the full `checkout.html` and relevant context to the LLM to produce a runnable Python Selenium script.

Notes:
- All reasoning is grounded strictly in the uploaded documents. The prompts explicitly forbid invented features.
- The latest provided `checkout.html` is cached in `data/runtime_checkout.html` for script generation.

## 5) Project Assets
- `assets/checkout.html` – example single-page checkout with:
  - 3 products and “Add to Cart”
  - Cart summary with quantity inputs and pricing
  - Discount code input (`SAVE15` → 15% off)
  - User Details form (Name, Email, Address) with inline validation errors in red
  - Shipping methods (Standard free, Express $10)
  - Payment methods (Credit Card, PayPal)
  - “Pay Now” shows “Payment Successful!” when form is valid
- `docs/product_specs.md` – business rules
- `docs/ui_ux_guide.txt` – visual/UX rules
- `docs/api_endpoints.json` – mock API shapes

## 6) Demo Flow (what to show in your recording)
- Upload documents + `checkout.html`
- Click “Build Knowledge Base” → success message
- Ask for test cases (e.g., discount code scenarios) → shows structured JSON
- Select a test case and generate Selenium code → copy into a local file and run with Python

## 7) Running Generated Selenium Scripts
Save the generated code as `test_case.py` and run:
```bash
python test_case.py
```
Ensure Chrome is installed, and if needed, set up ChromeDriver on PATH or modify the script to use a webdriver manager.

## 8) Troubleshooting
- Missing GROQ_API_KEY → set it and restart both services.
- Embedding model download slow on first run → it’s cached afterwards under `.cache/`.
- Knowledge base persistence → `data/kb_store.json` will be created automatically.

## 9) License
MIT

## 10) Deploying to Streamlit Cloud
You can deploy this repo directly to Streamlit Cloud.

### Option A (single app on Streamlit Cloud — recommended for demo)
Streamlit Cloud runs a single process per app; the UI starts the FastAPI backend inside the same process on port 8000.

1. App file: choose `ui/app.py`.
2. Secrets: open App → Settings → Secrets and paste valid TOML:

```
GROQ_API_KEY = "<your_groq_key>"
GROQ_MODEL  = "llama-3.1-8b-instant"
api_base    = "http://127.0.0.1:8000"
CHECKOUT_URL = "http://127.0.0.1:8000/checkout"
```

3. Deploy. Use the sidebar Health Check first; it should return `{ "status": "ok" }`.

Notes:
- Storage is ephemeral; `data/kb_store.json` will be recreated on restarts.
- Generated Selenium scripts will reference `CHECKOUT_URL`; with Option A they target the in-app `/checkout`.

### Option B (two services: public FastAPI + Streamlit Cloud UI)
If you want scripts to run against a publicly reachable page, deploy the FastAPI to a host (Render, Railway, Fly.io, EC2, etc.):

- Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Ensure your platform exposes the port and sets `PORT`.
- After deployment, set Streamlit Cloud Secrets:

```
GROQ_API_KEY = "<your_groq_key>"
GROQ_MODEL  = "llama-3.1-8b-instant"
api_base    = "https://<your-fastapi-host>"
CHECKOUT_URL = "https://<your-fastapi-host>/checkout"
```

That gives you a public `/checkout` URL and a public API base; Streamlit UI will call the public API, and generated Selenium scripts will open the public checkout page.
