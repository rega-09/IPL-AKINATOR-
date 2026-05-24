# engine/probability_engine.py
# ─────────────────────────────────────────────────────────────────────────────
# THE CORE AI BRAIN
#
# This file implements:
#   1. CandidatePool  — tracks all players + their current probability scores
#   2. Bayesian update — adjusts scores after each answer
#   3. Entropy calculation — measures current uncertainty
#   4. Information gain — finds the best next question
#   5. Confidence check — decides when to guess
#
# Nothing in this file knows about the game UI, the API, or the session.
# It is pure probability logic — inputs are players + answers, output is math.
# ─────────────────────────────────────────────────────────────────────────────

import math
import json
import os

from typing import Dict, List, Tuple, Optional
from engine.question_bank import (
    Answer, LIKELIHOOD, QUESTION_BANK,
    compute_player_fit, get_question
)


# ─────────────────────────────────────────────────────────────────────────────
# CLASS: CandidatePool
# ─────────────────────────────────────────────────────────────────────────────

class CandidatePool:
    """
    Maintains the probability distribution over all IPL players.

    WHY a class and not standalone functions?
        The pool has STATE — probability scores change over time.
        A class bundles the data (scores) with the operations (update, rank).
        This makes it easy to serialize/deserialize for session management.

    Attributes:
        players     : List of all player dicts (from players.json)
        scores      : Dict mapping player_id → current probability score
                      (raw scores, not yet normalized to sum to 1.0)
        asked_ids   : Set of question IDs already asked (never repeat)
        update_log  : History of (question_id, answer, score_snapshot) for debugging
    """

    def __init__(self, players: List[Dict]):
        """
        Initialize with equal probability for every player.

        WHY equal initialization?
            Before any question, we have zero information — all players are
            equally likely. This is the principle of maximum entropy initialization.
        """
        self.players = players

        # Initialize all scores to 1.0 (equal weight)
        # WHY 1.0 and not 1/N?
        #   We work with unnormalized scores for numerical stability.
        #   We normalize only when we need actual probabilities (for display/guessing).
        #   This avoids floating-point underflow when multiplying many small numbers.
        self.scores: Dict[str, float] = {
            p["id"]: 1.0 for p in players
        }

        self.asked_ids: set = set()       # Question IDs already used
        self.update_log: List[Dict] = []  # Audit trail of updates

    # ─────────────────────────────────────────────────────────────────────────
    # CORE METHOD: Bayesian Update
    # ─────────────────────────────────────────────────────────────────────────

    def update(self, question_id: str, answer: Answer) -> None:
        """
        Applies Bayes' theorem to update all player scores given an answer.

        THE MATH:
            new_score[player] = old_score[player] × P(answer | player_fits_or_not)

        Where P(answer | player) comes from LIKELIHOOD table:
            - If player FITS the question's YES condition:
                use LIKELIHOOD[answer]["fits"]
            - If player does NOT fit:
                use LIKELIHOOD[answer]["doesnt"]

        WHY multiply scores instead of replace?
            Multiplication accumulates evidence over multiple questions.
            Each new answer narrows the pool further without hard-deleting anyone.

        Args:
            question_id : ID of the question that was asked
            answer      : The user's Answer enum value
        """
        question = get_question(question_id)
        self.asked_ids.add(question_id)

        # Snapshot scores before update (for logging/debugging)
        pre_scores = dict(self.scores)

        for player in self.players:
            pid = player["id"]
            fits = compute_player_fit(question, player)

            # Select the correct likelihood multiplier
            # fits=True  → player should answer YES → use "fits" multiplier
            # fits=False → player should answer NO  → use "doesnt" multiplier
            multiplier = LIKELIHOOD[answer]["fits"] if fits else LIKELIHOOD[answer]["doesnt"]

            # Apply Bayesian update: multiply current score by likelihood
            self.scores[pid] = self.scores[pid] * multiplier

        # Log this update for transparency
        self.update_log.append({
            "question_id": question_id,
            "question_text": question["text"],
            "answer": answer.value,
            "top_candidates_after": self.get_top_candidates(5),
        })

    # ─────────────────────────────────────────────────────────────────────────
    # CORE METHOD: Normalize scores to probabilities
    # ─────────────────────────────────────────────────────────────────────────

    def get_probabilities(self) -> Dict[str, float]:
        """
        Converts raw scores to normalized probabilities (sum = 1.0).

        WHY normalize?
            Raw scores after many multiplications become very small numbers.
            Normalizing gives us interpretable percentages for display and guessing.

        Returns:
            Dict mapping player_id → probability (0.0 to 1.0)
        """
        total = sum(self.scores.values())

        # Guard against division by zero (shouldn't happen with Laplace smoothing)
        if total == 0:
            n = len(self.scores)
            return {pid: 1.0/n for pid in self.scores}

        return {pid: score / total for pid, score in self.scores.items()}

    # ─────────────────────────────────────────────────────────────────────────
    # CORE METHOD: Entropy calculation
    # ─────────────────────────────────────────────────────────────────────────

    def entropy(self) -> float:
        """
        Calculates Shannon entropy of the current probability distribution.

        FORMULA:
            H = -Σ p(x) × log₂(p(x))

        WHY log base 2?
            Entropy in bits. A 50/50 split = 1 bit of uncertainty.
            Starting entropy for N equal players = log₂(N).
            For 48 players: log₂(48) ≈ 5.58 bits.

        Returns:
            Float — entropy in bits. Lower = more certain.
        """
        probs = self.get_probabilities()
        total = 0.0

        for prob in probs.values():
            if prob > 0:
                # p × log₂(p) — using math.log2 for base-2 logarithm
                total -= prob * math.log2(prob)

        return total

    # ─────────────────────────────────────────────────────────────────────────
    # CORE METHOD: Information Gain
    # ─────────────────────────────────────────────────────────────────────────

    def information_gain(self, question_id: str) -> float:
        """
        Calculates expected information gain from asking a specific question.

        FORMULA:
            IG(Q) = H(current) - E[H(after asking Q)]

        Where E[H(after asking Q)] is the weighted average of entropy across
        all possible answers (YES, NO, MAYBE, DONT_KNOW).

        In practice, we only compute for YES and NO (most common answers),
        weighted by how many players would produce each answer.

        WHY expected entropy and not just "how many players does YES eliminate"?
            Because entropy accounts for the DISTRIBUTION of remaining players,
            not just their count. Eliminating 1 high-probability player is
            more valuable than eliminating 10 low-probability ones.

        Args:
            question_id : ID of the question to evaluate

        Returns:
            Float — information gain in bits. Higher = better question.
        """
        question = get_question(question_id)
        current_entropy = self.entropy()
        probs = self.get_probabilities()

        # Calculate probability that answer will be YES vs NO
        # based on current player probabilities
        # P(YES) = Σ P(player) × P(YES | player)
        p_yes = 0.0
        p_no  = 0.0

        for player in self.players:
            pid = player["id"]
            player_prob = probs[pid]
            fits = compute_player_fit(question, player)

            if fits:
                # This player would answer YES → contributes to P(YES)
                p_yes += player_prob * LIKELIHOOD[Answer.YES]["fits"]
                p_no  += player_prob * LIKELIHOOD[Answer.NO]["fits"]
            else:
                p_yes += player_prob * LIKELIHOOD[Answer.YES]["doesnt"]
                p_no  += player_prob * LIKELIHOOD[Answer.NO]["doesnt"]

        # Normalize (they should roughly sum to 1 already)
        total = p_yes + p_no
        if total == 0:
            return 0.0
        p_yes /= total
        p_no  /= total

        # Calculate entropy if answer were YES
        entropy_if_yes = self._hypothetical_entropy(question_id, Answer.YES)

        # Calculate entropy if answer were NO
        entropy_if_no  = self._hypothetical_entropy(question_id, Answer.NO)

        # Expected entropy = weighted average
        expected_entropy = p_yes * entropy_if_yes + p_no * entropy_if_no

        # Information gain = how much entropy we LOSE (how much we learn)
        return current_entropy - expected_entropy

    def _hypothetical_entropy(self, question_id: str, answer: Answer) -> float:
        """
        Calculates what the entropy WOULD BE if we received a specific answer.

        WHY private method (underscore prefix)?
            This is a helper for information_gain() — not meant to be called
            directly from outside the class.

        Args:
            question_id : Question being evaluated
            answer      : Hypothetical answer (YES or NO)

        Returns:
            Float — entropy that would result from this answer
        """
        question = get_question(question_id)

        # Compute hypothetical scores (don't modify self.scores)
        hypo_scores = {}
        for player in self.players:
            pid = player["id"]
            fits = compute_player_fit(question, player)
            multiplier = LIKELIHOOD[answer]["fits"] if fits else LIKELIHOOD[answer]["doesnt"]
            hypo_scores[pid] = self.scores[pid] * multiplier

        # Normalize hypothetical scores
        total = sum(hypo_scores.values())
        if total == 0:
            return 0.0

        hypo_probs = {pid: s / total for pid, s in hypo_scores.items()}

        # Calculate entropy of this hypothetical distribution
        h = 0.0
        for prob in hypo_probs.values():
            if prob > 0:
                h -= prob * math.log2(prob)
        return h

    # ─────────────────────────────────────────────────────────────────────────
    # CORE METHOD: Select best next question
    # ─────────────────────────────────────────────────────────────────────────

    def select_best_question(self) -> Optional[Dict]:
        """
        Improved question selection with 3 fixes:
        1. First question variety (random from top 4)
        2. Decisive question boost (captaincy/WK/finisher boosted when relevant)
        3. Category diversity (penalise repeating same category)
        """
        import random
        available = [q for q in QUESTION_BANK if q["id"] not in self.asked_ids]
        if not available:
            return None

        active_count = self.get_active_candidate_count()
        probs        = self.get_probabilities()

        # Compute IG with adjustments
        scored = []
        for q in available:
            ig = self.information_gain(q["id"])

            # BOOST decisive questions when pool is small
            decisive_ids = {
                "has_captained", "is_wicketkeeper", "is_finisher",
                "won_orange_cap", "won_purple_cap", "won_any_cap",
                "won_ipl_title", "is_death_bowler", "high_profile",
                "is_aggressive_batter", "left_hand_bat", "bowls_spin"
            }
            if q["id"] in decisive_ids and active_count <= 50:
                top_10 = self.get_top_candidates(10)
                top_ids = {c["player_id"] for c in top_10}
                top_players = [p for p in self.players if p["id"] in top_ids]
                fit_count = sum(1 for p in top_players if compute_player_fit(q, p))
                fit_pct = fit_count / max(len(top_players), 1)
                if 0.15 <= fit_pct <= 0.85:
                    ig *= 3.0  # Strong boost

            # PENALISE over-used categories
            asked_qs = [get_question(qid) for qid in self.asked_ids if qid in {q['id'] for q in QUESTION_BANK}]
            same_cat = sum(1 for aq in asked_qs if aq["category"] == q["category"])
            if same_cat >= 2:
                ig *= 0.5

            scored.append((ig, q))

        scored.sort(key=lambda x: x[0], reverse=True)

        # FIRST QUESTION VARIETY: rotate among top 4
        if len(self.asked_ids) == 0:
            top_n   = min(4, len(scored))
            weights = [max(s[0], 0.001) for s in scored[:top_n]]
            total_w = sum(weights)
            weights = [w / total_w for w in weights]
            return random.choices([s[1] for s in scored[:top_n]], weights=weights, k=1)[0]

        best_ig, best_q = scored[0]
        if best_ig < 0.005:
            return None
        return best_q

    # ─────────────────────────────────────────────────────────────────────────
    # CONFIDENCE AND GUESSING
    # ─────────────────────────────────────────────────────────────────────────

    def get_top_candidates(self, n: int = 3) -> List[Dict]:
        """
        Returns the top N players sorted by probability (highest first).

        Returns:
            List of dicts: [{ player_id, name, probability }, ...]
        """
        probs = self.get_probabilities()
        sorted_players = sorted(probs.items(), key=lambda x: x[1], reverse=True)

        # Build result with player names
        player_lookup = {p["id"]: p for p in self.players}
        result = []
        for pid, prob in sorted_players[:n]:
            player = player_lookup.get(pid, {})
            result.append({
                "player_id": pid,
                "name": player.get("name", pid),
                "probability": round(prob, 4),
                "probability_pct": f"{prob * 100:.1f}%",
            })
        return result

    def get_confidence(self) -> Tuple[str, float]:
        """
        Returns the top player and their confidence score.

        Returns:
            Tuple of (player_name, confidence_float)
            e.g. ("MS Dhoni", 0.87)
        """
        top = self.get_top_candidates(1)
        if not top:
            return ("Unknown", 0.0)
        return (top[0]["name"], top[0]["probability"])

    def should_guess(self, threshold: float = 0.80) -> bool:
        """
        Dynamic confidence threshold based on active pool size.

        WHY dynamic?
            With 802 players, even a perfect 8-question game rarely
            concentrates probability above 80% — mathematically impossible
            when 10+ similar players remain.

            Solution: lower threshold proportionally as questions are asked,
            but never below 40% (prevents wild guesses).

        Thresholds:
            Active > 20  → use full 80% (still early, need more info)
            Active 10-20 → 65% (narrowing well)
            Active 5-10  → 55% (small pool, top candidate likely right)
            Active < 5   → 45% (very small pool, go with top)
        """
        _, confidence = self.get_confidence()
        active = self.get_active_candidate_count()

        if active > 20:
            effective_threshold = threshold          # 80% — still broad
        elif active > 10:
            effective_threshold = 0.60               # 60%
        elif active > 5:
            effective_threshold = 0.50               # 50%
        else:
            effective_threshold = 0.40               # 40% — very narrow pool

        return confidence >= effective_threshold

    def get_active_candidate_count(self) -> int:
        """
        Returns the number of players with probability > 1% (effectively active).

        WHY "effective" count and not total?
            After several questions, many players will have near-zero probability
            (e.g. 0.0001%). The "active" count shows how many are truly in the race.
        """
        probs = self.get_probabilities()
        return sum(1 for p in probs.values() if p > 0.001)

    # ─────────────────────────────────────────────────────────────────────────
    # SERIALIZATION (for session persistence)
    # ─────────────────────────────────────────────────────────────────────────

    def to_dict(self) -> Dict:
        """
        Serializes pool state to a JSON-safe dict.
        WHY? FastAPI sessions need to store state between HTTP requests.
        """
        return {
            "scores": self.scores,
            "asked_ids": list(self.asked_ids),
            "update_log": self.update_log,
        }

    def from_dict(self, state: Dict) -> None:
        """
        Restores pool state from a serialized dict.
        WHY? Allows us to resume a game session from saved state.
        """
        self.scores    = state["scores"]
        self.asked_ids = set(state["asked_ids"])
        self.update_log = state.get("update_log", [])


# ─────────────────────────────────────────────────────────────────────────────
# STANDALONE SELF-TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Load the real player dataset
    dataset_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "processed", "players.json"
    )
    with open(dataset_path) as f:
        players = json.load(f)

    print("="*60)
    print("PROBABILITY ENGINE SELF-TEST")
    print("="*60)

    pool = CandidatePool(players)

    print(f"\n[INIT] Players loaded       : {len(players)}")
    print(f"[INIT] Starting entropy     : {pool.entropy():.4f} bits")
    print(f"[INIT] Active candidates    : {pool.get_active_candidate_count()}")

    # ── Test 1: Find best first question ────────────────────────────────────
    print("\n--- TEST 1: Best First Question ---")
    best_q = pool.select_best_question()
    print(f"Best question to ask first : '{best_q['text']}'")
    print(f"Question ID                : {best_q['id']}")
    ig = pool.information_gain(best_q["id"])
    print(f"Information gain           : {ig:.4f} bits")

    # ── Test 2: Simulate answering "Is your player Indian?" → YES ───────────
    print("\n--- TEST 2: Simulate 'Is your player Indian?' → YES ---")
    pool.update("is_indian", Answer.YES)
    print(f"Entropy after update   : {pool.entropy():.4f} bits")
    print(f"Active candidates      : {pool.get_active_candidate_count()}")
    print(f"Top 5 candidates:")
    for c in pool.get_top_candidates(5):
        print(f"  {c['name']:25s} {c['probability_pct']}")

    # ── Test 3: Simulate "Is your player a bowler?" → YES ───────────────────
    print("\n--- TEST 3: Simulate 'Is your player a bowler?' → YES ---")
    pool.update("is_pure_bowler", Answer.YES)
    print(f"Entropy after update   : {pool.entropy():.4f} bits")
    print(f"Active candidates      : {pool.get_active_candidate_count()}")
    print(f"Top 5 candidates:")
    for c in pool.get_top_candidates(5):
        print(f"  {c['name']:25s} {c['probability_pct']}")

    # ── Test 4: Next best question after 2 updates ───────────────────────────
    print("\n--- TEST 4: Next Best Question ---")
    next_q = pool.select_best_question()
    print(f"Next best question : '{next_q['text']}'")

    # ── Test 5: Confidence check ─────────────────────────────────────────────
    print("\n--- TEST 5: Confidence Check ---")
    name, conf = pool.get_confidence()
    print(f"Top candidate   : {name}")
    print(f"Confidence      : {conf*100:.1f}%")
    print(f"Should guess?   : {pool.should_guess()}")

    # ── Test 6: Serialization round-trip ────────────────────────────────────
    print("\n--- TEST 6: Serialization Round-Trip ---")
    state = pool.to_dict()
    pool2 = CandidatePool(players)
    pool2.from_dict(state)
    print(f"Scores match after restore: {pool.scores == pool2.scores}")
    print(f"Asked IDs match           : {pool.asked_ids == pool2.asked_ids}")

    print("\n✅ All engine tests complete")