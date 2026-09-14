# Streamlit UI for VERA `/ask` Endpoint
import os
from pathlib import Path

import streamlit as st
import requests
from dotenv import load_dotenv

load_dotenv()  # picks up VERA_API_KEY from the local .env, same as main.py

# run.sh records its actual host:port here on every start, so the default
# below tracks whichever port is currently active instead of a hardcoded one.
_LOCAL_URL_FILE = Path(__file__).resolve().parent / ".vera-local-url"


def _default_api_base_url() -> str:
    try:
        return _LOCAL_URL_FILE.read_text().strip() or "http://127.0.0.1:8001"
    except FileNotFoundError:
        return "http://127.0.0.1:8001"


# Configuration
API_BASE_URL = _default_api_base_url()
if "API_BASE_URL" in st.session_state:
    API_BASE_URL = st.session_state["API_BASE_URL"]

API_KEY = os.getenv("VERA_API_KEY", "")
if "API_KEY" in st.session_state:
    API_KEY = st.session_state["API_KEY"]

st.title("VERA - Question Answering Service")

# Sidebar for settings
st.sidebar.header("Settings")
st.sidebar.subheader("API Configuration")
api_url = st.sidebar.text_input(
    "API Base URL",
    value=API_BASE_URL,
    help="Your Render URL for production: https://your-service.onrender.com"
)
api_key = st.sidebar.text_input(
    "API Key (X-API-Key)",
    value=API_KEY,
    type="password",
    help="Defaults to VERA_API_KEY from .env; override to point at a deployment with a different key.",
)


def save_settings():
    st.session_state["API_BASE_URL"] = api_url
    st.session_state["API_KEY"] = api_key


st.sidebar.button("Save Settings", on_click=save_settings)

# Force bad demo toggle
st.sidebar.subheader("Guardrail Demo")
force_bad = st.sidebar.checkbox("Show guardrail demo (force_bad)", value=False)

# Question input
st.subheader("Ask a Question")
question = st.text_input(
    "Enter your research question:",
    placeholder="What is VERA?",
    help="Ask anything. The service will return an answer with token usage and cost."
)

# Ask button
if st.button("Ask", type="primary"):
    if not question:
        st.warning("⚠️ Please enter a question.")
    elif not api_key:
        st.warning("⚠️ No API key set. Add VERA_API_KEY to .env or enter one in the sidebar.")
    else:
        with st.spinner("🤔 Thinking..."):
            try:
                # Make API request
                response = requests.post(
                    f"{API_BASE_URL}/ask",
                    json={"question": question, "mode": "force_bad" if force_bad else "normal"},
                    headers={"Content-Type": "application/json", "X-API-Key": api_key},
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()

                    # Display answer
                    st.markdown("### ✅ Answer")
                    st.success(data["answer"])

                    # Display metrics
                    st.markdown("### 💰 Metrics")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Tokens Used", f"{data['tokens_used']:,}")
                    with col2:
                        st.metric("Cost", f"${data['cost_usd']:.6f}")

                    # Display raw JSON
                    with st.expander("📊 Full Response (JSON)"):
                        st.json(data)

                    # Next question suggestion
                    st.info("💡 Try asking about your capstone topic!")

                elif response.status_code == 500:
                    st.error(f"❌ Error: {response.json().get('detail', 'Unknown error')}")

                elif response.status_code == 401:
                    st.error("❌ API key error. Check the sidebar API key matches the server's VERA_API_KEY.")

                elif response.status_code == 402:
                    st.error("❌ Insufficient quota. Add credits to your OpenAI account.")

                elif response.status_code == 429:
                    st.error("❌ Rate limit exceeded. Wait a few seconds and try again.")

                else:
                    st.error(f"❌ Error {response.status_code}: {response.text}")

            except requests.exceptions.RequestException as e:
                st.error(f"❌ Request failed: {e}")
                st.info("💡 Make sure the API is running: `./run.sh`")
else:
    st.info("👆 Click 'Ask' to get started.")
