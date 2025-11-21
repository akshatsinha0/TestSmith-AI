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
