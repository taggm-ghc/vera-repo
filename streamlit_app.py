# Streamlit UI for VERA `/ask` Endpoint
import os
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv

from vera.public_mode import is_public_mode, post_ask, upstream_base_url
from vera.ui_safety import safe_markdown

load_dotenv()  # picks up VERA_API_KEY from the local .env, same as main.py

# run.sh records its actual host:port here on every start (dev-mode default URL only).
_LOCAL_URL_FILE = Path(__file__).resolve().parent / ".vera-local-url"

# Mode is read once per script run from VERA_PUBLIC_MODE; unset means PUBLIC (safe default).
PUBLIC = is_public_mode()

# Server-side only. Never passed as a widget value, never stored in st.session_state, never
# rendered. In public mode this is the only key the UI uses; in dev mode it is NOT used at all
# (a dev types their own key), so a user-editable URL can never receive the server key.
_SERVER_KEY = os.getenv("VERA_API_KEY", "")

st.title("VERA - Question Answering Service")

if PUBLIC:
    api_base_url = upstream_base_url(local_url_file=None)
    api_key = _SERVER_KEY
else:
    st.sidebar.header("Settings (local/dev mode)")
    api_base_url = st.sidebar.text_input(
        "API Base URL", value=upstream_base_url(local_url_file=_LOCAL_URL_FILE),
        help="Local/dev only. The key typed below is sent to this URL.")
    api_key = st.sidebar.text_input(
        "API Key (X-API-Key)", value="", type="password",
        help="Blank by default. Type the key for the API above; it is never pre-filled.")

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
        st.warning("The service is not configured." if PUBLIC else "No API key set. Type one in the sidebar.")
    else:
        with st.spinner("🤔 Thinking..."):
            try:
                # Make API request
                response = post_ask(api_base_url, question, "force_bad" if force_bad else "normal", api_key)

                if response.status_code == 200:
                    data = response.json()

                    # Display answer
                    st.markdown("### ✅ Answer")
                    st.success(safe_markdown(data["answer"]))

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

                elif response.status_code == 429:
                    st.error("Rate limit reached. Please try again later.")

                elif PUBLIC:
                    st.error("The service could not answer this request. Please try again later.")

                elif response.status_code == 401:
                    st.error("API key error. Check the key typed in the sidebar matches the server's VERA_API_KEY.")

                else:
                    st.error(f"Error {response.status_code}")

            except requests.exceptions.RequestException as e:
                if PUBLIC:
                    st.error("The service is unavailable. Please try again later.")
                else:
                    st.error(f"Request failed: {type(e).__name__}")
                    st.info("Make sure the API is running: `./run.sh`")
else:
    st.info("👆 Click 'Ask' to get started.")
