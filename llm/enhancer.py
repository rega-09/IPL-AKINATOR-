# llm/enhancer.py
# ─────────────────────────────────────────────────────────────────────────────
# WHY THIS FILE EXISTS:
#   The enhancer sits between the game engine and the API routes.
#   It takes raw engine output and optionally enriches it using Claude.
#
#   Key design principle: GRACEFUL DEGRADATION
#     If the LLM is unavailable (no API key, rate limit, network error),
#     the game returns the raw engine output unchanged.
#     The game NEVER breaks because of LLM unavailability.
#
#   Think of it as a decorator pattern:
#     Raw engine output → Enhancer → Richer output (with LLM)
#                                  → Same output   (without LLM)
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, List, Optional
import time
from llm.gemini_client import claude

# Simple rate limiter — ensures minimum 4 seconds between LLM calls
# WHY 4s? Free tier = 15 RPM = 1 call per 4 seconds max
_last_call_time = 0.0

def _rate_limit():
    global _last_call_time
    elapsed = time.time() - _last_call_time
    if elapsed < 4.0:
        time.sleep(4.0 - elapsed)
    _last_call_time = time.time()
from llm.prompts import (
    QUESTION_REWRITER_SYSTEM,
    CONFIDENCE_NARRATOR_SYSTEM,
    build_question_rewrite_prompt,
    build_confidence_narrator_prompt,
    build_dynamic_question_prompt,
)


# ─────────────────────────────────────────────────────────────────────────────
# ENHANCER FUNCTIONS
# Each function enhances one specific piece of engine output.
# ─────────────────────────────────────────────────────────────────────────────

def enhance_question(
    raw_question:   Dict,
    history:        List[Dict],
    top_candidates: List[Dict],
    active_count:   int,
) -> Dict:
    """
    Takes a raw question dict from the engine and returns an enhanced version
    with a naturally phrased question text.

    WHY return the full question dict (not just the text)?
        The engine needs the original question ID to do Bayesian updates.
        We only replace the display text — the ID stays the same.

    Fallback: if LLM fails, returns original question unchanged.

    Args:
        raw_question   : { id, text, category } from engine
        history        : Q&A history so far
        top_candidates : Current top 3 candidates
        active_count   : Players still in contention

    Returns:
        Enhanced question dict with rephrased text (or original on failure)
    """
    if not claude.available:
        return raw_question

    # Skip enhancement for first question — engine picks best first Q
    # and there's no history context yet to make rephrasing meaningful
    if len(history) == 0:
        return raw_question

    user_message = build_question_rewrite_prompt(
        raw_question   = raw_question["text"],
        history        = history,
        top_candidates = top_candidates,
        active_count   = active_count,
    )

    result = claude.complete_json(
        system_prompt = QUESTION_REWRITER_SYSTEM,
        user_message  = user_message,
    )

    # Validate output — must have "rephrased" key with non-empty string
    if (
        result
        and isinstance(result, dict)
        and "rephrased" in result
        and isinstance(result["rephrased"], str)
        and len(result["rephrased"]) > 10
    ):
        # Return enhanced question — same ID (for engine), new text (for user)
        return {
            **raw_question,                       # Keep id, category
            "text":         result["rephrased"],  # Replace display text
            "original_text": raw_question["text"] # Keep original for debugging
        }

    # Fallback — LLM output was invalid
    return raw_question


def enhance_guess(
    history:        List[Dict],
    top_candidates: List[Dict],
    final_guess:    str,
    confidence_pct: str,
) -> str:
    """
    Generates a natural language narration explaining WHY the system
    is guessing a specific player.

    This is what makes the system feel like a genuine cricket expert
    rather than a probability machine.

    Fallback: returns a simple template string if LLM fails.

    Args:
        history        : Full Q&A game history
        top_candidates : Top candidates with probabilities
        final_guess    : Player name we're guessing
        confidence_pct : e.g. "87.3%"

    Returns:
        Narration string to display to user before the guess
    """
    if not claude.available:
        return _fallback_narration(final_guess, confidence_pct, top_candidates)

    user_message = build_confidence_narrator_prompt(
        history        = history,
        top_candidates = top_candidates,
        final_guess    = final_guess,
        confidence_pct = confidence_pct,
    )

    result = claude.complete(
        system_prompt = CONFIDENCE_NARRATOR_SYSTEM,
        user_message  = user_message,
        max_tokens    = 150,
        temperature   = 0.6,
    )

    if result and len(result) > 20:
        return result

    # Fallback
    return _fallback_narration(final_guess, confidence_pct, top_candidates)


def generate_dynamic_question(
    history:        List[Dict],
    top_candidates: List[Dict],
    active_count:   int,
    asked_ids:      List[str],
) -> Optional[Dict]:
    """
    When the question bank runs out of high-information-gain questions,
    asks Claude to generate a brand new question targeting the remaining
    ambiguity.

    WHY only use this as a fallback?
        LLM-generated questions can't be validated against player attributes
        the same way bank questions can — Bayesian scoring won't work.
        We use this ONLY when the engine has no better option.

    Returns:
        A question dict { id, text, category } or None if LLM fails.
        Note: id will be "llm_generated" — handled specially in game_session.
    """
    if not claude.available:
        return None

    user_message = build_dynamic_question_prompt(
        history        = history,
        top_candidates = top_candidates,
        active_count   = active_count,
        asked_ids      = asked_ids,
    )

    result = claude.complete_json(
        system_prompt = (
            "You are an IPL cricket expert playing a guessing game. "
            "Output ONLY valid JSON with keys 'question' and 'targets'. "
            "No markdown, no explanation."
        ),
        user_message  = user_message,
        max_tokens    = 200,
    )

    if (
        result
        and isinstance(result, dict)
        and "question" in result
        and len(result["question"]) > 10
    ):
        return {
            "id":       "llm_generated",
            "text":     result["question"],
            "category": "llm",
            "targets":  result.get("targets", "unknown"),
        }

    return None


# ─────────────────────────────────────────────────────────────────────────────
# PRIVATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _fallback_narration(
    final_guess:    str,
    confidence_pct: str,
    top_candidates: List[Dict],
) -> str:
    """
    Template-based narration when LLM is unavailable.
    Always works — no external dependency.
    """
    if len(top_candidates) >= 2:
        second = top_candidates[1]["name"]
        return (
            f"Based on all your answers, the evidence points clearly to one player. "
            f"While {second} was briefly in contention, the profile fits only one person. "
            f"I believe your player is {final_guess}! (Confidence: {confidence_pct})"
        )
    return (
        f"The answers you gave match one player's profile very closely. "
        f"I believe your player is {final_guess}! (Confidence: {confidence_pct})"
    )


# ─────────────────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== enhancer.py self-test ===\n")

    sample_history = [
        {
            "question_number": 1,
            "question_text":   "Has your player played more than 10 IPL seasons?",
            "answer":          "yes",
            "top_candidates":  [],
            "entropy":         4.2,
            "active_count":    24,
        },
        {
            "question_number": 2,
            "question_text":   "Does your player bowl pace (fast or medium-fast)?",
            "answer":          "yes",
            "top_candidates":  [],
            "entropy":         3.0,
            "active_count":    8,
        },
        {
            "question_number": 3,
            "question_text":   "Has your player played for Mumbai Indians (MI)?",
            "answer":          "yes",
            "top_candidates":  [],
            "entropy":         2.1,
            "active_count":    4,
        },
    ]

    sample_candidates = [
        {"name": "Jasprit Bumrah",    "probability": 0.72, "probability_pct": "72.0%",
         "player_id": "jasprit_bumrah"},
        {"name": "Lasith Malinga",    "probability": 0.15, "probability_pct": "15.0%",
         "player_id": "lasith_malinga"},
        {"name": "Trent Boult",       "probability": 0.08, "probability_pct": "8.0%",
         "player_id": "trent_boult"},
    ]

    raw_q = {
        "id":       "is_pure_bowler",
        "text":     "Is your player primarily a bowler (not a batting all-rounder)?",
        "category": "role",
    }

    print(f"LLM Available: {claude.available}\n")

    # Test 1: Question enhancement
    print("TEST 1 — enhance_question()")
    enhanced_q = enhance_question(
        raw_question   = raw_q,
        history        = sample_history,
        top_candidates = sample_candidates,
        active_count   = 4,
    )
    print(f"  Original : {raw_q['text']}")
    print(f"  Enhanced : {enhanced_q['text']}")
    if claude.available:
        print(f"  LLM used : {'original_text' in enhanced_q}")

    # Test 2: Guess narration
    print("\nTEST 2 — enhance_guess()")
    narration = enhance_guess(
        history        = sample_history,
        top_candidates = sample_candidates,
        final_guess    = "Jasprit Bumrah",
        confidence_pct = "72.0%",
    )
    print(f"  Narration: {narration}")

    # Test 3: Fallback narration (always works)
    print("\nTEST 3 — _fallback_narration() (no LLM)")
    fallback = _fallback_narration("Jasprit Bumrah", "72.0%", sample_candidates)
    print(f"  Fallback : {fallback}")

    print("\n✅ enhancer.py tests complete")