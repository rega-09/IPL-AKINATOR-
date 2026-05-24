# firebase/firestore_client.py
# ─────────────────────────────────────────────────────────────────────────────
# WHY THIS FILE?
#   Single point of contact for all Firestore operations.
#   Same graceful degradation pattern as our LLM client:
#   if Firebase isn't configured → game still works, just no cloud persistence.
#
# COLLECTIONS:
#   sessions/   → one document per completed game
#   learning/   → aggregated failure patterns per player
#   insights/   → LLM-generated improvement notes
# ─────────────────────────────────────────────────────────────────────────────

import os
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

load_dotenv()

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("[WARNING] firebase-admin not installed. Run: pip install firebase-admin")


# ─────────────────────────────────────────────────────────────────────────────
# CLIENT CLASS
# ─────────────────────────────────────────────────────────────────────────────

class FirestoreClient:
    """
    Wrapper around Firebase Admin SDK for Firestore operations.

    WHY a wrapper?
        Same reason as GeminiClient — one place to handle init,
        errors, and fallbacks. Routes.py never touches Firebase directly.
    """

    def __init__(self):
        self.available = False
        self.db        = None

        if not FIREBASE_AVAILABLE:
            print("[Firebase] firebase-admin not installed — cloud storage disabled")
            return

        try:
            # WHY check if already initialized?
            #   FastAPI reloads modules — initializing twice raises an error.
            if firebase_admin._apps:
                self.db        = firestore.client()
                self.available = True
                return

            # OPTION 1: Credentials JSON as environment variable (Render/cloud)
            # WHY? On cloud platforms, we can't commit secret files.
            # Store the entire JSON content as FIREBASE_CREDENTIALS_JSON env var.
            creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
            if creds_json:
                import json as _json
                creds_dict = _json.loads(creds_json)
                cred = credentials.Certificate(creds_dict)
                firebase_admin.initialize_app(cred)

            else:
                # OPTION 2: Credentials file path (local development)
                creds_path = os.getenv(
                    "FIREBASE_CREDENTIALS",
                    "firebase/serviceAccountKey.json"
                )
                if not os.path.isabs(creds_path):
                    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    creds_path   = os.path.join(project_root, creds_path)

                if not os.path.exists(creds_path):
                    print(
                        f"[Firebase] Credentials not found. "
                        "Set FIREBASE_CREDENTIALS_JSON env var (cloud) "
                        "or place serviceAccountKey.json locally. "
                        "See firebase/setup_firebase.md"
                    )
                    return

                cred = credentials.Certificate(creds_path)
                firebase_admin.initialize_app(cred)

            self.db        = firestore.client()
            self.available = True
            print("[Firebase] ✅ Firestore connected")

        except Exception as e:
            print(f"[Firebase] Connection failed: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # SESSION OPERATIONS
    # ─────────────────────────────────────────────────────────────────────────

    def save_session(self, session_data: Dict) -> bool:
        """
        Saves a completed game session to Firestore.

        Collection: sessions/{session_id}

        WHY save every session?
            Every game — win or loss — is training data.
            Wins confirm good questions. Losses reveal gaps.

        Returns True on success, False on failure.
        """
        if not self.available:
            return False

        try:
            session_id = session_data.get("session_id", "unknown")

            # Firestore can't store nested arrays of dicts cleanly
            # Serialize history to JSON string for storage
            doc_data = {
                "session_id":     session_id,
                "started_at":     session_data.get("started_at", ""),
                "ended_at":       datetime.now(timezone.utc).isoformat(),
                "questions_asked": session_data.get("questions_asked", 0),
                "final_guess":    session_data.get("final_guess", ""),
                "correct_player": session_data.get("correct_player", ""),
                "correct":        session_data.get("correct", False),
                # Store history as JSON string — preserves full structure
                "history_json":   json.dumps(session_data.get("history", [])),
                "created_at":     firestore.SERVER_TIMESTAMP,
            }

            self.db.collection("sessions").document(session_id).set(doc_data)
            return True

        except Exception as e:
            print(f"[Firebase] save_session failed: {e}")
            return False

    def get_recent_sessions(self, limit: int = 50) -> List[Dict]:
        """
        Fetches recent completed sessions for learning analysis.

        WHY limit 50?
            Enough to find patterns without overwhelming the LLM context.
        """
        if not self.available:
            return []

        try:
            docs = (
                self.db.collection("sessions")
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
                .stream()
            )
            return [doc.to_dict() for doc in docs]

        except Exception as e:
            print(f"[Firebase] get_recent_sessions failed: {e}")
            return []

    # ─────────────────────────────────────────────────────────────────────────
    # LEARNING OPERATIONS
    # ─────────────────────────────────────────────────────────────────────────

    def record_failure(self, wrong_guess: str, correct_player: str, history: List[Dict]) -> bool:
        """
        Records a wrong guess for learning purposes.

        Collection: learning/{correct_player_slug}

        WHY track per correct_player?
            The learning system needs to know: "which players do we keep
            getting wrong?" and "what questions failed to identify them?"
            Grouping by correct_player makes this lookup O(1).
        """
        if not self.available:
            return False

        try:
            from utils.helpers import slugify
            player_id  = slugify(correct_player)
            doc_ref    = self.db.collection("learning").document(player_id)
            doc        = doc_ref.get()

            # Extract which questions were asked (for pattern analysis)
            questions_asked = [
                {"q": h.get("question_text", ""), "a": h.get("answer", "")}
                for h in history
            ]

            if doc.exists:
                # Update existing record — increment miss count
                existing = doc.to_dict()
                miss_count = existing.get("miss_count", 0) + 1

                # Keep last 10 failure patterns
                failure_patterns = existing.get("failure_patterns", [])
                failure_patterns.append({
                    "wrong_guess":     wrong_guess,
                    "questions_asked": questions_asked,
                    "timestamp":       datetime.now(timezone.utc).isoformat(),
                })
                failure_patterns = failure_patterns[-10:]  # Keep last 10

                doc_ref.update({
                    "miss_count":       miss_count,
                    "failure_patterns": failure_patterns,
                    "last_missed_at":   firestore.SERVER_TIMESTAMP,
                })
            else:
                # First time we've missed this player
                doc_ref.set({
                    "player_id":        player_id,
                    "player_name":      correct_player,
                    "miss_count":       1,
                    "failure_patterns": [{
                        "wrong_guess":     wrong_guess,
                        "questions_asked": questions_asked,
                        "timestamp":       datetime.now(timezone.utc).isoformat(),
                    }],
                    "last_missed_at":   firestore.SERVER_TIMESTAMP,
                    "created_at":       firestore.SERVER_TIMESTAMP,
                })

            return True

        except Exception as e:
            print(f"[Firebase] record_failure failed: {e}")
            return False

    def get_frequent_failures(self, min_misses: int = 2) -> List[Dict]:
        """
        Returns players we've missed more than min_misses times.
        These are the players the learning system should focus on.
        """
        if not self.available:
            return []

        try:
            docs = (
                self.db.collection("learning")
                .where("miss_count", ">=", min_misses)
                .order_by("miss_count", direction=firestore.Query.DESCENDING)
                .limit(20)
                .stream()
            )
            return [doc.to_dict() for doc in docs]

        except Exception as e:
            print(f"[Firebase] get_frequent_failures failed: {e}")
            return []

    def save_insight(self, player_id: str, player_name: str, insight_text: str) -> bool:
        """
        Saves an LLM-generated insight about how to better identify a player.

        Collection: insights/{player_id}

        WHY store insights separately?
            Insights are expensive (LLM calls). We generate them once
            per player and reuse them across many sessions.
        """
        if not self.available:
            return False

        try:
            self.db.collection("insights").document(player_id).set({
                "player_id":    player_id,
                "player_name":  player_name,
                "insight_text": insight_text,
                "generated_at": firestore.SERVER_TIMESTAMP,
            })
            return True

        except Exception as e:
            print(f"[Firebase] save_insight failed: {e}")
            return False

    def get_insights(self) -> Dict[str, str]:
        """
        Returns all stored player insights as {player_id: insight_text}.
        Loaded at session start to improve question generation.
        """
        if not self.available:
            return {}

        try:
            docs = self.db.collection("insights").stream()
            return {
                doc.id: doc.to_dict().get("insight_text", "")
                for doc in docs
            }

        except Exception as e:
            print(f"[Firebase] get_insights failed: {e}")
            return {}

    # ─────────────────────────────────────────────────────────────────────────
    # STATS (for health endpoint)
    # ─────────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict:
        """
        Returns aggregate stats shown in the /health endpoint.
        Judges love seeing live numbers during the demo.
        """
        if not self.available:
            return {"firebase": "disabled"}

        try:
            total_sessions  = len(list(self.db.collection("sessions").limit(500).stream()))
            correct_sessions = len(list(
                self.db.collection("sessions").where("correct", "==", True).limit(500).stream()
            ))
            total_failures  = len(list(self.db.collection("learning").stream()))
            accuracy = (correct_sessions / total_sessions * 100) if total_sessions > 0 else 0

            return {
                "firebase":       "connected",
                "total_sessions": total_sessions,
                "correct_guesses": correct_sessions,
                "accuracy_pct":   round(accuracy, 1),
                "players_learned": total_failures,
            }

        except Exception as e:
            return {"firebase": "error", "detail": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# MODULE-LEVEL SINGLETON
# ─────────────────────────────────────────────────────────────────────────────

db = FirestoreClient()


# ─────────────────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")

    print("=== firestore_client.py self-test ===\n")
    print(f"Firebase available: {db.available}")

    if not db.available:
        print("\n⚠️  Firebase not configured.")
        print("Follow setup_firebase.md to connect.")
        print("Game works without it — Firestore is persistence layer only.")
    else:
        print("\nTEST 1 — Save session")
        result = db.save_session({
            "session_id":     "test-session-001",
            "questions_asked": 6,
            "final_guess":    "MS Dhoni",
            "correct_player": "MS Dhoni",
            "correct":        True,
            "history":        [{"question_text": "Is your player Indian?", "answer": "yes"}],
        })
        print(f"  Saved: {result}")

        print("\nTEST 2 — Record failure")
        result = db.record_failure(
            wrong_guess    = "MS Dhoni",
            correct_player = "Dinesh Karthik",
            history        = [{"question_text": "Is your player a wicketkeeper?", "answer": "yes"}],
        )
        print(f"  Recorded: {result}")

        print("\nTEST 3 — Get stats")
        stats = db.get_stats()
        print(f"  Stats: {stats}")

        print("\n✅ Firestore tests complete")