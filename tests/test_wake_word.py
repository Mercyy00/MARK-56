"""
Unit tests for core/wake_word.py and multi-wake-phrase configuration.
"""
import pytest
from core.wake_word import (
    DEFAULT_WAKE_WORDS,
    WakeWordDetector,
    is_installed,
)
from memory.config_manager import (
    get_wake_words,
    save_wake_words,
)


def test_default_wake_words_contain_multiple_options():
    assert len(DEFAULT_WAKE_WORDS) >= 4
    lower_words = [w.lower() for w in DEFAULT_WAKE_WORDS]
    assert "hey jarvis" in lower_words
    assert "jarvis" in lower_words
    assert "computer" in lower_words
    assert "friday" in lower_words


def test_config_manager_wake_words_roundtrip():
    original = get_wake_words()
    try:
        custom = ["Jarvis", "Computer", "Friday", "Mark 56", "Matrix"]
        save_wake_words(custom)
        loaded = get_wake_words()
        assert loaded == custom
    finally:
        save_wake_words(original)


def test_wake_detector_custom_phrases():
    detected = []

    def on_detect(phrase: str = "wake word"):
        detected.append(phrase)

    detector = WakeWordDetector(
        on_detect=on_detect,
        wake_words=["Friday", "Computer", "Jarvis"],
    )

    assert detector.wake_words == ["Friday", "Computer", "Jarvis"]

    # Trigger detection directly
    detector._trigger("Friday")
    assert detected == ["Friday"]

    detector._trigger("Computer")
    assert detected == ["Friday", "Computer"]


def test_wake_detector_feed_does_not_crash():
    import numpy as np
    detector = WakeWordDetector(
        on_detect=lambda: None,
        wake_words=["Jarvis"],
    )
    # When not running, feeding should safely no-op
    detector.feed(np.zeros((1280,), dtype=np.int16))
    assert detector._queue.empty()
