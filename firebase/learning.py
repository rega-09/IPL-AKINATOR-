# firebase/learning.py
# ─────────────────────────────────────────────────────────────────────────────
# THE LEARNING BRAIN
#
# This is what the brief calls "learning from incorrect guesses."
# It reads failure patterns from Firestore and uses Gemini to generate
# improvement insights — then those insights feed back into future sessions.
#
# LEARNING LOOP:
#   1. Game ends wrong → record_failure() in Firestore
#   2. Periodically: analyze_failures() reads patterns
#   3. Gemini generates insight: "To identify Dinesh Karthik, ask about
#      his KKR captaincy and finisher role — not just wicketkeeper"
#   4. Insight stored in Firestore insights/ collection
#   5. Next session: insights injected into LLM question prompts
#      → better questions for previously missed players
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
from typing import Dict, List, Optional
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from firebase.firestore_client import db
from llm.gemini_client import claude


# ─────────────────────────────────────────────────────────────────────────────
# LEARNING FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def record_game_outcome(session_result: Dict) -> None:
    """
    Called after every game ends (win or loss).
    Saves session to Firestore and triggers failure recording if wrong.

    Args:
        session_result: The dict returned by GameSession.confirm_guess()
    """
    # Always save the full session
    db.save_session({
        "session_id":      session_result.get("session_id", "unknown"),
        "questions_asked": session_result.get("questions_asked", 0),
        "final_guess":     session_result.get("guessed", ""),
        "correct_player":  session_result.get("correct_player", ""),
        "correct":         session_result.get("correct", False),
        "history":         session_result.get("history", []),
    })

    # On wrong guess — record the failure for learning
    if not session_result.get("correct", True):
        wrong_guess    = session_result.get("guessed", "")
        correct_player = session_result.get("correct_player", "")
        history        = session_result.get("history", [])

        if correct_player:
            db.record_failure(
                wrong_guess    = wrong_guess,
                correct_player = correct_player,
                history        = history,
            )
            print(f"[Learning] Recorded failure: guessed {wrong_guess}, was {correct_player}")

            # Trigger insight generation for players missed multiple times
            _maybe_generate_insight(correct_player)


def _maybe_generate_insight(player_name: str) -> None:
    """
    Generates an LLM insight for a player if they've been missed 3+ times.

    WHY threshold of 3?
        One miss could be bad luck. Three misses = systematic gap.
        We want enough data before spending an LLM call on insight generation.
    """
    from utils.helpers import slugify
    player_id = slugify(player_name)

    # Check miss count from Firestore
    failures = db.get_frequent_failures(min_misses=3)
    player_failures = [f for f in failures if f.get("player_id") == player_id]

    if not player_failures:
        return  # Not missed enough times yet

    # Check if we already have a fresh insight
    insights = db.get_insights()
    if player_id in insights:
        return  # Already have insight for this player

    # Generate insight using Gemini
    failure_data = player_failures[0]
    insight = _generate_player_insight(player_name, failure_data)

    if insight:
        db.save_insight(player_id, player_name, insight)
        print(f"[Learning] Generated insight for {player_name}")


def _generate_player_insight(player_name: str, failure_data: Dict) -> Optional[str]:
    """
    Uses Gemini to analyze failure patterns and generate a specific insight
    about how to better identify a player.

    Returns a short text insight, or None if LLM unavailable.
    """
    if not claude.available:
        return None

    # Build context from failure patterns
    patterns = failure_data.get("failure_patterns", [])
    miss_count = failure_data.get("miss_count", 0)

    # Format failed Q&A pairs for LLM context
    failed_qa = []
    for pattern in patterns[-3:]:  # Last 3 failures
        wrong = pattern.get("wrong_guess", "Unknown")
        qs    = pattern.get("questions_asked", [])
        qa_str = ", ".join([f"'{q['q'][:40]}' → {q['a']}" for q in qs[:4]])
        failed_qa.append(f"  Guessed {wrong}: [{qa_str}]")

    failed_context = "\n".join(failed_qa) if failed_qa else "  No detailed history"

    system_prompt = (
        "You are an IPL cricket expert helping an AI guessing game improve. "
        "Analyze why the game keeps failing to identify a player and suggest "
        "what specific distinguishing questions would help identify them. "
        "Be concise — 2-3 sentences maximum."
    )

    user_message = f"""
The IPL Akinator game has failed to identify {player_name} {miss_count} times.

Recent failure patterns (what was asked and guessed wrong):
{failed_context}

What unique attributes of {player_name} should the game focus on to identify them correctly?
What question(s) would definitively distinguish {player_name} from similar players?
""".strip()

    return claude.complete(
        system_prompt = system_prompt,
        user_message  = user_message,
        max_tokens    = 150,
        temperature   = 0.4,
    )


def get_learning_context() -> str:
    """
    Returns a formatted string of all stored insights to inject into
    the LLM question generator prompt.

    WHY inject into prompts?
        The question generator (in enhancer.py) can use this context
        to ask more targeted questions when specific players are candidates.

    Returns:
        Multi-line string of player insights, or empty string if none.
    """
    insights = db.get_insights()
    if not insights:
        return ""

    lines = ["LEARNED PLAYER INSIGHTS (from past failures):"]
    for player_id, insight in list(insights.items())[:10]:  # Max 10 insights in context
        player_name = player_id.replace("_", " ").title()
        lines.append(f"  • {player_name}: {insight}")

    return "\n".join(lines)


def get_learning_stats() -> Dict:
    """
    Returns learning system stats for the /health endpoint.
    """
    stats = db.get_stats()
    failures = db.get_frequent_failures(min_misses=1)
    insights = db.get_insights()

    return {
        **stats,
        "frequent_failures": len(failures),
        "insights_generated": len(insights),
        "top_missed_players": [
            f.get("player_name", "Unknown")
            for f in failures[:5]
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== learning.py self-test ===\n")
    print(f"Firestore available : {db.available}")
    print(f"Gemini available    : {claude.available}")

    print("\nTEST 1 — Learning context (from stored insights)")
    ctx = get_learning_context()
    print(f"  Context length: {len(ctx)} chars")
    print(f"  Preview: {ctx[:100]}..." if ctx else "  No insights yet (empty Firestore)")

    print("\nTEST 2 — Learning stats")
    stats = get_learning_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    if db.available:
        print("\nTEST 3 — Record simulated failure")
        record_game_outcome({
            "session_id":      "test-learning-001",
            "questions_asked": 8,
            "guessed":         "MS Dhoni",
            "correct_player":  "Dinesh Karthik",
            "correct":         False,
            "history": [
                {"question_text": "Is your player a wicketkeeper?", "answer": "yes"},
                {"question_text": "Has your player captained an IPL team?", "answer": "yes"},
            ],
        })
        print("  ✅ Failure recorded")

    print("\n✅ learning.py test complete")