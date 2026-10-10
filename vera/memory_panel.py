"""Item #84: Minimal UI display of VERA's recalled findings from memory."""


def render_memory_panel(st, data: dict) -> None:
    """Display recalled findings from memory. Handles missing keys gracefully.

    Args:
        st: Streamlit module
        data: Response dict containing optional 'recalled' and 'memory_written' keys.
              recalled: list of {"claim_text","source_title","source_url","saved_at"}
              memory_written: int (count of findings saved)
    """
    from vera.sources_sidebar import _link, plain
    from vera.ui_safety import safe_markdown

    recalled = data.get("recalled") or []
    memory_written = data.get("memory_written", 0)

    if not recalled and memory_written <= 0:
        return

    if recalled:
        st.markdown("### 🧠 From VERA's memory")
        st.caption("Checked, cited findings confirmed by VERA's operator (confirmed is not proof of truth). "
                   "Never your question or who asked.")
        for item in recalled:
            claim_text = item.get("claim_text", "")
            source_title = item.get("source_title", "")
            source_url = item.get("source_url", "")
            saved_at = item.get("saved_at", "")

            # Format the display
            if claim_text:
                st.markdown(safe_markdown(claim_text))
            if source_title or source_url:
                st.caption(_link(source_title or source_url, source_url))
            if saved_at:
                st.caption(f"Saved {plain(saved_at)}")

    if memory_written > 0:
        st.success(f"Saved {memory_written} checked finding{'s' if memory_written != 1 else ''} to memory")
