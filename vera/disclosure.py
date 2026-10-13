"""Item #74 M2: the one public no-profiling / limits disclosure. The text lives only here so tests can pin it."""
import json

from vera.memory_gate import CONFIG_KEY, CONFIG_PATH

_COMMON = ("VERA is an AI system, so its answers are AI-generated. They draw only on the sources cited, "
           "are not neutral or complete, and may be wrong. Check the sources. "
           "VERA keeps no profile of you and does not tailor answers to you. It does not save your question or who you are. ")

# Matches memory.store.confirm_required = true (D6, 50644f0): findings are saved as pending, only the owner confirms.
DISCLOSURE_TEXT = (_COMMON + "VERA's memory holds only checked findings that cite a scholarly source. "
                   "A new finding is saved as pending, and only VERA's owner can confirm it.")

# Used only if confirm_required is off: findings would be saved without owner confirmation.
DISCLOSURE_TEXT_UNCONFIRMED = (_COMMON + "VERA's memory holds only checked findings that cite a scholarly source.")


def confirm_required(path=CONFIG_PATH) -> bool:
    """True unless the memory config explicitly turns owner confirmation off (unreadable config -> True, the stricter text)."""
    try:
        return bool(json.loads(open(path).read())[CONFIG_KEY]["store"].get("confirm_required", True))
    except (OSError, ValueError, KeyError, TypeError):
        return True


def disclosure_text(path=CONFIG_PATH) -> str:
    return DISCLOSURE_TEXT if confirm_required(path) else DISCLOSURE_TEXT_UNCONFIRMED


def render_disclosure(st) -> None:
    st.caption(disclosure_text())
