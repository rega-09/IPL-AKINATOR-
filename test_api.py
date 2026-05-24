# test_api.py  (run from project root while server is running)
# ─────────────────────────────────────────────────────────────────────────────
# WHY THIS FILE?
#   A quick end-to-end test script you can run from the terminal to verify
#   all API endpoints are working correctly WITHOUT needing a browser.
#
# HOW TO USE:
#   1. Start server in one terminal : python run.py
#   2. Run this in another terminal : python test_api.py
# ─────────────────────────────────────────────────────────────────────────────

import requests
import json

BASE_URL = "http://localhost:8000"

def pretty(label: str, response: requests.Response):
    """Print a clean response summary."""
    print(f"\n{'─'*55}")
    print(f"  {label}")
    print(f"  Status : {response.status_code}")
    try:
        data = response.json()
        # Print only key fields — not the full response
        keys_to_show = [
            "status", "session_id", "question_number",
            "final_guess", "confidence_pct", "correct",
            "player_count", "question_count", "active_sessions",
            "message"
        ]
        for k in keys_to_show:
            if k in data:
                print(f"  {k:20s}: {data[k]}")
        if "current_question" in data and data["current_question"]:
            print(f"  {'question':<20}: {data['current_question']['text'][:55]}")
        if "top_candidates" in data:
            print(f"  {'top candidate':<20}: {data['top_candidates'][0]['name']} ({data['top_candidates'][0]['probability_pct']})")
    except Exception as e:
        print(f"  Body   : {response.text[:200]}")

print("="*55)
print("  IPL AKINATOR — API END-TO-END TEST")
print("="*55)

# ── TEST 1: Health check ─────────────────────────────────────
print("\n[1/5] Health Check — GET /health")
r = requests.get(f"{BASE_URL}/health")
pretty("GET /health", r)
assert r.status_code == 200
assert r.json()["status"] == "ok"
print("  ✅ PASSED")

# ── TEST 2: Start game ───────────────────────────────────────
print("\n[2/5] Start Game — POST /game/start")
r = requests.post(f"{BASE_URL}/game/start", json={})
pretty("POST /game/start", r)
assert r.status_code == 201
data     = r.json()
sid      = data["session_id"]
first_q  = data["current_question"]
assert "session_id" in data
assert "current_question" in data
print(f"  ✅ PASSED — session: {sid[:8]}...")

# ── TEST 3: Submit answer ────────────────────────────────────
print("\n[3/5] Submit Answer — POST /game/{id}/answer")
r = requests.post(
    f"{BASE_URL}/game/{sid}/answer",
    json={"answer": "yes"}
)
pretty("POST /game/{id}/answer", r)
assert r.status_code == 200
resp = r.json()
assert resp["status"] in ("active", "guessing")
print(f"  ✅ PASSED — game status: {resp['status']}")

# ── TEST 4: Get state ────────────────────────────────────────
print("\n[4/5] Get State — GET /game/{id}/state")
r = requests.get(f"{BASE_URL}/game/{sid}/state")
pretty("GET /game/{id}/state", r)
assert r.status_code == 200
print("  ✅ PASSED")

# ── TEST 5: Invalid session → 404 ───────────────────────────
print("\n[5/5] Invalid Session → 404")
r = requests.post(
    f"{BASE_URL}/game/fake-session-id/answer",
    json={"answer": "yes"}
)
print(f"\n{'─'*55}")
print(f"  POST /game/fake-id/answer")
print(f"  Status : {r.status_code}")
print(f"  Detail : {r.json().get('detail', '')[:60]}")
assert r.status_code == 404
print("  ✅ PASSED — correctly returned 404")

# ── SUMMARY ──────────────────────────────────────────────────
print(f"\n{'='*55}")
print("  ✅ ALL 5 API TESTS PASSED")
print(f"  Active session: {sid[:8]}...")
print(f"  Visit http://localhost:8000/docs to test interactively")
print("="*55)