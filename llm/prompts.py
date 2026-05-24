# llm/prompts.py
# ─────────────────────────────────────────────────────────────────────────────
# WHY THIS FILE EXISTS:
#   All prompt templates live here — NOT scattered across files.
#
#   Benefits:
#     1. Easy to iterate — tweak a prompt in ONE place
#     2. Prompts are readable as plain strings — not buried in logic
#     3. Each prompt has a clear contract (inputs → expected output format)
#
# PROMPT ENGINEERING PRINCIPLES USED:
#   - Role assignment  : "You are an IPL expert..."
#   - Output format    : Explicit JSON schema or plain text constraints
#   - Few-shot examples: Show Claude what good output looks like
#   - Constraints      : "Do NOT...", "ONLY output..."
#   - Context injection: Dynamic placeholders filled at runtime
# ─────────────────────────────────────────────────────────────────────────────

from typing import List, Dict


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPTS
# These define Claude's role for the entire conversation.
# Passed as the `system` parameter — sets the frame for all user messages.
# ─────────────────────────────────────────────────────────────────────────────

QUESTION_REWRITER_SYSTEM = """
You are an expert IPL cricket analyst hosting a live "Guess the Player" game show.

Your job is to take a mechanical yes/no question and rephrase it to sound like a
natural, engaging question a knowledgeable cricket host would ask — while keeping
the exact same meaning and yes/no answerable format.

Rules:
- Output ONLY a JSON object. No explanations, no preamble, no markdown.
- The rephrased question must still be answerable with yes, no, maybe, or don't know.
- Make it conversational and cricket-savvy — reference IPL context where natural.
- Keep it under 20 words.
- Do NOT change the factual meaning of the question.
- Do NOT add information that wasn't in the original question.

Output format:
{"rephrased": "your rephrased question here"}
""".strip()


CONFIDENCE_NARRATOR_SYSTEM = """
You are a sharp IPL cricket analyst explaining your deduction process in a
Sherlock Holmes style — confident, cricket-specific, and engaging.

Your job is to look at the Q&A history and top candidate probabilities,
then produce a short 2-3 sentence narration explaining WHY you think
the top candidate is the correct player.

Rules:
- Be specific — reference actual answers from the history.
- Sound confident but not arrogant.
- Use cricket terminology naturally.
- Output ONLY the narration text — no JSON, no labels.
- Maximum 60 words.
- End with the guess: "I believe your player is [Name]!"
""".strip()


# ─────────────────────────────────────────────────────────────────────────────
# USER MESSAGE BUILDERS
# Functions that construct the user message for each prompt type.
# WHY functions and not f-strings directly in the caller?
#   Keeps the prompt logic in ONE file — callers just call a function.
# ─────────────────────────────────────────────────────────────────────────────

def build_question_rewrite_prompt(
    raw_question:     str,
    history:          List[Dict],
    top_candidates:   List[Dict],
    active_count:     int,
) -> str:
    """
    Builds the user message asking Claude to rephrase a question.

    Args:
        raw_question   : The mechanical question from the engine
        history        : List of previous Q&A turns
        top_candidates : Current top 3 players with probabilities
        active_count   : How many players are still in contention

    Returns:
        Formatted user message string
    """

    # Build history summary (last 3 turns max — keep context short)
    history_lines = []
    for turn in history[-3:]:
        history_lines.append(
            f"  Q: {turn['question_text'][:50]}... → {turn['answer'].upper()}"
        )
    history_text = "\n".join(history_lines) if history_lines else "  (No questions asked yet)"

    # Build top candidates summary
    candidates_text = ", ".join(
        f"{c['name']} ({c['probability_pct']})"
        for c in top_candidates[:3]
    )

    return f"""
Rephrase this question for the IPL Akinator game show:

ORIGINAL QUESTION: "{raw_question}"

GAME CONTEXT:
- Players still in contention: {active_count}
- Top candidates right now: {candidates_text}
- Recent Q&A history:
{history_text}

Output the rephrased question as JSON: {{"rephrased": "..."}}
""".strip()


def build_confidence_narrator_prompt(
    history:        List[Dict],
    top_candidates: List[Dict],
    final_guess:    str,
    confidence_pct: str,
) -> str:
    """
    Builds the user message asking Claude to narrate its reasoning
    before making the final guess.

    Args:
        history        : Full Q&A history of the game
        top_candidates : Top 3 players with probabilities
        final_guess    : The player name we're about to guess
        confidence_pct : e.g. "87.3%"

    Returns:
        Formatted user message string
    """

    # Format full history for Claude to reason over
    history_lines = []
    for turn in history:
        history_lines.append(
            f"  Q{turn['question_number']}: {turn['question_text'][:55]}... "
            f"→ {turn['answer'].upper()}"
        )
    history_text = "\n".join(history_lines)

    # Format candidates
    candidates_text = "\n".join(
        f"  - {c['name']}: {c['probability_pct']}"
        for c in top_candidates[:3]
    )

    return f"""
You are about to guess the IPL player. Here is the full game so far:

Q&A HISTORY:
{history_text}

CURRENT PROBABILITY RANKINGS:
{candidates_text}

Your top guess: {final_guess} (confidence: {confidence_pct})

Write a 2-3 sentence narration explaining WHY {final_guess} fits all these answers.
Be specific — reference actual answers. End with: "I believe your player is {final_guess}!"
""".strip()


def build_dynamic_question_prompt(
    history:        List[Dict],
    top_candidates: List[Dict],
    active_count:   int,
    asked_ids:      List[str],
) -> str:
    """
    Asks Claude to generate a brand new question from scratch
    (used when the engine's question bank runs low on high-IG questions).

    WHY this as a fallback?
        The question bank has 53 questions — usually enough for 8 turns.
        But for edge cases where the pool is stuck, Claude can generate
        a novel question targeting the remaining ambiguity.

    Args:
        history        : Full Q&A history
        top_candidates : Current top candidates
        active_count   : Players still in contention
        asked_ids      : Question IDs already used (to avoid repeating topics)

    Returns:
        Formatted user message string
    """

    history_lines = [
        f"  Q{t['question_number']}: {t['question_text'][:55]}... → {t['answer'].upper()}"
        for t in history
    ]
    history_text = "\n".join(history_lines) if history_lines else "  (None yet)"

    candidates_text = "\n".join(
        f"  - {c['name']}: {c['probability_pct']}"
        for c in top_candidates[:5]
    )

    return f"""
You are playing IPL Akinator. Generate the single best yes/no question to identify
the mystery player from the remaining candidates.

Q&A SO FAR:
{history_text}

TOP REMAINING CANDIDATES:
{candidates_text}
(Total still in contention: {active_count})

Generate ONE question that best distinguishes between these candidates.
The question must:
- Be answerable with yes/no/maybe/don't know
- Target something NOT already asked (batting style, specific team era, known achievement)
- Maximally split the remaining candidates

Output ONLY JSON: {{"question": "your question here", "targets": "what attribute this tests"}}
""".strip()


# ─────────────────────────────────────────────────────────────────────────────
# SELF-TEST (no API call — just tests prompt building)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== prompts.py self-test ===\n")

    sample_history = [
        {
            "question_number": 1,
            "question_text": "Has your player played more than 10 IPL seasons?",
            "answer": "yes",
            "top_candidates": [],
            "entropy": 4.2,
            "active_count": 24,
        },
        {
            "question_number": 2,
            "question_text": "Has your player won 3 or more IPL titles?",
            "answer": "no",
            "top_candidates": [],
            "entropy": 3.1,
            "active_count": 12,
        },
    ]

    sample_candidates = [
        {"name": "Jasprit Bumrah",    "probability": 0.42, "probability_pct": "42.0%"},
        {"name": "Bhuvneshwar Kumar", "probability": 0.18, "probability_pct": "18.0%"},
        {"name": "Yuzvendra Chahal",  "probability": 0.15, "probability_pct": "15.0%"},
    ]

    # Test 1: Question rewrite prompt
    print("TEST 1 — Question rewrite prompt")
    prompt = build_question_rewrite_prompt(
        raw_question   = "Does your player bowl pace (fast or medium-fast)?",
        history        = sample_history,
        top_candidates = sample_candidates,
        active_count   = 8,
    )
    print(f"  Length : {len(prompt)} chars")
    print(f"  Preview: {prompt[:120]}...")
    print("  ✅ Built successfully")

    # Test 2: Confidence narrator prompt
    print("\nTEST 2 — Confidence narrator prompt")
    prompt2 = build_confidence_narrator_prompt(
        history        = sample_history,
        top_candidates = sample_candidates,
        final_guess    = "Jasprit Bumrah",
        confidence_pct = "42.0%",
    )
    print(f"  Length : {len(prompt2)} chars")
    print(f"  Preview: {prompt2[:120]}...")
    print("  ✅ Built successfully")

    # Test 3: Dynamic question prompt
    print("\nTEST 3 — Dynamic question prompt")
    prompt3 = build_dynamic_question_prompt(
        history        = sample_history,
        top_candidates = sample_candidates,
        active_count   = 8,
        asked_ids      = ["long_career", "won_multiple_titles"],
    )
    print(f"  Length : {len(prompt3)} chars")
    print(f"  Preview: {prompt3[:120]}...")
    print("  ✅ Built successfully")

    print("\n✅ All prompt tests passed")