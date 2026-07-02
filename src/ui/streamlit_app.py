"""Streamlit dashboard for BLITZ OS. Talks to the FastAPI backend."""

import os
from datetime import datetime

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="BLITZ Intelligence OS", page_icon="🧠", layout="wide")

st.markdown(
    """
    <style>
    .main-header { font-size: 2.5rem; font-weight: bold; color: #00B4D8; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "history" not in st.session_state:
    st.session_state.history = []

st.markdown('<div class="main-header">🧠 BLITZ Intelligence OS</div>', unsafe_allow_html=True)
st.markdown("Strategic Research & Decision Intelligence Platform")

with st.sidebar:
    st.markdown("### ⚙️ Controls")
    max_iterations = st.slider("Max Research Iterations", 1, 5, 3)

    st.markdown("### 📊 System Stats")
    try:
        stats = requests.get(f"{API_URL}/stats", timeout=5).json()
        st.metric("Total Research Entries", stats.get("total_entries", 0))
        st.metric("Total Cost", f"${stats.get('total_cost', 0):.2f}")
        health = requests.get(f"{API_URL}/health", timeout=5).json()
        if not health.get("llm_configured"):
            st.info("No LLM key configured — running in heuristic mode.")
        if not health.get("web_search_configured"):
            st.info("No SERPAPI key — web evidence is mocked.")
    except requests.RequestException:
        st.warning("API not running. Start with: `uvicorn src.api.routes:app --reload`")

    st.markdown("### 🔎 Knowledge Archive")
    archive_query = st.text_input("Search past research")
    if archive_query:
        try:
            found = requests.get(f"{API_URL}/search/{archive_query}", timeout=10).json()
            st.caption(f"{found['total']} match(es)")
            for rec in found["results"][:5]:
                st.markdown(f"- {rec['query'][:60]} ({rec['timestamp'][:10]})")
        except requests.RequestException:
            st.warning("Archive search failed — is the API running?")

st.markdown("### 🔍 Ask Your Research Question")
query = st.text_input(
    "What do you want to research?",
    placeholder="Example: What are the top 3 trends in AI-powered legal tech for 2025?",
)

if st.button("🔍 Research", type="primary") and query:
    with st.spinner("🧠 Thinking... researching, validating, and analyzing..."):
        try:
            response = requests.post(
                f"{API_URL}/research",
                json={"query": query, "max_iterations": max_iterations},
                timeout=300,
            )
            response.raise_for_status()
            data = response.json()

            if data["success"]:
                st.session_state.history.append(
                    {
                        "query": query,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "confidence": data.get("confidence") or 0,
                        "sources": data.get("sources") or [],
                        "response": data.get("response") or "",
                    }
                )

                st.markdown("---")
                st.markdown("## 📊 Research Results")

                confidence = data.get("confidence") or 0
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Confidence", f"{confidence * 100:.0f}%")
                col2.metric("Sources", len(data.get("sources") or []))
                col3.metric("Gaps", len(data.get("gaps") or []))
                col4.metric("Cost", f"${data.get('cost') or 0:.4f}")

                st.markdown("### 📝 Detailed Analysis")
                st.markdown(data.get("response") or "_No response generated._")

                if data.get("gaps"):
                    st.markdown("### 🔍 Gaps Identified")
                    for gap in data["gaps"]:
                        st.warning(f"• {gap}")

                if data.get("follow_up"):
                    st.markdown("### ➡️ Suggested Follow-up")
                    st.info(data["follow_up"])
            else:
                st.error(f"Research failed: {data.get('error', 'Unknown error')}")
        except requests.ConnectionError:
            st.error("⚠️ Cannot connect to the BLITZ API. Start the backend first.")
        except Exception as e:
            st.error(f"An error occurred: {e}")

if st.session_state.history:
    st.markdown("---")
    st.markdown("## 📜 Research History (this session)")
    for entry in reversed(st.session_state.history[-5:]):
        with st.expander(f"{entry['timestamp']} — {entry['query'][:60]}"):
            st.markdown(f"**Confidence:** {entry['confidence'] * 100:.0f}%")
            st.markdown(f"**Sources:** {', '.join(entry['sources']) or 'none'}")
            st.markdown("---")
            st.markdown(entry["response"])
