# llm/gemini_client.py
# ─────────────────────────────────────────────────────────────────────────────
# APPROACH: Direct REST API via requests library
#
# WHY REST INSTEAD OF SDK?
#   Both google-generativeai (old) and google-genai (new) have been causing
#   version conflicts. Using the REST API directly:
#     - Zero SDK dependency conflicts
#     - Works with any Python version
#     - Identical reliability — it's the same API underneath
#     - requests is already in our requirements.txt
#
# API REFERENCE:
#   https://ai.google.dev/api/generate-content
# ─────────────────────────────────────────────────────────────────────────────

import os
import json
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# WHY gemini-2.0-flash?
#   gemini-1.5-flash requires v1beta endpoint which has access restrictions.
#   gemini-2.0-flash is the current stable free-tier model on v1 endpoint.
#   If this also fails, we fall back to gemini-1.5-flash on v1beta.
PRIMARY_MODEL   = "gemini-2.0-flash"
FALLBACK_MODEL  = "gemini-1.5-flash"
API_VERSION     = "v1beta"
BASE_URL        = f"https://generativelanguage.googleapis.com/{API_VERSION}/models"
MAX_TOKENS      = 500
TEMPERATURE     = 0.7


class GeminiClient:
    """
    Calls Gemini API directly via HTTP requests — no SDK dependency.
    Exposes .complete() and .complete_json() — same interface as before.
    """

    def __init__(self):
        self.api_key   = os.getenv("GEMINI_API_KEY")
        self.available = bool(self.api_key)
        self.model     = PRIMARY_MODEL

        if not self.api_key:
            print(
                "[WARNING] GEMINI_API_KEY not set in .env. "
                "LLM enhancement disabled — game will use raw questions."
            )
        else:
            # Auto-detect which model works for this API key
            self.model = self._detect_working_model()
            if self.model:
                print(f"[LLM] Gemini client ready — model: {self.model}")
            else:
                print("[WARNING] No Gemini model accessible. Using fallback mode.")
                self.available = False

    def _detect_working_model(self) -> Optional[str]:
        """
        Tries models in order and returns the first one that responds.
        WHY? Different API keys have access to different model versions.
        """
        models_to_try = [PRIMARY_MODEL, FALLBACK_MODEL, "gemini-pro"]

        for model in models_to_try:
            url = f"{BASE_URL}/{model}:generateContent?key={self.api_key}"
            try:
                resp = requests.post(
                    url,
                    json={
                        "contents": [{"parts": [{"text": "Reply with: ok"}]}],
                        "generationConfig": {"maxOutputTokens": 5}
                    },
                    timeout=8,
                )
                if resp.status_code == 200:
                    return model
                elif resp.status_code == 404:
                    continue   # Model not found — try next
                elif resp.status_code == 429:
                    # Rate limited — model EXISTS, just quota hit
                    # Return model name anyway — live calls will retry
                    print(f"[LLM] Rate limited (429) — model {model} exists, will retry on calls")
                    return model
                else:
                    print(f"[LLM] API key error: {resp.status_code} — {resp.text[:100]}")
                    return None
            except Exception:
                continue

        return None

    def _call_api(
        self,
        prompt:      str,
        max_tokens:  int   = MAX_TOKENS,
        temperature: float = TEMPERATURE,
    ) -> Optional[str]:
        """
        Makes the actual HTTP POST to Gemini REST API.

        WHY direct requests?
            Bypasses all SDK version issues entirely.
            The REST API is stable and version-independent.
        """
        if not self.available or not self.api_key or not self.model:
            return None

        url  = f"{BASE_URL}/{self.model}:generateContent?key={self.api_key}"
        body = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature":     temperature,
                "maxOutputTokens": max_tokens,
            }
        }

        try:
            resp = requests.post(url, json=body, timeout=15)

            if resp.status_code == 429:
                # Rate limited — skip LLM, use fallback immediately (no delay)
                # WHY no retry? A 5s delay blocks every answer click.
                # Better UX: fall back to raw question instantly.
                return None

            if resp.status_code != 200:
                print(f"[LLM ERROR] API returned {resp.status_code}: {resp.text[:150]}")
                return None

            data = resp.json()

            # Navigate Gemini response structure
            # Response: { candidates: [ { content: { parts: [ { text: "..." } ] } } ] }
            text = (
                data
                .get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
            return text.strip() if text else None

        except requests.exceptions.Timeout:
            print("[LLM ERROR] Gemini API timed out")
            return None
        except Exception as e:
            print(f"[LLM ERROR] Gemini API call failed: {type(e).__name__}: {e}")
            return None

    def complete(
        self,
        system_prompt: str,
        user_message:  str,
        max_tokens:    int   = MAX_TOKENS,
        temperature:   float = TEMPERATURE,
    ) -> Optional[str]:
        """
        Makes a Gemini API call and returns text.
        Returns None on failure — game always falls back gracefully.
        """
        if not self.available:
            return None

        combined = (
            f"INSTRUCTIONS:\n{system_prompt}\n\n"
            f"TASK:\n{user_message}"
        )
        return self._call_api(combined, max_tokens, temperature)

    def complete_json(
        self,
        system_prompt: str,
        user_message:  str,
        max_tokens:    int = MAX_TOKENS,
    ) -> Optional[dict]:
        """
        Gemini call expecting JSON output.
        Strips markdown fences and parses to dict.
        """
        raw = self.complete(
            system_prompt = system_prompt,
            user_message  = user_message,
            max_tokens    = max_tokens,
            temperature   = 0.2,
        )

        if raw is None:
            return None

        try:
            cleaned = raw.strip()
            # Strip ```json ... ``` or ``` ... ``` fences
            if cleaned.startswith("```"):
                lines   = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])
            return json.loads(cleaned)

        except json.JSONDecodeError as e:
            print(f"[LLM ERROR] JSON parse failed: {e}\nRaw: {raw[:200]}")
            return None


# ─────────────────────────────────────────────────────────────────────────────
# SINGLETON — named `claude` so enhancer.py import stays unchanged
# ─────────────────────────────────────────────────────────────────────────────

claude = GeminiClient()


# ─────────────────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")

    print("=== gemini_client.py self-test (REST API) ===\n")
    print(f"Available : {claude.available}")
    print(f"Model     : {claude.model}\n")

    if not claude.available:
        print("Set GEMINI_API_KEY in .env")
        print("Get free key: https://aistudio.google.com/app/apikey")
    else:
        print("TEST 1 — Basic text")
        r = claude.complete(
            system_prompt = "Answer in one sentence only.",
            user_message  = "Who is known as Captain Cool in IPL?"
        )
        print(f"  Response : {r}\n")

        print("TEST 2 — JSON output")
        r = claude.complete_json(
            system_prompt = (
                "You rephrase cricket questions naturally. "
                "Output ONLY valid JSON: {\"rephrased\": \"your question\"}. "
                "No markdown, no explanation."
            ),
            user_message = "Rephrase: 'Is your player primarily a bowler?'"
        )
        print(f"  Rephrased: {r}")

    print("\n✅ Test complete")