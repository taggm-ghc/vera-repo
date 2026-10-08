"""Streamlit multipage entry: VERA Trace Eval (Week 4). All logic lives in vera/trace_eval/ui.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from vera.sources_sidebar import render_sources_sidebar  # noqa: E402
from vera.trace_eval.ui import render_trace_eval  # noqa: E402

st.set_page_config(page_title="VERA Trace Eval", layout="wide")
render_sources_sidebar(st)
render_trace_eval()
