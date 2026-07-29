"""
MindGuardian AI — Suicide / Crisis Risk Detector

Primary model  : «gooofy/suicide-risk-classifier»
  Labels       : suicide, non-suicide
  Source       : Fine-tuned DistilBERT on the Suicide and Depression
                 Detection dataset (Kaggle).

Fallback heuristic
  If the HuggingFace model is unavailable (no internet / no torch),
  a keyword-based heuristic is used so the app still provides
  basic safety flagging.

Risk levels
-----------
  low    — model predicts non-suicide with high confidence  (< 0.40 suicide score)
  medium — borderline or model predicts suicide score 0.40–0.70
  high   — model predicts suicide with confidence > 0.70
"""

from __future__ import annotations
import logging
import re

logger = logging.getLogger(__name__)

_risk_pipeline = None


def _load_pipeline():
    global _risk_pipeline
    if _risk_pipeline is not None:
        return _risk_pipeline

    try:
        from transformers import pipeline
        logger.info("Loading risk detection model…")
        _risk_pipeline = pipeline(
            task="text-classification",
            model="gooofy/suicide-risk-classifier",
            top_k=None,         # return all labels so we can pick "suicide" score
            truncation=True,
            max_length=512,
        )
        logger.info("Risk model loaded.")
    except Exception as exc:
        logger.warning("Could not load risk model (%s). Using keyword fallback.", exc)
        _risk_pipeline = None

    return _risk_pipeline


# ---------------------------------------------------------------------------
# Keyword-based fallback heuristic
# ---------------------------------------------------------------------------

_HIGH_RISK_KEYWORDS = re.compile(
    r"\b(kill\s+myself|end\s+my\s+life|want\s+to\s+die|suicide|suicidal"
    r"|no\s+reason\s+to\s+live|can't\s+go\s+on|better\s+off\s+dead"
    r"|take\s+my\s+own\s+life|self.harm|cut\s+myself|overdose)\b",
    re.IGNORECASE,
)

_MEDIUM_RISK_KEYWORDS = re.compile(
    r"\b(hopeless|worthless|no\s+one\s+cares|give\s+up|exhausted"
    r"|can't\s+take\s+it|falling\s+apart|hate\s+myself|disappear"
    r"|pointless|nothing\s+matters|empty\s+inside)\b",
    re.IGNORECASE,
)


def _keyword_risk(text: str) -> dict:
    if _HIGH_RISK_KEYWORDS.search(text):
        return {"level": "high",   "score": 0.85, "source": "keyword"}
    if _MEDIUM_RISK_KEYWORDS.search(text):
        return {"level": "medium", "score": 0.55, "source": "keyword"}
    return {"level": "low",    "score": 0.10, "source": "keyword"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_risk(text: str) -> dict:
    """
    Detect suicide / crisis risk in *text*.

    Returns
    -------
    {
        "level":  str,   # "low" | "medium" | "high"
        "score":  float, # probability of the suicide class (0–1)
        "source": str,   # "model" | "keyword"
    }
    """
    _FALLBACK = {"level": "low", "score": 0.0, "source": "fallback"}

    if not text or len(text.strip()) < 3:
        return _FALLBACK

    pipe = _load_pipeline()

    # --- Model path ---
    if pipe is not None:
        try:
            results = pipe(text[:512])
            # results = [[{"label": "suicide", "score": ...}, {"label": "non-suicide", ...}]]
            all_labels = results[0] if isinstance(results[0], list) else results
            suicide_score = next(
                (r["score"] for r in all_labels if r["label"].lower() == "suicide"),
                0.0,
            )

            if suicide_score >= 0.70:
                level = "high"
            elif suicide_score >= 0.40:
                level = "medium"
            else:
                level = "low"

            return {"level": level, "score": round(float(suicide_score), 4), "source": "model"}

        except Exception as exc:
            logger.warning("Risk model inference failed: %s. Falling back to keywords.", exc)

    # --- Keyword fallback ---
    return _keyword_risk(text)


# ---------------------------------------------------------------------------
# Utility helpers (used by templates / dashboard)
# ---------------------------------------------------------------------------

RISK_COLOR: dict[str, str] = {
    "low":    "success",
    "medium": "warning",
    "high":   "danger",
}

RISK_ICON: dict[str, str] = {
    "low":    "shield-check",
    "medium": "alert-triangle",
    "high":   "alert-octagon",
}


def risk_badge(level: str) -> dict:
    """Return display metadata for a risk level string."""
    level = level or "low"
    return {
        "level": level,
        "color": RISK_COLOR.get(level, "secondary"),
        "icon":  RISK_ICON.get(level, "info"),
    }
