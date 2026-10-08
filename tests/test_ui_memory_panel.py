"""Item #84: UI display of VERA's recalled findings from memory."""
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent


def test_memory_panel_renders_with_recalled_findings():
    """Test that recalled findings are displayed with claim text, source link, and saved date."""
    from vera.memory_panel import render_memory_panel

    mock_st = mock.MagicMock()
    data = {
        "answer": "Test answer",
        "sources": [],
        "recalled": [
            {
                "claim_text": "Earlier finding about quantum physics",
                "source_title": "Quantum Computing Basics",
                "source_url": "https://arxiv.org/abs/2301.00001",
                "saved_at": "2026-10-07T10:30:00"
            }
        ],
        "memory_written": 0
    }

    render_memory_panel(mock_st, data)

    # Should call markdown with the heading
    markdown_calls = [call[0][0] for call in mock_st.markdown.call_args_list]
    assert any("From VERA's memory" in str(call) for call in markdown_calls)
    # Should call caption with memory description
    caption_calls = [call[0][0] for call in mock_st.caption.call_args_list]
    assert any("auto-saved" in str(call).lower() for call in caption_calls)


def test_memory_panel_empty_when_no_recalled_and_no_written():
    """Test that memory panel is not rendered when there are no recalled items and memory_written is 0."""
    from vera.memory_panel import render_memory_panel

    mock_st = mock.MagicMock()
    data = {
        "answer": "Test answer",
        "sources": [],
        "recalled": [],
        "memory_written": 0
    }

    render_memory_panel(mock_st, data)

    # Should not call markdown at all
    mock_st.markdown.assert_not_called()
    mock_st.success.assert_not_called()


def test_memory_panel_shows_memory_written_count():
    """Test that memory_written displays the number of saved findings."""
    from vera.memory_panel import render_memory_panel

    mock_st = mock.MagicMock()
    data = {
        "answer": "Test answer",
        "sources": [],
        "recalled": [],
        "memory_written": 3
    }

    render_memory_panel(mock_st, data)

    # Should call success with the saved count
    success_calls = [call[0][0] for call in mock_st.success.call_args_list]
    assert any("3" in str(call) and "checked" in str(call) for call in success_calls)


def test_memory_panel_handles_missing_keys():
    """Test that the panel gracefully handles missing fields in recalled items."""
    from vera.memory_panel import render_memory_panel

    mock_st = mock.MagicMock()
    data = {
        "answer": "Test answer",
        "sources": [],
        "recalled": [
            {
                "claim_text": "Finding without URL",
                # source_url and source_title missing
            },
            {
                "source_title": "Title without URL and claim",
                "saved_at": "2026-10-07T10:30:00"
                # claim_text and source_url missing
            }
        ],
        "memory_written": 1
    }

    # Should not raise an exception
    render_memory_panel(mock_st, data)

    # Should have called markdown for heading
    markdown_calls = [call[0][0] for call in mock_st.markdown.call_args_list]
    assert any("From VERA's memory" in str(call) for call in markdown_calls)
    # Should have called success for memory_written
    success_calls = [call[0][0] for call in mock_st.success.call_args_list]
    assert any("Saved" in str(call) for call in success_calls)


def test_memory_panel_handles_missing_recalled_and_memory_written_keys():
    """Test backward compatibility when recalled and memory_written keys are absent (older API)."""
    from vera.memory_panel import render_memory_panel

    mock_st = mock.MagicMock()
    data = {
        "answer": "Test answer",
        "sources": []
        # no recalled or memory_written keys at all
    }

    render_memory_panel(mock_st, data)

    # Should not call anything (graceful no-op)
    mock_st.markdown.assert_not_called()
    mock_st.success.assert_not_called()
    mock_st.caption.assert_not_called()


def test_memory_panel_with_multiple_recalled_items():
    """Test that multiple recalled items are all displayed."""
    from vera.memory_panel import render_memory_panel

    mock_st = mock.MagicMock()
    data = {
        "answer": "Test answer",
        "sources": [],
        "recalled": [
            {
                "claim_text": "First finding",
                "source_title": "First Source",
                "source_url": "https://example.com/1",
                "saved_at": "2026-10-07T10:00:00"
            },
            {
                "claim_text": "Second finding",
                "source_title": "Second Source",
                "source_url": "https://example.com/2",
                "saved_at": "2026-10-07T11:00:00"
            }
        ],
        "memory_written": 0
    }

    render_memory_panel(mock_st, data)

    # Should have called markdown for heading
    markdown_calls = [call[0][0] for call in mock_st.markdown.call_args_list]
    assert any("From VERA's memory" in str(call) for call in markdown_calls)
    # Should have called caption multiple times for each item
    caption_calls = mock_st.caption.call_args_list
    assert len(caption_calls) >= 2  # At least 2 captions for the items


def test_memory_written_singular_plural():
    """Test that memory_written message uses correct singular/plural form."""
    from vera.memory_panel import render_memory_panel

    # Test singular
    mock_st = mock.MagicMock()
    data_singular = {
        "answer": "Test answer",
        "sources": [],
        "recalled": [],
        "memory_written": 1
    }

    render_memory_panel(mock_st, data_singular)

    success_calls = [call[0][0] for call in mock_st.success.call_args_list]
    assert any("Saved 1 checked finding" in str(call) and "findings" not in str(call) for call in success_calls)

    # Test plural
    mock_st = mock.MagicMock()
    data_plural = {
        "answer": "Test answer",
        "sources": [],
        "recalled": [],
        "memory_written": 2
    }

    render_memory_panel(mock_st, data_plural)

    success_calls = [call[0][0] for call in mock_st.success.call_args_list]
    assert any("Saved 2 checked findings" in str(call) for call in success_calls)
