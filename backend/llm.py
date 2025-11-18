from __future__ import annotations
import os
import json
from typing import List, Dict, Any

from groq import Groq


TESTCASE_SYSTEM = (
    "You are a QA test planner. Generate ONLY JSON (a list of objects). Each object must include keys: "
    "Test_ID, Feature, Test_Scenario, Steps (array), Expected_Result, Grounded_In (array of source document names). "
    "Base all details strictly on the provided context. If a fact is not in context, do not invent it."
)

SELENIUM_SYSTEM = (
    "You are a senior QA automation engineer. Generate a complete, runnable Python Selenium script. "
    "Use WebDriverWait and robust selectors based on the provided checkout.html. "
    "Do not invent non-existent elements. Use 'By.ID' where possible, else CSS selectors. "
    "Output ONLY a single Python code block."
)


def _format_context(context_docs: List[Dict[str, Any]]) -> str:
    parts = []
    for d in context_docs:
        src = (d.get("metadata") or {}).get("source_document") or "unknown"
        parts.append(f"SOURCE: {src}\n---\n{d.get('text','')}")
    return "\n\n".join(parts)


class LLMClient:
    def __init__(self) -> None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY not set. Get a free key from https://console.groq.com/keys and set it in your env."
            )
        self.client = Groq(api_key=api_key)
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    def generate_test_cases(self, query: str, context_docs: List[Dict[str, Any]]) -> str:
        context = _format_context(context_docs)
        user = (
            "Context (documentation excerpts):\n" + context +
            "\n\nInstruction: Based on the above context, "
            "generate positive and negative test cases for: '" + query + "'. "
            "Return a JSON array only."
        )
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": TESTCASE_SYSTEM}, {"role": "user", "content": user}],
            temperature=0.2,
            max_tokens=1800,
        )
        return resp.choices[0].message.content.strip()

    def generate_selenium_script(self, test_case: Dict[str, Any], html: str, context_docs: List[Dict[str, Any]]) -> str:
        context = _format_context(context_docs)
        test_url = os.getenv("CHECKOUT_URL", "http://127.0.0.1:8000/checkout")
        user = (
            f"checkout.html (full or partial):\n{html}\n\n" +
            f"Documentation context:\n{context}\n\n" +
            "Selected Test Case (JSON):\n" + json.dumps(test_case, indent=2) +
            "\n\nInstruction: Generate a full Python Selenium script implementing this test case on the given checkout page. "
            f"Assume the page is served locally at: {test_url} (open it with driver.get).\n" 
            "Strict requirements:\n"
            "- Use webdriver_manager for Chrome: from webdriver_manager.chrome import ChromeDriverManager;\n"
            "  from selenium.webdriver.chrome.service import Service; service = Service(ChromeDriverManager().install())\n"
            "- Initialize driver with service; use WebDriverWait; prefer By.ID then CSS selectors matching the HTML.\n"
            "- Add lightweight assertions for expected outcomes and inline comments.\n"
            "Output ONLY a single Python code block, no extra text."
        )
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": SELENIUM_SYSTEM}, {"role": "user", "content": user}],
            temperature=0.2,
            max_tokens=2200,
        )
        return resp.choices[0].message.content.strip()
