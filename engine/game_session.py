# engine/game_session.py
# ─────────────────────────────────────────────────────────────────────────────
# WHY THIS FILE EXISTS:
#   The probability engine is pure math — it knows nothing about game rules.
#   The question bank is pure data — it knows nothing about sessions.
#
#   game_session.py is the ORCHESTRATOR. It:
#     - Owns one CandidatePool per game
#     - Enforces the 8-question limit
#     - Decides: ask another question OR make a final guess
#     - Tracks full game history (for the learning system later)
#     - Produces clean response objects the FastAPI layer can serve
#
# ONE SESSION = ONE GAME
#   Each time a user starts a new game, a new GameSession is created.
#   Sessions are identified by a unique session_id (UUID).
# ─────────────────────────────────────────────────────────────────────────────

import uuid
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.probability_engine import CandidatePool
from engine.question_bank import Answer, QUESTION_BANK, get_question


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

MAX_QUESTIONS       = int(os.getenv("MAX_QUESTIONS", 8))        # Hard limit from brief
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.80))  # 80% to guess
DATASET_PATH        = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "processed", "players.json"
)


# ─────────────────────────────────────────────────────────────────────────────
# GAME STATUS ENUM (as string constants — no import needed)
# ─────────────────────────────────────────────────────────────────────────────

class GameStatus:
    ACTIVE    = "active"      # Game in progress — next question ready
    GUESSING  = "guessing"    # Confidence reached — making final guess
    FINISHED  = "finished"    # Game over (correct / incorrect guess confirmed)
    MAXED_OUT = "maxed_out"   # Hit 8-question limit — forced best guess


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: Load player dataset
# ─────────────────────────────────────────────────────────────────────────────

def load_players() -> List[Dict]:
    """
    Loads the player dataset from disk.

    WHY load every session and not once at startup?
        For a hackathon, simplicity wins. In production you'd cache this
        in memory at startup. For now, loading per session is fine —
        the file is small (~100KB) and fast to read.
    """
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(
            f"Player dataset not found at {DATASET_PATH}. "
            "Run scraper/dataset_builder.py first."
        )
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# CLASS: GameSession
# ─────────────────────────────────────────────────────────────────────────────

class GameSession:
    """
    Manages one complete IPL Akinator game.

    Lifecycle:
        1. GameSession()          → initializes pool, picks first question
        2. submit_answer(answer)  → updates pool, picks next question or guesses
        3. confirm_guess(correct) → records outcome, triggers learning if wrong
        4. to_dict() / from_dict  → serialize for API sessions

    Attributes:
        session_id      : Unique UUID for this game
        pool            : CandidatePool with all player probability scores
        status          : Current GameStatus string
        question_count  : How many questions have been asked so far
        current_question: The question currently awaiting an answer
        history         : List of { question, answer, top_candidates } per turn
        final_guess     : Player name the system guessed (when status=GUESSING)
        correct_player  : Actual player (filled in after user confirms/denies)
        started_at      : ISO timestamp of game start
    """

    def __init__(self):
        self.session_id       = str(uuid.uuid4())
        self.players          = load_players()
        self.pool             = CandidatePool(self.players)
        self.status           = GameStatus.ACTIVE
        self.question_count   = 0
        self.current_question = None
        self.history          : List[Dict] = []
        self.final_guess      = None
        self.correct_player   = None
        self.started_at       = datetime.now(timezone.utc).isoformat()

        # Pick the first question immediately on creation
        self.current_question = self._pick_next_question()

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE: Pick the next best question
    # ─────────────────────────────────────────────────────────────────────────

    def _pick_next_question(self) -> Optional[Dict]:
        """
        Asks the probability engine to select the best next question.

        Returns a clean question dict (id + text) or None if no good
        questions remain.

        WHY return only id + text?
            The scorer function (lambda) inside the full question dict is not
            JSON-serializable. We strip it here for clean API responses.
        """
        best = self.pool.select_best_question()
        if best is None:
            return None

        # Return only serializable fields (no scorer lambda)
        return {
            "id":       best["id"],
            "text":     best["text"],
            "category": best["category"],
        }

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC: Submit an answer to the current question
    # ─────────────────────────────────────────────────────────────────────────

    def submit_answer(self, answer_str: str) -> Dict:
        """
        Processes the user's answer, updates the pool, and determines next step.

        Args:
            answer_str : One of "yes", "no", "maybe", "dont_know"

        Returns:
            A response dict describing the new game state:
            {
                session_id, status, question_number,
                next_question OR final_guess,
                top_candidates, entropy, active_count
            }

        WHY return top_candidates in every response?
            Useful for a debug/transparency panel in the UI — shows users
            (and judges) that the AI is genuinely reasoning probabilistically.
        """

        # ── Validate answer ──────────────────────────────────────────────────
        answer = self._parse_answer(answer_str)
        if answer is None:
            return self._error_response(f"Invalid answer: '{answer_str}'. Use yes/no/maybe/dont_know")

        # ── Validate game state ──────────────────────────────────────────────
        if self.status != GameStatus.ACTIVE:
            return self._error_response(f"Game is not active. Current status: {self.status}")

        if self.current_question is None:
            return self._error_response("No current question. Game may be in an invalid state.")

        # ── Apply Bayesian update ────────────────────────────────────────────
        question_id = self.current_question["id"]
        self.pool.update(question_id, answer)
        self.question_count += 1

        # ── Record history ───────────────────────────────────────────────────
        self.history.append({
            "question_number": self.question_count,
            "question_id":     question_id,
            "question_text":   self.current_question["text"],
            "answer":          answer.value,
            "top_candidates":  self.pool.get_top_candidates(3),
            "entropy":         round(self.pool.entropy(), 4),
            "active_count":    self.pool.get_active_candidate_count(),
        })

        # ── Determine next state ─────────────────────────────────────────────
        top_name, confidence = self.pool.get_confidence()

        # Condition 1: Confidence threshold reached → GUESS
        if self.pool.should_guess(CONFIDENCE_THRESHOLD):
            return self._make_guess(top_name, confidence, reason="confidence_reached")

        # Condition 2: Hit maximum question limit → FORCED GUESS
        if self.question_count >= MAX_QUESTIONS:
            return self._make_guess(top_name, confidence, reason="max_questions_reached")

        # Condition 3: No more useful questions → FORCED GUESS
        next_q = self._pick_next_question()
        if next_q is None:
            return self._make_guess(top_name, confidence, reason="no_useful_questions")

        # Condition 4: Continue asking
        self.current_question = next_q
        return self._active_response()

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE: Make a final guess
    # ─────────────────────────────────────────────────────────────────────────

    def _make_guess(self, player_name: str, confidence: float, reason: str) -> Dict:
        """
        Transitions game to GUESSING state and returns the final guess.

        WHY store reason?
            Distinguishes "confident guess" (≥80%) from "forced guess" (8 Qs).
            Useful for the learning system — forced guesses have different
            failure patterns than confident guesses.
        """
        self.status       = GameStatus.GUESSING
        self.final_guess  = player_name

        top_candidates = self.pool.get_top_candidates(3)

        return {
            "session_id":       self.session_id,
            "status":           self.status,
            "questions_asked":  self.question_count,
            "final_guess":      player_name,
            "confidence":       round(confidence, 4),
            "confidence_pct":   f"{confidence * 100:.1f}%",
            "guess_reason":     reason,
            "top_candidates":   top_candidates,
            "message":          f"I think your player is {player_name}! "
                                f"(Confidence: {confidence * 100:.1f}%)",
            "prompt":           "Am I right? (yes / no)"
        }

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC: Confirm whether the guess was correct
    # ─────────────────────────────────────────────────────────────────────────

    def confirm_guess(self, correct: bool, actual_player: Optional[str] = None) -> Dict:
        """
        Called after the user tells us if our guess was right or wrong.

        Args:
            correct        : True if we guessed correctly
            actual_player  : The player's name if we were wrong (for learning)

        Returns:
            Final game summary dict.

        WHY record correct_player even on success?
            The learning system uses session outcomes to improve.
            On correct guess: correct_player = final_guess.
            On wrong guess: correct_player = what user tells us.
        """
        if self.status != GameStatus.GUESSING:
            return self._error_response("Game is not in guessing state.")

        self.status = GameStatus.FINISHED
        self.correct_player = self.final_guess if correct else actual_player

        result = {
            "session_id":       self.session_id,
            "status":           self.status,
            "questions_asked":  self.question_count,
            "correct":          correct,
            "guessed":          self.final_guess,
            "correct_player":   self.correct_player,
            "history":          self.history,
            "message": (
                f"🎉 Yes! I knew it was {self.final_guess}!"
                if correct else
                f"😅 Oops! I'll remember that {self.correct_player} for next time."
            )
        }

        # Save session for learning system
        self._save_session_log()

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE: Build active game response
    # ─────────────────────────────────────────────────────────────────────────

    def _active_response(self) -> Dict:
        """
        Builds the response dict for an in-progress game (next question ready).
        """
        _, confidence = self.pool.get_confidence()

        return {
            "session_id":       self.session_id,
            "status":           self.status,
            "question_number":  self.question_count + 1,
            "questions_asked":  self.question_count,
            "max_questions":    MAX_QUESTIONS,
            "current_question": self.current_question,
            "top_candidates":   self.pool.get_top_candidates(3),
            "entropy":          round(self.pool.entropy(), 4),
            "active_count":     self.pool.get_active_candidate_count(),
            "top_confidence":   f"{confidence * 100:.1f}%",
        }

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE: Parse answer string to Answer enum
    # ─────────────────────────────────────────────────────────────────────────

    def _parse_answer(self, answer_str: str) -> Optional[Answer]:
        """
        Converts user input string to Answer enum.

        WHY flexible parsing?
            Users might type "Yes", "YES", "y", "yeah" — we handle common variants.
        """
        normalized = answer_str.strip().lower()

        mapping = {
            "yes":        Answer.YES,
            "y":          Answer.YES,
            "yeah":       Answer.YES,
            "yep":        Answer.YES,
            "no":         Answer.NO,
            "n":          Answer.NO,
            "nope":       Answer.NO,
            "nah":        Answer.NO,
            "maybe":      Answer.MAYBE,
            "sort of":    Answer.MAYBE,
            "kind of":    Answer.MAYBE,
            "dont_know":  Answer.DONT_KNOW,
            "don't know": Answer.DONT_KNOW,
            "idk":        Answer.DONT_KNOW,
            "not sure":   Answer.DONT_KNOW,
        }
        return mapping.get(normalized)

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE: Error response
    # ─────────────────────────────────────────────────────────────────────────

    def _error_response(self, message: str) -> Dict:
        return {
            "session_id": self.session_id,
            "status":     "error",
            "message":    message,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE: Save session log for learning system
    # ─────────────────────────────────────────────────────────────────────────

    def _save_session_log(self) -> None:
        """
        Saves the completed session to disk for the learning system.

        WHY save to disk and not a DB?
            Simple and fast for hackathon. The learning system reads these files
            to build a history of past games and improve future sessions.

        File: data/sessions/{session_id}.json
        """
        sessions_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "sessions"
        )
        os.makedirs(sessions_dir, exist_ok=True)

        log = {
            "session_id":     self.session_id,
            "started_at":     self.started_at,
            "ended_at":       datetime.now(timezone.utc).isoformat(),
            "questions_asked": self.question_count,
            "final_guess":    self.final_guess,
            "correct_player": self.correct_player,
            "correct":        self.final_guess == self.correct_player,
            "history":        self.history,
        }

        path = os.path.join(sessions_dir, f"{self.session_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2)

    # ─────────────────────────────────────────────────────────────────────────
    # SERIALIZATION
    # ─────────────────────────────────────────────────────────────────────────

    def to_dict(self) -> Dict:
        """Serialize session state for storage between API requests."""
        return {
            "session_id":        self.session_id,
            "status":            self.status,
            "question_count":    self.question_count,
            "current_question":  self.current_question,
            "history":           self.history,
            "final_guess":       self.final_guess,
            "correct_player":    self.correct_player,
            "started_at":        self.started_at,
            "pool_state":        self.pool.to_dict(),
        }

    @classmethod
    def from_dict(cls, state: Dict) -> "GameSession":
        """
        Restores a GameSession from a serialized dict.
        WHY classmethod?
            It's a factory — creates a new instance from saved data
            without needing an existing instance first.
        """
        session = cls.__new__(cls)           # Create instance without __init__
        session.players          = load_players()
        session.pool             = CandidatePool(session.players)
        session.pool.from_dict(state["pool_state"])
        session.session_id       = state["session_id"]
        session.status           = state["status"]
        session.question_count   = state["question_count"]
        session.current_question = state["current_question"]
        session.history          = state["history"]
        session.final_guess      = state["final_guess"]
        session.correct_player   = state["correct_player"]
        session.started_at       = state["started_at"]
        return session


# ─────────────────────────────────────────────────────────────────────────────
# FULL GAME SIMULATION (self-test)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pprint

    print("="*60)
    print("GAME SESSION SIMULATION — Target: Jasprit Bumrah")
    print("="*60)

    session = GameSession()
    print(f"\nSession ID : {session.session_id}")
    print(f"First Q    : {session.current_question['text']}\n")

    # Simulate answers for Jasprit Bumrah:
    # Indian, pure bowler, pace, MI, active, taken 100+ wickets, veteran
    simulation = [
        # (question_id_expected, answer_to_give)
        # We answer based on Bumrah's profile regardless of question order
        # The engine picks questions dynamically — we respond based on content
    ]

    # Answer map: for any question, what would Bumrah answer?
    bumrah_answers = {
        "is_overseas":         "no",
        "is_indian":           "yes",
        "is_pure_bowler":      "yes",
        "is_batsman":          "no",
        "is_allrounder":       "no",
        "is_wicketkeeper":     "no",
        "bowls_spin":          "no",
        "bowls_pace":          "yes",
        "left_hand_bat":       "no",
        "left_arm_bowl":       "no",
        "is_opener":           "no",
        "is_finisher":         "no",
        "is_middle_order":     "no",
        "played_for_csk":      "no",
        "played_for_mi":       "yes",
        "played_for_rcb":      "no",
        "played_for_kkr":      "no",
        "played_for_srh":      "no",
        "played_for_rr":       "no",
        "played_for_dc":       "no",
        "played_for_pbks":     "no",
        "played_for_gt":       "no",
        "played_for_lsg":      "no",
        "one_team_only":       "yes",
        "multiple_teams":      "no",
        "has_captained":       "yes",
        "won_ipl_title":       "yes",
        "won_multiple_titles": "yes",
        "won_orange_cap":      "no",
        "won_purple_cap":      "no",
        "won_any_cap":         "no",
        "is_active":           "yes",
        "is_veteran":          "no",
        "long_career":         "yes",
        "recent_player":       "no",
        "scored_4000_runs":    "no",
        "scored_2000_runs":    "no",
        "taken_100_wickets":   "yes",
        "taken_150_wickets":   "yes",
        "played_100_matches":  "yes",
        "played_200_matches":  "no",
        "known_power_hitter":  "no",
        "known_death_bowling": "yes",
        "known_economy":       "yes",
        "known_captaincy":     "no",
        "high_profile":        "yes",
        "is_australian":       "no",
        "is_west_indian":      "no",
        "is_south_african":    "no",
        "is_english":          "no",
        "is_sri_lankan":       "no",
        "is_afghan":           "no",
        "is_kiwi":             "no",
    }

    print(f"{'Q#':<4} {'Question':<55} {'Answer':<10} {'Top Guess':<25} {'Conf':>6}  {'Active':>6}")
    print("-"*115)

    for turn in range(MAX_QUESTIONS + 1):
        if session.status != GameStatus.ACTIVE:
            break

        q = session.current_question
        qid = q["id"]

        # Get appropriate answer for Bumrah
        answer = bumrah_answers.get(qid, "dont_know")

        # Get top candidate before answering
        top_name, conf = session.pool.get_confidence()

        print(f"{turn+1:<4} {q['text'][:54]:<55} {answer:<10} {top_name:<25} {conf*100:>5.1f}%  {session.pool.get_active_candidate_count():>6}")

        response = session.submit_answer(answer)

        if response["status"] == GameStatus.GUESSING:
            print(f"\n{'─'*115}")
            print(f"🎯 FINAL GUESS: {response['final_guess']}")
            print(f"   Confidence : {response['confidence_pct']}")
            print(f"   Reason     : {response['guess_reason']}")
            print(f"   Questions  : {response['questions_asked']}")
            break

    # Confirm correct
    if session.status == GameStatus.GUESSING:
        result = session.confirm_guess(
            correct=session.final_guess == "Jasprit Bumrah",
            actual_player="Jasprit Bumrah"
        )
        print(f"\n{result['message']}")
        print(f"Session log saved ✅")