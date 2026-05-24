# scraper/ipl_scraper.py
# ─────────────────────────────────────────────────────────────────────────────
# WHY THIS SCRAPER?
#   The IPL official stats API returns structured JSON with:
#     - All players who appeared in each IPL season
#     - Their teams per season
#     - Basic role classifications
#
#   This is our FOUNDATION layer — we build the player list here,
#   then Cricinfo enriches it with deeper stats.
#
# WHY THIS API SPECIFICALLY?
#   https://ipl-stats-sports-mechanic.s3.ap-south-1.amazonaws.com
#   This is a public S3 bucket used by the official IPL website.
#   It's stable, no auth required, returns clean JSON.
# ─────────────────────────────────────────────────────────────────────────────

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.helpers import safe_get, save_json, clean_text, slugify, normalize_name
from typing import Dict, List, Optional
import time

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# WHY constants at the top?
#   If a URL changes, you change it in ONE place — not scattered across the code.
# ─────────────────────────────────────────────────────────────────────────────

BASE_URL = "https://ipl-stats-sports-mechanic.s3.ap-south-1.amazonaws.com/ipl/feeds"

# Each IPL season has a numeric ID in the API.
# Season 1 (2008) = ID 1, Season 17 (2024) = ID 17
# We map year → season_id for readable code
SEASON_MAP = {
    2008: 1,  2009: 2,  2010: 3,  2011: 4,
    2012: 5,  2013: 6,  2014: 7,  2015: 8,
    2016: 9,  2017: 10, 2018: 11, 2019: 12,
    2020: 13, 2021: 14, 2022: 15, 2023: 16,
    2024: 17
}

# Team name normalization map
# WHY? The API uses full names like "Chennai Super Kings" but we want short codes
# like "CSK" for our dataset — cleaner for LLM reasoning
TEAM_SHORT = {
    "Chennai Super Kings": "CSK",
    "Mumbai Indians": "MI",
    "Royal Challengers Bangalore": "RCB",
    "Royal Challengers Bengaluru": "RCB",
    "Kolkata Knight Riders": "KKR",
    "Sunrisers Hyderabad": "SRH",
    "Delhi Capitals": "DC",
    "Delhi Daredevils": "DC",
    "Rajasthan Royals": "RR",
    "Punjab Kings": "PBKS",
    "Kings XI Punjab": "PBKS",
    "Deccan Chargers": "DC_OLD",
    "Kochi Tuskers Kerala": "KTK",
    "Pune Warriors India": "PWI",
    "Rising Pune Supergiant": "RPS",
    "Rising Pune Supergiants": "RPS",
    "Gujarat Lions": "GL",
    "Gujarat Titans": "GT",
    "Lucknow Super Giants": "LSG",
}


# ─────────────────────────────────────────────────────────────────────────────
# CORE FUNCTION 1: Fetch one season's squad data
# ─────────────────────────────────────────────────────────────────────────────

def fetch_season_squads(year: int, season_id: int) -> List[Dict]:
    """
    Fetches all player-team records for one IPL season.

    WHY returns a list of dicts?
        Each dict = one player-season record:
        { name, team, year, role }
        Multiple records per player (one per season they played)
        The merger.py will later collapse these into one player entry.

    Args:
        year      : Calendar year of the season (e.g., 2023)
        season_id : Numeric ID used by the API (e.g., 16)

    Returns:
        List of player-season dicts, or empty list on failure
    """

    # The squad endpoint returns team rosters per season
    url = f"{BASE_URL}/stats/{season_id}-squad.json"
    print(f"  Fetching squads for {year} (season_id={season_id})...")

    response = safe_get(url)
    if not response:
        print(f"  [SKIP] Could not fetch season {year}")
        return []

    try:
        data = response.json()
    except Exception as e:
        print(f"  [ERROR] JSON parse failed for season {year}: {e}")
        return []

    records = []

    # The API structure: data["squads"] = list of team objects
    # Each team object has "players" list
    # WHY check with .get()?
    #   Safer than data["squads"] — if key missing, returns [] instead of crashing
    squads = data.get("squads", [])

    for team_obj in squads:
        team_full_name = clean_text(team_obj.get("name", "Unknown"))
        # Convert full name → short code using our map
        # If not in map, use first letters of each word as fallback
        team_code = TEAM_SHORT.get(team_full_name, team_full_name[:3].upper())

        players = team_obj.get("players", [])
        for player_obj in players:
            name = clean_text(player_obj.get("name", ""))
            if not name:
                continue  # Skip empty names

            role_raw = clean_text(player_obj.get("role", "Unknown"))
            nationality = clean_text(player_obj.get("country", "India"))

            records.append({
                "name": name,
                "slug": slugify(name),          # Unique ID: "ms_dhoni"
                "team": team_code,
                "year": year,
                "role_raw": role_raw,
                "nationality": nationality,
                "overseas": nationality.lower() not in ["india", "indian", ""],
            })

    print(f"  → Found {len(records)} player-team records for {year}")
    return records


# ─────────────────────────────────────────────────────────────────────────────
# CORE FUNCTION 2: Normalize role strings
# ─────────────────────────────────────────────────────────────────────────────

def normalize_role(role_raw: str) -> str:
    """
    Converts raw role strings from the API into clean standard categories.

    WHY?
        The API returns inconsistent strings like:
        "Bat", "BAT", "batsman", "Batting", "WK-Bat", "Wicket Keeper Batsman"
        We standardize to 4 clean roles our LLM can reason about clearly.

    Standard roles:
        - "Batsman"
        - "Bowler"
        - "All-rounder"
        - "Wicketkeeper-Batsman"
    """
    role = role_raw.lower().strip()

    # Check in order of specificity — most specific patterns first
    if any(kw in role for kw in ["wicket", "wk", "keeper", "glove"]):
        return "Wicketkeeper-Batsman"
    elif any(kw in role for kw in ["all", "allrounder", "all-rounder"]):
        return "All-rounder"
    elif any(kw in role for kw in ["bowl", "pace", "spin", "fast", "medium"]):
        return "Bowler"
    elif any(kw in role for kw in ["bat", "opening", "opener"]):
        return "Batsman"
    else:
        return "All-rounder"  # Default fallback — safer than "Unknown"


# ─────────────────────────────────────────────────────────────────────────────
# CORE FUNCTION 3: Collapse season records into one player per entry
# ─────────────────────────────────────────────────────────────────────────────

def collapse_to_players(all_records: List[Dict]) -> List[Dict]:
    """
    Merges multiple season records for the same player into one unified entry.

    WHY?
        fetch_season_squads() returns one record per (player, season).
        MS Dhoni will have 16 records — one per season he played.
        We need ONE record for MS Dhoni with:
            - all his teams: ["CSK", "RPS"]
            - all his seasons: [2008, 2009, ..., 2024]

    Process:
        1. Group all records by player slug (unique ID)
        2. For each player: aggregate teams, seasons, determine primary role
        3. Return clean list of player dicts

    Args:
        all_records: Flat list of (player, season) records

    Returns:
        List of one-dict-per-player records
    """

    # Use slug as the grouping key
    # player_map: { "ms_dhoni": { name, teams: set(), seasons: set(), roles: list, ... } }
    player_map: Dict[str, Dict] = {}

    for record in all_records:
        slug = record["slug"]

        if slug not in player_map:
            # First time we see this player — initialize their entry
            player_map[slug] = {
                "id": slug,
                "name": record["name"],
                "nationality": record["nationality"],
                "overseas": record["overseas"],
                "ipl_teams": set(),       # Use set to auto-deduplicate
                "seasons_played": set(),  # Use set to auto-deduplicate
                "roles_seen": [],         # Collect all role strings across seasons
            }

        # Add this season's data to the player's entry
        player_map[slug]["ipl_teams"].add(record["team"])
        player_map[slug]["seasons_played"].add(record["year"])
        player_map[slug]["roles_seen"].append(record["role_raw"])

    # Now convert sets to sorted lists (JSON can't serialize sets)
    # and determine the primary role (most common role string)
    players = []
    for slug, player in player_map.items():
        # Most common role across all seasons = primary role
        # WHY? A player might be listed as "Bat" in 2010 but "All-rounder" later
        # The most frequent label is most accurate
        from collections import Counter
        role_counts = Counter(player["roles_seen"])
        most_common_role_raw = role_counts.most_common(1)[0][0]

        seasons_list = sorted(player["seasons_played"])

        players.append({
            "id": slug,
            "name": player["name"],
            "nationality": player["nationality"],
            "overseas": player["overseas"],
            "ipl_teams": sorted(player["ipl_teams"]),
            "current_team": sorted(player["ipl_teams"])[-1],  # Last team alphabetically as proxy
            "seasons_played": seasons_list,
            "first_season": min(seasons_list),
            "last_season": max(seasons_list),
            "active": max(seasons_list) >= 2023,  # Active if played in last 2 seasons
            "primary_role": normalize_role(most_common_role_raw),
            # Fields below will be enriched by cricinfo_scraper.py
            "batting_style": None,
            "bowling_style": None,
            "captained_teams": [],
            "titles_won": 0,
            "approx_ipl_runs": None,
            "approx_ipl_wickets": None,
            "approx_matches": len(seasons_list),  # Rough proxy
            "orange_cap": False,
            "purple_cap": False,
            "known_for": [],
            "high_profile": False,
            "source": "ipl_official",
        })

    # Sort by first season — older players first
    players.sort(key=lambda x: x["first_season"])
    return players


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def run_ipl_scraper(output_path: str = "data/raw/ipl_official.json") -> List[Dict]:
    """
    Full pipeline: fetch all seasons → collapse to players → save JSON.

    WHY save raw output separately?
        If the merger fails later, you don't re-scrape — you reload from raw file.
        This is called 'checkpoint saving' — important in long pipelines.
    """
    print("\n" + "="*60)
    print("IPL OFFICIAL SCRAPER — Starting")
    print("="*60)

    all_records = []

    for year, season_id in SEASON_MAP.items():
        season_records = fetch_season_squads(year, season_id)
        all_records.extend(season_records)

        # WHY sleep between requests?
        # Avoid overwhelming the server with rapid sequential requests.
        # Even for a public S3 bucket, being polite is good practice.
        time.sleep(0.5)

    print(f"\nTotal raw records collected: {len(all_records)}")

    # Collapse into per-player records
    players = collapse_to_players(all_records)
    print(f"Unique players after collapsing: {len(players)}")

    # Save to raw folder
    save_json(players, output_path)

    return players


# ─────────────────────────────────────────────────────────────────────────────
# Run directly for testing
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    players = run_ipl_scraper()
    # Print a sample to verify
    print("\n--- Sample Player Entry ---")
    import json
    if players:
        print(json.dumps(players[0], indent=2))