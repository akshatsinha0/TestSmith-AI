import io
import json
import requests
import streamlit as st

try:
    API_BASE = st.secrets.get("api_base", "http://127.0.0.1:8000")
except FileNotFoundError:
    API_BASE = "http://127.0.0.1:8000"

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

if "test_cases" not in st.session_state:
    st.session_state.test_cases = []

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
            r = requests.post(f"{API_BASE}/generate_test_cases", json={"query": query}, timeout=120)
            r.raise_for_status()
            out = r.json()
            st.session_state.test_cases = out.get("test_cases", [])
            st.code(out.get("raw", ""), language="json")
            if st.session_state.test_cases:
                st.success(f"Parsed {len(st.session_state.test_cases)} structured test cases.")
        except Exception as e:
            st.error(str(e))

    if st.session_state.test_cases:
        st.markdown("### Select a test case")
        options = [f"{tc['test_id']} - {tc['feature']}" for tc in st.session_state.test_cases]
        idx = st.selectbox("Test case", options=list(range(len(options))), format_func=lambda i: options[i])
        st.session_state.selected_tc = st.session_state.test_cases[idx]
        st.json(st.session_state.selected_tc)

with sel_tab:
    st.subheader("Generate Selenium Script")
    disabled = not bool(st.session_state.get("test_cases"))
    if st.button("Generate Selenium Script", type="primary", disabled=disabled):
        try:
            tc = st.session_state.get("selected_tc") or (st.session_state.test_cases[0] if st.session_state.test_cases else None)
            if not tc:
                st.warning("No test case selected.")
            else:
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
