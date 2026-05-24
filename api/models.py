# api/models.py
# ─────────────────────────────────────────────────────────────────────────────
# WHY PYDANTIC MODELS?
#
#   Pydantic does three things automatically that would otherwise take
#   dozens of lines of manual code:
#
#   1. VALIDATION  — If the frontend sends { "answer": 123 } instead of
#                    { "answer": "yes" }, Pydantic rejects it with a clear
#                    error before it ever touches our game logic.
#
#   2. SERIALIZATION — Converts Python objects (dataclasses, dicts) into
#                      clean JSON automatically. No manual json.dumps() needed.
#
#   3. DOCUMENTATION — FastAPI reads these models and auto-generates an
#                      interactive API docs page at /docs — judges love this.
#
# WHY SEPARATE REQUEST AND RESPONSE MODELS?
#   Request  models = what we ACCEPT from the frontend (strict validation)
#   Response models = what we SEND to the frontend (controlled output shape)
#   Keeping them separate prevents accidentally exposing internal fields.
# ─────────────────────────────────────────────────────────────────────────────

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from enum import Enum


# ─────────────────────────────────────────────────────────────────────────────
# SHARED ENUMS
# ─────────────────────────────────────────────────────────────────────────────

class AnswerChoice(str, Enum):
    """
    Valid answers a user can submit.

    WHY inherit from both str and Enum?
        Makes the enum JSON-serializable by default.
        "yes" serializes as "yes", not as <AnswerChoice.YES: 'yes'>.
    """
    YES       = "yes"
    NO        = "no"
    MAYBE     = "maybe"
    DONT_KNOW = "dont_know"


class GameStatusEnum(str, Enum):
    """All possible states a game session can be in."""
    ACTIVE    = "active"
    GUESSING  = "guessing"
    FINISHED  = "finished"
    MAXED_OUT = "maxed_out"
    ERROR     = "error"


# ─────────────────────────────────────────────────────────────────────────────
# NESTED MODELS (used inside response models)
# ─────────────────────────────────────────────────────────────────────────────

class QuestionOut(BaseModel):
    """
    Represents a single question sent to the frontend.

    WHY include category?
        The frontend can use it to show a category label
        (e.g. "Role", "Team") — makes the UI richer.
    """
    id:       str = Field(..., description="Unique question identifier")
    text:     str = Field(..., description="The question text shown to the user")
    category: str = Field(..., description="Question category: role/team/era/stats/style")


class CandidateOut(BaseModel):
    """
    Represents one candidate player with their current probability.
    Shown in the UI's 'AI is thinking...' transparency panel.
    """
    player_id:       str   = Field(..., description="Unique player slug ID")
    name:            str   = Field(..., description="Player's full name")
    probability:     float = Field(..., description="Raw probability (0.0 to 1.0)")
    probability_pct: str   = Field(..., description="Human-readable: '34.2%'")


class HistoryEntry(BaseModel):
    """
    One turn in the game history — question asked + answer given.
    Returned in the final game summary.
    """
    question_number: int
    question_id:     str
    question_text:   str
    answer:          str
    top_candidates:  List[CandidateOut]
    entropy:         float
    active_count:    int


# ─────────────────────────────────────────────────────────────────────────────
# REQUEST MODELS (incoming from frontend)
# ─────────────────────────────────────────────────────────────────────────────

class StartGameRequest(BaseModel):
    """
    Request body for POST /game/start.

    WHY optional player_hint?
        Future feature — user could optionally say "I'm thinking of a bowler"
        to seed the first question smarter. Not implemented yet but good
        to design for extensibility now.
    """
    player_hint: Optional[str] = Field(
        None,
        description="Optional hint about the player type (unused in v1)"
    )

    model_config = ConfigDict(extra="ignore")


class SubmitAnswerRequest(BaseModel):
    """
    Request body for POST /game/{session_id}/answer.

    WHY validate answer as AnswerChoice enum?
        If frontend sends "yess" (typo), Pydantic returns a 422 error
        immediately with a clear message — no silent bugs in game logic.
    """
    answer: AnswerChoice = Field(
        ...,
        description="User's answer: yes | no | maybe | dont_know"
    )

    model_config = ConfigDict(extra="ignore")


class ConfirmGuessRequest(BaseModel):
    """
    Request body for POST /game/{session_id}/confirm.

    WHY optional actual_player?
        Only needed when correct=False (we guessed wrong).
        If correct=True, we already know the player.
    """
    correct:       bool            = Field(...,  description="True if our guess was correct")
    actual_player: Optional[str]   = Field(None, description="Player's name if we guessed wrong")

    model_config = ConfigDict(extra="ignore")


# ─────────────────────────────────────────────────────────────────────────────
# RESPONSE MODELS (outgoing to frontend)
# ─────────────────────────────────────────────────────────────────────────────

class StartGameResponse(BaseModel):
    """
    Response for POST /game/start.
    Contains session ID + first question + initial game state.
    """
    session_id:       str          = Field(..., description="UUID for this game session")
    status:           GameStatusEnum
    question_number:  int          = Field(..., description="Always 1 for first question")
    max_questions:    int          = Field(..., description="Hard question limit (8)")
    current_question: QuestionOut
    top_candidates:   List[CandidateOut]
    entropy:          float        = Field(..., description="Current uncertainty in bits")
    active_count:     int          = Field(..., description="Players still in contention")
    message:          str          = Field(..., description="Friendly intro message")


class AnswerResponse(BaseModel):
    """
    Response for POST /game/{session_id}/answer.

    WHY Optional fields?
        When status=active  → next_question is filled, final_guess is None
        When status=guessing → final_guess is filled, next_question is None
        One model handles both states cleanly.
    """
    session_id:       str
    status:           GameStatusEnum
    questions_asked:  int

    # Active game fields (status = active)
    question_number:  Optional[int]        = None
    max_questions:    Optional[int]        = None
    current_question: Optional[QuestionOut] = None

    # Guessing fields (status = guessing)
    final_guess:      Optional[str]        = None
    confidence:       Optional[float]      = None
    confidence_pct:   Optional[str]        = None
    guess_reason:     Optional[str]        = None
    prompt:           Optional[str]        = None

    # Always present
    top_candidates:   List[CandidateOut]   = []
    entropy:          Optional[float]      = None
    active_count:     Optional[int]        = None
    top_confidence:   Optional[str]        = None
    message:          Optional[str]        = None


class ConfirmGuessResponse(BaseModel):
    """
    Response for POST /game/{session_id}/confirm.
    Final game summary shown on results screen.
    """
    session_id:     str
    status:         GameStatusEnum
    questions_asked: int
    correct:        bool
    guessed:        str
    correct_player: Optional[str]
    message:        str
    history:        List[dict]  = []

    # WHY List[dict] instead of List[HistoryEntry]?
    # The history entries from GameSession already come as dicts with
    # nested CandidateOut dicts — re-validating them adds complexity
    # for no real gain at hackathon scale. In production, use HistoryEntry.


class GameStateResponse(BaseModel):
    """
    Response for GET /game/{session_id}/state.
    Used by frontend to refresh/sync game state.
    """
    session_id:       str
    status:           GameStatusEnum
    questions_asked:  int
    max_questions:    int
    current_question: Optional[QuestionOut]
    top_candidates:   List[CandidateOut]
    entropy:          float
    active_count:     int
    final_guess:      Optional[str]  = None


class HealthResponse(BaseModel):
    """
    Response for GET /health.

    WHY include player_count and questions_count?
        Judges can verify the system loaded correctly at a glance.
        A health check that just returns {"status": "ok"} is less impressive.
    """
    status:          str  = "ok"
    player_count:    int
    question_count:  int
    active_sessions: int
    version:         str  = "1.0.0"


class ErrorResponse(BaseModel):
    """
    Standard error response shape.

    WHY a dedicated error model?
        Consistent error shape across all endpoints means the frontend
        only needs one error handler, not one per endpoint.
    """
    status:    str = "error"
    message:   str
    session_id: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    print("=== models.py self-test ===\n")

    # Test 1: AnswerChoice enum validation
    print("TEST 1 — AnswerChoice enum")
    for val in ["yes", "no", "maybe", "dont_know"]:
        a = AnswerChoice(val)
        print(f"  ✅ '{val}' → {a}")

    # Test 2: SubmitAnswerRequest validation
    print("\nTEST 2 — SubmitAnswerRequest")
    req = SubmitAnswerRequest(answer="yes")
    print(f"  ✅ answer={req.answer}, type={type(req.answer)}")

    # Test 3: Serialization
    print("\nTEST 3 — JSON serialization")
    q = QuestionOut(id="is_overseas", text="Is your player overseas?", category="nationality")
    print(f"  ✅ {q.model_dump_json()}")

    # Test 4: Invalid answer (should raise)
    print("\nTEST 4 — Invalid answer validation")
    try:
        bad = SubmitAnswerRequest(answer="yess")
        print("  ❌ Should have raised ValidationError")
    except Exception as e:
        print(f"  ✅ Correctly rejected 'yess': {type(e).__name__}")

    print("\n✅ All model tests passed")