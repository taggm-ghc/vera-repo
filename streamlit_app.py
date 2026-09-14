# Streamlit UI for VERA `/ask` Endpoint
import streamlit as st
import requests
import json

# Configuration
API_BASE_URL = "http://127.0.0.1:8001"
if "API_BASE_URL" in st.session_state:
    API_BASE_URL = st.session_state["API_BASE_URL"]

st.title("VERA - Question Answering Service")

# Sidebar for settings
st.sidebar.header("Settings")
st.sidebar.subheader("API Configuration")
api_url = st.sidebar.text_input(
    "API Base URL",
    value=API_BASE_URL,
    help="Your Render URL for production: https://your-service.onrender.com"
)
def save_api_url():
    st.session_state["API_BASE_URL"] = api_url
st.sidebar.button("Save API URL", on_click=save_api_url)

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
    else:
        with st.spinner("🤔 Thinking..."):
            try:
                # Make API request
                response = requests.post(
                    f"{API_BASE_URL}/ask",
                    json={"question": question, "force_bad": force_bad},
                    headers={"Content-Type": "application/json"},
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
                    st.error("❌ API key error. Check your .env file.")
                    
                elif response.status_code == 402:
                    st.error("❌ Insufficient quota. Add credits to your OpenAI account.")
                    
                elif response.status_code == 429:
                    st.error("❌ Rate limit exceeded. Wait a few seconds and try again.")
                    
                else:
                    st.error(f"❌ Error {response.status_code}: {response.text}")
                    
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Request failed: {e}")
                st.info("💡 Make sure the API is running: `uvicorn main:app --reload`")
else:
    st.info("👆 Click 'Ask' to get started.")
