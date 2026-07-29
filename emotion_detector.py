"""
MindGuardian AI — Emotion Detector

Uses the Hugging Face pipeline with:
    j-hartmann/emotion-english-distilroberta-base

Labels: anger, disgust, fear, joy, neutral, sadness, surprise

The pipeline is loaded once at module level (lazy-loaded on first call)
to avoid slowing down app startup.
"""

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

# Module-level singleton — populated on first call
_emotion_pipeline = None


def _load_pipeline():
    """Load the HuggingFace emotion classification pipeline (once)."""
    global _emotion_pipeline
    if _emotion_pipeline is not None:
        return _emotion_pipeline

    try:
        from transformers import pipeline
        logger.info("Loading emotion detection model…")
        _emotion_pipeline = pipeline(
            task="text-classification",
            model="j-hartmann/emotion-english-distilroberta-base",
            top_k=1,                    # return only the top label
            truncation=True,
            max_length=512,
        )
        logger.info("Emotion model loaded.")
    except Exception as exc:
        logger.warning("Could not load emotion model (%s). Using fallback.", exc)
        _emotion_pipeline = None

    return _emotion_pipeline


# ---------------------------------------------------------------------------
# Emoji map for UI display
# ---------------------------------------------------------------------------

EMOTION_EMOJI: dict[str, str] = {
    "joy":      "😊",
    "sadness":  "😢",
    "anger":    "😠",
    "fear":     "😨",
    "disgust":  "🤢",
    "surprise": "😲",
    "neutral":  "😐",
}

# Colour map (Bootstrap badge classes)
EMOTION_COLOR: dict[str, str] = {
    "joy":      "success",
    "sadness":  "primary",
    "anger":    "danger",
    "fear":     "warning",
    "disgust":  "secondary",
    "surprise": "info",
    "neutral":  "light",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_emotion(text: str) -> dict:
    """
    Detect the dominant emotion in *text*.

    Returns
    -------
    {
        "label": str,   # e.g. "joy"
        "score": float, # confidence 0–1
        "emoji": str,
        "color": str,   # Bootstrap badge class
    }

    Falls back to {"label": "neutral", "score": 0.0, ...} if the model
    is unavailable or the text is too short.
    """
    _FALLBACK = {
        "label": "neutral",
        "score": 0.0,
        "emoji": EMOTION_EMOJI["neutral"],
        "color": EMOTION_COLOR["neutral"],
    }

    if not text or len(text.strip()) < 3:
        return _FALLBACK

    pipe = _load_pipeline()
    if pipe is None:
        return _FALLBACK

    try:
        # pipeline returns [[{"label": ..., "score": ...}]] with top_k=1
        result = pipe(text[:512])
        top    = result[0][0] if isinstance(result[0], list) else result[0]
        label  = top["label"].lower()
        score  = float(top["score"])

        return {
            "label": label,
            "score": score,
            "emoji": EMOTION_EMOJI.get(label, "❓"),
            "color": EMOTION_COLOR.get(label, "secondary"),
        }
    except Exception as exc:
        logger.warning("Emotion detection failed: %s", exc)
        return _FALLBACK
