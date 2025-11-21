import os
import io
import json
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.responses import FileResponse
from dotenv import load_dotenv

from backend.parser import parse_any
from backend.rag import build_kb, retrieve_context, persist_runtime_html, load_runtime_html, RUNTIME_HTML_PATH
from backend.llm import LLMClient

# Load environment variables from .env if present
load_dotenv()

app = FastAPI(title="TestSmith-AI API", version="0.1.0")
# Serve static assets (sample checkout.html)
app.mount("/static", StaticFiles(directory="assets"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class BuildKBResponse(BaseModel):
    chunks_indexed: int
    sources: List[str]

class GenerateTestCasesRequest(BaseModel):
    query: str


class TestCase(BaseModel):
    test_id: str
    feature: str
    scenario: str
    steps: List[str]
    expected_result: str
    grounded_in: List[str]


class ContextSnippet(BaseModel):
    source_document: str
    preview: str


class GenerateTestCasesResponse(BaseModel):
    test_cases: List[TestCase]
    raw: str
    context_preview: List[ContextSnippet]

class GenerateScriptRequest(BaseModel):
    test_case: TestCase

class GenerateScriptResponse(BaseModel):
    code: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/checkout")
def serve_checkout():
    # Serve uploaded runtime checkout if present, else fallback to bundled sample
    path = RUNTIME_HTML_PATH if os.path.exists(RUNTIME_HTML_PATH) else os.path.join("assets", "checkout.html")
    return FileResponse(path, media_type="text/html")


@app.post("/build_kb", response_model=BuildKBResponse)
async def build_kb_endpoint(
    support_docs: List[UploadFile] = File(default=[]),
    checkout_html: Optional[UploadFile] = File(default=None),
    checkout_html_text: Optional[str] = Form(default=None),
):
    texts = []
    sources = []

    # Support documents
    for uf in support_docs:
        content = await uf.read()
        text, meta = parse_any(content, filename=uf.filename)
        texts.append({"text": text, "metadata": meta})
        sources.append(meta.get("source_document", uf.filename))

    # checkout.html as file or pasted text
    html_text = None
    if checkout_html is not None:
        b = await checkout_html.read()
        html_text, meta = parse_any(b, filename=checkout_html.filename)
        texts.append({"text": html_text, "metadata": meta})
        sources.append(meta.get("source_document", checkout_html.filename))
    elif checkout_html_text:
        html_text = checkout_html_text
        texts.append({"text": checkout_html_text, "metadata": {"source_document": "checkout.html", "type": "html"}})
        sources.append("checkout.html")

    # Persist runtime HTML for later Selenium generation
    if html_text:
        persist_runtime_html(html_text)

    chunks_indexed = build_kb(texts)
    return BuildKBResponse(chunks_indexed=chunks_indexed, sources=sorted(list(set(sources))))


@app.post("/generate_test_cases", response_model=GenerateTestCasesResponse)
async def generate_test_cases(req: GenerateTestCasesRequest):
    query = req.query
    retrieved = retrieve_context(query=query, k=8)

    llm = LLMClient()
    raw = llm.generate_test_cases(query=query, context_docs=retrieved)

    # Prepare lightweight context previews for UI grounding panel
    context_preview: List[ContextSnippet] = []
    for d in retrieved:
        meta = (d.get("metadata") or {})
        src = meta.get("source_document") or "unknown"
        text = (d.get("text") or "").strip().replace("\n", " ")
        if not text:
            continue
        if len(text) > 260:
            text = text[:260] + "..."
        context_preview.append(ContextSnippet(source_document=src, preview=text))

    # Try to parse into structured items
    test_cases: List[TestCase] = []

    def _extract_json_array(text: str) -> str:
        """Best-effort extraction of a JSON array from an LLM response.

        Strips code fences and any leading/trailing commentary, then
        returns the substring from the first '[' to the last ']'.
        """
        if not text:
            return ""
        cleaned = text.strip()
        # Remove ```json or ``` fences if present
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            # After stripping backticks, try to find first '['
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return cleaned
        return cleaned[start : end + 1]

    try:
        payload = _extract_json_array(raw)
        data = json.loads(payload)
        for i, item in enumerate(data):
            tc = TestCase(
                test_id=item.get("Test_ID") or item.get("id") or f"TC-{i+1:03d}",
                feature=item.get("Feature") or item.get("feature") or "",
                scenario=item.get("Test_Scenario") or item.get("scenario") or "",
                steps=item.get("Steps") or item.get("steps") or [],
                expected_result=item.get("Expected_Result") or item.get("expected") or "",
                grounded_in=item.get("Grounded_In") or item.get("grounded_in") or [],
            )
            # Normalize grounded_in to list
            if isinstance(tc.grounded_in, str):
                tc.grounded_in = [tc.grounded_in]
            test_cases.append(tc)
    except Exception:
        # If not JSON, return raw and empty list
        pass

    return GenerateTestCasesResponse(test_cases=test_cases, raw=raw, context_preview=context_preview)


@app.post("/generate_selenium_script", response_model=GenerateScriptResponse)
async def generate_selenium_script(req: GenerateScriptRequest):
    html = load_runtime_html()  # full HTML from last run
    if not html:
        # Try fetch from KB as fallback
        html = ""
        try:
            # retrieve with a query hint
            html_ctx = retrieve_context("checkout html structure", k=1)
            if html_ctx:
                html = html_ctx[0]["text"]
        except Exception:
            pass

    retrieved = retrieve_context(query=f"selectors and rules for {req.test_case.feature}", k=6)

    llm = LLMClient()
    code = llm.generate_selenium_script(test_case=req.test_case.model_dump(), html=html, context_docs=retrieved)

    return GenerateScriptResponse(code=code)
