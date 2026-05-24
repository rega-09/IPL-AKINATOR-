# api/session_store.py
# ─────────────────────────────────────────────────────────────────────────────
# WHY THIS FILE EXISTS:
#   FastAPI handles each HTTP request independently — it has no built-in
#   concept of "this request belongs to the same game as the last one."
#
#   We need a SESSION STORE: a place to keep GameSession objects alive
#   between requests, identified by session_id (UUID).
#
# DESIGN CHOICE — In-Memory Dict:
#   We store sessions in a plain Python dict: { session_id: GameSession }
#   This lives in RAM for the lifetime of the server process.
#
#   WHY not a database?
#     For a hackathon demo, in-memory is:
#       - Zero setup (no DB install, no migrations)
#       - Zero latency (dict lookup is O(1))
#       - Zero complexity (no connection pooling, no ORM)
#     The tradeoff (lost sessions on restart) doesn't matter for a demo.
#
#   WHY not Flask-Session or similar?
#     We don't need cookies or user accounts. Session_id in the URL is
#     simpler and more RESTful for a game API.
#
# THREAD SAFETY NOTE:
#   Python's GIL (Global Interpreter Lock) makes simple dict reads/writes
#   thread-safe enough for a hackathon. In production, you'd use
#   asyncio.Lock() or an external store like Redis.
# ─────────────────────────────────────────────────────────────────────────────

import sys
import os
from typing import Dict, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.game_session import GameSession


# ─────────────────────────────────────────────────────────────────────────────
# THE STORE
# A module-level dict — one instance shared across all requests.
#
# WHY module-level?
#   Python caches imported modules. The first import of session_store.py
#   creates _store = {}. Every subsequent import gets the SAME dict object.
#   This gives us a singleton store without any singleton boilerplate.
# ─────────────────────────────────────────────────────────────────────────────

_store: Dict[str, GameSession] = {}


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API — Functions that routes.py will call
# ─────────────────────────────────────────────────────────────────────────────

def create_session() -> GameSession:
    """
    Creates a new GameSession, stores it, and returns it.

    WHY return the session object and not just the ID?
        The caller (routes.py) needs the session immediately to build
        the response. Returning the full object avoids an immediate
        get_session() call right after create.
    """
    session = GameSession()                    # Initializes pool + first question
    _store[session.session_id] = session       # Store by UUID key
    return session


def get_session(session_id: str) -> Optional[GameSession]:
    """
    Retrieves an existing session by ID.

    Returns None if session doesn't exist (not a crash).
    WHY return None instead of raising?
        routes.py will convert None into a clean 404 HTTP response.
        Raising here would produce an unhandled 500 instead.
    """
    return _store.get(session_id)             # dict.get() returns None if missing


def delete_session(session_id: str) -> bool:
    """
    Removes a finished session from memory.

    WHY delete finished sessions?
        Memory management — a long-running server would leak memory
        if finished sessions accumulate forever.
        For a hackathon, this is optional but good practice.

    Returns True if session existed and was deleted, False otherwise.
    """
    if session_id in _store:
        del _store[session_id]
        return True
    return False


def get_active_count() -> int:
    """
    Returns the number of currently active sessions.
    Used by the /health endpoint so judges can see live usage.
    """
    return len(_store)


def get_all_session_ids() -> list:
    """
    Returns a list of all active session IDs.
    Useful for admin/debug endpoints (not exposed publicly).
    """
    return list(_store.keys())


def session_exists(session_id: str) -> bool:
    """
    Quick existence check without fetching the full object.
    WHY?
        Some routes only need to verify existence before routing logic.
        Avoids unnecessary object retrieval.
    """
    return session_id in _store


# ─────────────────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== session_store.py self-test ===\n")

    # Test 1: Create session
    print("TEST 1 — Create session")
    s1 = create_session()
    print(f"  ✅ Created session: {s1.session_id[:8]}...")
    print(f"  ✅ Active count   : {get_active_count()}")
    print(f"  ✅ First question : {s1.current_question['text'][:50]}...")

    # Test 2: Retrieve session
    print("\nTEST 2 — Retrieve session")
    retrieved = get_session(s1.session_id)
    assert retrieved is s1, "Should be the same object"
    print(f"  ✅ Retrieved same object: {retrieved is s1}")

    # Test 3: Non-existent session returns None
    print("\nTEST 3 — Missing session returns None")
    missing = get_session("non-existent-id")
    assert missing is None
    print(f"  ✅ Missing session returns: {missing}")

    # Test 4: Create multiple sessions
    print("\nTEST 4 — Multiple sessions")
    s2 = create_session()
    s3 = create_session()
    print(f"  ✅ Active sessions: {get_active_count()}")
    assert get_active_count() == 3

    # Test 5: Delete session
    print("\nTEST 5 — Delete session")
    result = delete_session(s1.session_id)
    assert result is True
    assert get_session(s1.session_id) is None
    print(f"  ✅ Deleted: {result}")
    print(f"  ✅ Active after delete: {get_active_count()}")

    # Test 6: session_exists check
    print("\nTEST 6 — session_exists")
    print(f"  ✅ s2 exists: {session_exists(s2.session_id)}")
    print(f"  ✅ s1 exists: {session_exists(s1.session_id)} (deleted)")

    print("\n✅ All session store tests passed")