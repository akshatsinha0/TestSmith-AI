from __future__ import annotations
import json
from typing import Tuple
from bs4 import BeautifulSoup

try:
    import fitz  # pymupdf
except Exception:
    fitz = None


def parse_any(content: bytes, filename: str) -> Tuple[str, dict]:
    name = (filename or "").lower()
    meta = {"source_document": filename}

    if name.endswith((".md", ".txt")):
        try:
            return content.decode("utf-8", errors="ignore"), {**meta, "type": "text"}
        except Exception:
            return content.decode("latin-1", errors="ignore"), {**meta, "type": "text"}

    if name.endswith(".json"):
        try:
            data = json.loads(content.decode("utf-8", errors="ignore"))
            # pretty-print to keep structure
            return json.dumps(data, indent=2), {**meta, "type": "json"}
        except Exception:
            return content.decode("utf-8", errors="ignore"), {**meta, "type": "json"}

    if name.endswith(".pdf") and fitz is not None:
        text = ""
        try:
            with fitz.open(stream=content, filetype="pdf") as doc:
                for page in doc:
                    text += page.get_text()
            return text, {**meta, "type": "pdf"}
        except Exception:
            pass

    if name.endswith((".html", ".htm")):
        text = _html_to_text(content.decode("utf-8", errors="ignore"))
        return text, {**meta, "type": "html"}

    # Fallback: treat as utf-8 text
    return content.decode("utf-8", errors="ignore"), {**meta, "type": "text"}


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    # Keep the HTML for selectors as well as extracted text for semantics
    # Return the full HTML string so LLM sees structure
    return str(soup)
