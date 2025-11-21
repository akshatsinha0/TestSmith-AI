import io
import json
from collections import Counter
import requests
import streamlit as st

st.set_page_config(page_title="TestSmith-AI", layout="wide")

# Global typography: Elms Sans (Google Font)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Elms+Sans:ital,wght@0,100..900;1,100..900&display=swap');
    html, body, [class*="css"], .stMarkdown, .stTextInput, .stButton, .stSelectbox {
        font-family: "Elms Sans", sans-serif;
        font-optical-sizing: auto;
        font-weight: 400;
        font-style: normal;
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: "Elms Sans", sans-serif;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("TestSmith-AI: Autonomous QA Agent")

# Resolve backend API base URL (optional override via Streamlit secrets)
try:
    API_BASE = st.secrets.get("api_base", "http://127.0.0.1:8000")
except FileNotFoundError:
    API_BASE = "http://127.0.0.1:8000"

if "test_cases" not in st.session_state:
    st.session_state.test_cases = []
if "context_preview" not in st.session_state:
    st.session_state.context_preview = []

with st.sidebar:
    st.markdown("## Backend")
    st.write(f"API: {API_BASE}")
    if st.button("Health Check"):
        try:
            r = requests.get(f"{API_BASE}/health", timeout=10)
            st.success(r.json())
        except Exception as e:
            st.error(str(e))

# Tabs
kb_tab, tc_tab, sel_tab = st.tabs(["1) Build Knowledge Base", "2) Generate Test Cases", "3) Generate Selenium Script"]) 

with kb_tab:
    st.subheader("Upload support documents and checkout.html")
    support_docs = st.file_uploader("Support docs (MD, TXT, JSON, PDF)", type=["md", "txt", "json", "pdf"], accept_multiple_files=True)
    html_col1, html_col2 = st.columns(2)
    with html_col1:
        checkout_html = st.file_uploader("checkout.html (optional)", type=["html", "htm"], accept_multiple_files=False)
    with html_col2:
        checkout_html_text = st.text_area("...or paste checkout.html", height=200)

    if st.button("Build Knowledge Base", type="primary"):
        files = []
        for doc in support_docs or []:
            files.append(("support_docs", (doc.name, doc.getvalue(), doc.type or "application/octet-stream")))
        if checkout_html is not None:
            files.append(("checkout_html", (checkout_html.name, checkout_html.getvalue(), checkout_html.type or "text/html")))
        data = {}
        if checkout_html_text and not checkout_html:
            data["checkout_html_text"] = checkout_html_text
        try:
            with st.spinner("Building knowledge base from uploaded documents..."):
                r = requests.post(f"{API_BASE}/build_kb", files=files, data=data, timeout=120)
                r.raise_for_status()
                out = r.json()
            st.success(f"Indexed {out['chunks_indexed']} chunks from sources: {', '.join(out['sources'])}")
            st.markdown("[Open checkout page (served by API)](http://127.0.0.1:8000/checkout)")
        except Exception as e:
            st.error(str(e))

with tc_tab:
    st.subheader("Generate Test Cases (RAG)")
    query = st.text_input("Instruction", value="Generate all positive and negative test cases for the discount code feature.")
    if st.button("Generate Test Cases", type="primary"):
        try:
            with st.spinner("Generating test cases with RAG agent..."):
                r = requests.post(f"{API_BASE}/generate_test_cases", json={"query": query}, timeout=120)
                r.raise_for_status()
                out = r.json()
            st.session_state.test_cases = out.get("test_cases", [])
            st.session_state.context_preview = out.get("context_preview", [])
            st.code(out.get("raw", ""), language="json")
            if st.session_state.test_cases:
                st.success(f"Parsed {len(st.session_state.test_cases)} structured test cases.")
        except Exception as e:
            st.error(str(e))

    if st.session_state.test_cases:
        # Simple summary of how many positive / negative / boundary cases we have
        type_counts = Counter()
        for tc in st.session_state.test_cases:
            scen = (tc.get("scenario") or tc.get("Test_Scenario") or "").lower()
            if scen.startswith("[positive]"):
                type_counts["Positive"] += 1
            elif scen.startswith("[negative]"):
                type_counts["Negative"] += 1
            elif scen.startswith("[boundary]"):
                type_counts["Boundary"] += 1
        c1, c2, c3 = st.columns(3)
        c1.metric("Positive tests", type_counts.get("Positive", 0))
        c2.metric("Negative tests", type_counts.get("Negative", 0))
        c3.metric("Boundary tests", type_counts.get("Boundary", 0))

        st.markdown("### Select a test case")
        options = [f"{tc['test_id']} - {tc['feature']}" for tc in st.session_state.test_cases]
        idx = st.selectbox("Test case", options=list(range(len(options))), format_func=lambda i: options[i])
        st.session_state.selected_tc = st.session_state.test_cases[idx]
        selected_tc = st.session_state.selected_tc
        st.json(selected_tc)

        # Grounding panel: show which docs/snippets back this test case
        preview_by_src = {c["source_document"]: c["preview"] for c in st.session_state.get("context_preview", [])}
        grounded = selected_tc.get("grounded_in") or []
        if grounded:
            st.markdown("#### Grounding (documentation snippets)")
            for src in grounded:
                snippet = preview_by_src.get(src)
                label = f"Source: {src}"
                with st.expander(label, expanded=False):
                    if snippet:
                        st.write(snippet)
                    else:
                        st.write("_Referenced by test case, but no snippet available from latest retrieval._")

        # Coverage summary by source document
        doc_counter = Counter()
        for tc in st.session_state.test_cases:
            for src in tc.get("grounded_in") or []:
                doc_counter[src] += 1
        if doc_counter:
            st.markdown("#### Source coverage across generated tests")
            for src, count in doc_counter.items():
                st.write(f"- {src}: {count} test(s)")

        # Download helpers
        def _format_tc_markdown(tc: dict) -> str:
            steps = tc.get("steps") or []
            lines = [
                f"### {tc.get('test_id', 'Test Case')} – {tc.get('feature', '')}",
                f"**Scenario**: {tc.get('scenario', '')}",
                "",
                "**Steps:**",
            ]
            for i, step in enumerate(steps, start=1):
                lines.append(f"{i}. {step}")
            lines.append("")
            lines.append(f"**Expected Result**: {tc.get('expected_result', '')}")
            lines.append("")
            grounded_str = ", ".join(tc.get("grounded_in") or [])
            if grounded_str:
                lines.append(f"**Grounded In**: {grounded_str}")
            return "\n".join(lines)

        st.markdown("#### Export test plan")
        md_plan = _format_tc_markdown(selected_tc)
        st.download_button(
            label="Download selected test case (Markdown)",
            data=md_plan,
            file_name=f"{selected_tc.get('test_id','test_case')}.md",
            mime="text/markdown",
        )
        st.download_button(
            label="Download full test suite (JSON)",
            data=json.dumps(st.session_state.test_cases, indent=2),
            file_name="test_suite.json",
            mime="application/json",
        )

with sel_tab:
    st.subheader("Generate Selenium Script")
    disabled = not bool(st.session_state.get("test_cases"))
    if st.button("Generate Selenium Script", type="primary", disabled=disabled):
        try:
            tc = st.session_state.get("selected_tc") or (st.session_state.test_cases[0] if st.session_state.test_cases else None)
            if not tc:
                st.warning("No test case selected.")
            else:
                with st.spinner("Generating Selenium script from selected test case..."):
                    r = requests.post(f"{API_BASE}/generate_selenium_script", json={"test_case": tc}, timeout=180)
                    r.raise_for_status()
                    code = r.json().get("code", "")
                st.session_state.generated_code = code
                st.code(code, language="python")
                if code:
                    st.download_button(
                        label="Download script",
                        data=code,
                        file_name=f"{tc.get('test_id','test_case')}.py",
                        mime="text/x-python",
                    )
        except Exception as e:
            st.error(str(e))

st.markdown("---")
st.caption("Upload docs ➜ Build KB ➜ Generate test cases ➜ Generate Selenium script. All reasoning grounded in your docs.")
