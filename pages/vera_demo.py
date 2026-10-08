"""Streamlit multipage entry: VERA demo (M7). All logic lives in vera/m7/."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from vera.m7.data import load_latest_report  # noqa: E402
from vera.m7.demo_ui import render_demo  # noqa: E402
from vera.sources_sidebar import render_sources_sidebar  # noqa: E402

st.set_page_config(page_title="VERA demo", layout="wide")
render_sources_sidebar(st)
_rep, _note = load_latest_report()
render_demo(_rep, _note)
