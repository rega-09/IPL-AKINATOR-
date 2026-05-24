# utils/helpers.py
# ─────────────────────────────────────────────────────────────────────────────
# WHY THIS FILE EXISTS:
# Every scraper needs the same small operations repeatedly:
#   - Making HTTP requests safely (with retries)
#   - Cleaning messy text from HTML
#   - Saving/loading JSON files
# Centralizing these here means: if something breaks, you fix it in ONE place.
# ─────────────────────────────────────────────────────────────────────────────

import requests   # Makes HTTP GET/POST requests to websites/APIs
import json       # Python's built-in JSON encoder/decoder
import time       # Used for sleep() — adds delay between requests
import re         # Regular expressions — for cleaning strings
import os         # File system operations (check if file exists, make dirs)

from typing import Optional, Dict, Any  # Type hints — makes code readable + catches bugs early


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: HTTP REQUEST HELPER
# ─────────────────────────────────────────────────────────────────────────────

def safe_get(url: str, headers: Optional[Dict] = None, retries: int = 3, delay: float = 2.0) -> Optional[requests.Response]:
    """
    Makes a GET request with automatic retries.

    WHY retries?
        Websites occasionally return 429 (Too Many Requests) or 503 (Service Unavailable).
        Instead of crashing, we wait and try again automatically.

    WHY delay?
        Being polite to servers. Hammering a site with rapid requests can get your
        IP blocked. A 2-second gap between retries is safe and respectful.

    Args:
        url     : The full URL to fetch
        headers : Optional dict — we use this to send a browser User-Agent header
                  so the server doesn't immediately reject us as a bot
        retries : How many times to retry on failure (default: 3)
        delay   : Seconds to wait between retries (default: 2.0)

    Returns:
        requests.Response object if successful, None if all retries fail
    """

    # Default headers mimic a real browser visit
    # WHY? Some sites block requests without a User-Agent header
    if headers is None:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

    for attempt in range(1, retries + 1):
        try:
            # timeout=10 means: if server doesn't respond in 10s, raise an error
            # WHY? Without timeout, your script can hang forever on a dead server
            response = requests.get(url, headers=headers, timeout=10)

            # raise_for_status() throws an exception for 4xx/5xx HTTP errors
            # WHY? A 404 response doesn't raise an error by default in requests —
            # this ensures we catch it explicitly
            response.raise_for_status()

            return response  # ✅ Success — return the response object

        except requests.exceptions.HTTPError as e:
            print(f"[Attempt {attempt}/{retries}] HTTP Error for {url}: {e}")

        except requests.exceptions.ConnectionError as e:
            print(f"[Attempt {attempt}/{retries}] Connection Error for {url}: {e}")

        except requests.exceptions.Timeout:
            print(f"[Attempt {attempt}/{retries}] Timeout for {url}")

        except requests.exceptions.RequestException as e:
            # Catch-all for any other requests error
            print(f"[Attempt {attempt}/{retries}] Request failed for {url}: {e}")

        # Wait before retrying — but not after the last attempt
        if attempt < retries:
            print(f"  Retrying in {delay}s...")
            time.sleep(delay)

    print(f"[ERROR] All {retries} attempts failed for: {url}")
    return None  # ❌ All retries exhausted


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: TEXT CLEANING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """
    Strips whitespace, newlines, and non-printable characters from a string.

    WHY?
        HTML scraped text is often full of:
        - Leading/trailing spaces: "  MS Dhoni  "
        - Newlines inside strings: "MS\nDhoni"
        - Non-breaking spaces (HTML &nbsp;): "MS\xa0Dhoni"
        This function normalizes all of that.
    """
    if not text:
        return ""

    # Replace non-breaking spaces (\xa0) with regular spaces
    text = text.replace("\xa0", " ")

    # re.sub replaces all whitespace sequences (tabs, newlines, multiple spaces)
    # with a single space
    text = re.sub(r'\s+', ' ', text)

    # .strip() removes leading and trailing spaces
    return text.strip()


def normalize_name(name: str) -> str:
    """
    Converts a player name into a consistent lowercase key for matching.

    WHY?
        When merging two datasets, "MS Dhoni" and "M.S. Dhoni" must match.
        We normalize both to "ms dhoni" before comparing.

    Example:
        "M.S. Dhoni"  → "ms dhoni"
        "Virat Kohli" → "virat kohli"
    """
    # Remove dots and extra spaces, then lowercase
    name = re.sub(r'\.', '', name)       # Remove dots
    name = re.sub(r'\s+', ' ', name)     # Collapse multiple spaces
    return name.strip().lower()


def extract_number(text: str) -> Optional[int]:
    """
    Extracts the first integer found in a string.

    WHY?
        Stats on Cricinfo often look like: "4,823 runs" or "runs: 4823"
        We just want the integer 4823.

    Example:
        "4,823 runs" → 4823
        "102*"       → 102
        "N/A"        → None
    """
    # Remove commas (thousands separators) first
    text = text.replace(",", "")

    # \d+ matches one or more digits
    match = re.search(r'\d+', text)
    return int(match.group()) if match else None


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: FILE I/O HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def save_json(data: Any, filepath: str) -> None:
    """
    Saves any Python object (dict, list) to a JSON file.

    WHY indent=2?
        Makes the JSON human-readable — important when debugging your dataset.
        Without it, the entire file is one unreadable line.

    WHY ensure_ascii=False?
        Player names may contain non-ASCII characters (e.g., accented letters
        in overseas player names). This preserves them correctly.
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[SAVED] {len(data) if isinstance(data, list) else 'data'} → {filepath}")


def load_json(filepath: str) -> Optional[Any]:
    """
    Loads a JSON file and returns the Python object.

    WHY check if file exists first?
        Gives a clear error message instead of a cryptic FileNotFoundError.
    """
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        return None

    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def slugify(name: str) -> str:
    """
    Converts a player name to a URL-safe ID string.

    WHY?
        Each player needs a unique `id` field in our dataset.
        "MS Dhoni" → "ms_dhoni"
        "Andre Russell" → "andre_russell"

    This ID is used to:
        - Deduplicate players across sources
        - Reference players in the probability engine
    """
    name = normalize_name(name)          # lowercase, remove dots
    name = re.sub(r'[^a-z0-9\s]', '', name)  # remove special chars
    name = re.sub(r'\s+', '_', name)          # replace spaces with underscores
    return name