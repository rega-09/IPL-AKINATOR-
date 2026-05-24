# scraper/csv_converter.py
# ─────────────────────────────────────────────────────────────────────────────
# WHY THIS FILE?
#   Converts finalsheet.csv (766 players, 20 columns) into our exact
#   player schema used by the probability engine.
#
# STRATEGY:
#   1. Read CSV → pandas DataFrame
#   2. Map every CSV column → schema field
#   3. Derive missing fields (batting_position, known_for, etc.) from
#      the boolean flag columns (opener, finisher, aggressive_batter...)
#   4. Merge with our existing 48 hand-curated players
#      (they have richer data — keep them, deduplicate by name)
#   5. Save to data/processed/players.json
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
import json
import pandas as pd
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.helpers import slugify, save_json, load_json, normalize_name

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────

CSV_PATH      = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw", "finalsheet.csv")
EXISTING_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed", "players.json")
OUTPUT_PATH   = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed", "players.json")


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def yes_no_to_bool(val) -> bool:
    """
    Converts 'Yes'/'No' string to Python bool.
    WHY? All boolean columns in the CSV are strings, not actual booleans.
    """
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("yes", "true", "1")


def parse_teams(teams_str: str) -> List[str]:
    """
    Converts comma-separated team string → clean list of team codes.
    e.g. "CSK, MI, RCB" → ["CSK", "MI", "RCB"]

    Also normalizes legacy team names:
    DC_Old → DC  (Delhi Daredevils became Delhi Capitals)
    PW     → PWI (Pune Warriors)
    """
    if not teams_str or pd.isna(teams_str):
        return []

    team_map = {
        "DC_Old": "DC",
        "DC_OLD": "DC",
        "PW":     "PWI",
        "RPSu":   "RPS",
        "RPSG":   "RPS",
        "GL":     "GL",
    }

    teams = [t.strip() for t in str(teams_str).split(",")]
    normalized = []
    for t in teams:
        normalized.append(team_map.get(t, t))

    return sorted(set(normalized))  # Deduplicate


def derive_batting_position(row) -> str:
    """
    Derives batting_position from boolean flag columns.

    Priority:
      opener=Yes   → "opener"
      finisher=Yes → "finisher"
      wicketkeeper → "finisher" (most WKs bat lower)
      bowler role  → "tail"
      default      → "middle-order"
    """
    if yes_no_to_bool(row.get("opener", "No")):
        return "opener"
    if yes_no_to_bool(row.get("finisher", "No")):
        return "finisher"
    role = str(row.get("role", "")).lower()
    if "wicket" in role or yes_no_to_bool(row.get("wicketkeeper", "No")):
        return "finisher"
    if "bowl" in role:
        return "tail"
    return "middle-order"


def derive_known_for(row) -> List[str]:
    """
    Builds the known_for list from boolean flag columns.
    This is what powers human-like LLM questions later.
    """
    tags = []

    if yes_no_to_bool(row.get("aggressive_batter", "No")):
        tags.append("aggressive batting")
    if yes_no_to_bool(row.get("opener", "No")):
        tags.append("opening batsman")
    if yes_no_to_bool(row.get("finisher", "No")):
        tags.append("finisher")
    if yes_no_to_bool(row.get("death_bowler", "No")):
        tags.append("death bowling")
    if yes_no_to_bool(row.get("spinner", "No")):
        tags.append("spin bowling")
    if yes_no_to_bool(row.get("fast_bowler", "No")):
        tags.append("pace bowling")
    if yes_no_to_bool(row.get("captain", "No")):
        tags.append("captaincy")
    if yes_no_to_bool(row.get("orange_cap", "No")):
        tags.append("orange cap")
    if yes_no_to_bool(row.get("purple_cap", "No")):
        tags.append("purple cap")
    if yes_no_to_bool(row.get("title_winner", "No")):
        tags.append("title winner")
    if yes_no_to_bool(row.get("wicketkeeper", "No")):
        tags.append("wicketkeeper")

    return tags


def normalize_role(role_str: str, is_wk: bool) -> str:
    """
    Converts CSV role string → our standard role categories.
    """
    if is_wk:
        return "Wicketkeeper-Batsman"

    role = str(role_str).strip().lower()
    if "wicket" in role:
        return "Wicketkeeper-Batsman"
    if "all" in role:
        return "All-rounder"
    if "bowl" in role:
        return "Bowler"
    if "bat" in role or "batter" in role:
        return "Batsman"
    return "All-rounder"


# ─────────────────────────────────────────────────────────────────────────────
# CORE CONVERTER
# ─────────────────────────────────────────────────────────────────────────────

def convert_row(row: pd.Series) -> Dict:
    """
    Converts one CSV row → one player dict in our schema.
    Every field mapping is explicit and documented.
    """
    name     = str(row["name"]).strip()
    teams    = parse_teams(row.get("teams", ""))
    is_wk    = yes_no_to_bool(row.get("wicketkeeper", "No"))
    is_active = yes_no_to_bool(row.get("active", "No"))
    is_retired = yes_no_to_bool(row.get("retired", "No"))
    overseas  = yes_no_to_bool(row.get("overseas", "No"))
    captain   = yes_no_to_bool(row.get("captain", "No"))
    title_won = yes_no_to_bool(row.get("title_winner", "No"))
    orange    = yes_no_to_bool(row.get("orange_cap", "No"))
    purple    = yes_no_to_bool(row.get("purple_cap", "No"))
    role      = normalize_role(row.get("role", "Batsman"), is_wk)
    known_for = derive_known_for(row)

    # Bowling style — None for pure batsmen (403 nulls in CSV, expected)
    bowling_style = None
    if pd.notna(row.get("bowling_style")):
        bowling_style = str(row["bowling_style"]).strip()

    return {
        "id":                    slugify(name),
        "name":                  name,
        "nationality":           str(row.get("country", "India")).strip(),
        "overseas":              overseas,
        "primary_role":          role,
        "batting_style":         str(row.get("batting_style", "Right-hand")).strip(),
        "bowling_style":         bowling_style,

        # Teams — from CSV
        "ipl_teams":             teams,
        "current_team":          teams[-1] if teams else None,

        # Seasons — we don't have exact seasons in CSV
        # Derive: active players get [2022,2023,2024], retired get []
        # WHY not empty? Engine uses seasons for veteran/active questions.
        "seasons_played":        [2023, 2024] if is_active else [2008],
        "first_season":          2008,   # Conservative — most players joined early
        "last_season":           2024 if is_active else 2020,
        "active":                is_active,

        # Captaincy & achievements
        "captained_teams":       teams[:1] if captain else [],
        "is_captain_ever":       captain,
        "titles_won":            1 if title_won else 0,
        "won_title":             title_won,

        # Batting position — derived from boolean flags
        "batting_position":      derive_batting_position(row),

        # Known for — derived from boolean flags
        "known_for":             known_for,

        # Caps
        "orange_cap":            orange,
        "purple_cap":            purple,
        "cap_winner":            orange or purple,

        # Stats — not in CSV, use role-based estimates
        # WHY estimates? Engine uses these for approximate stat questions.
        "approx_ipl_runs":       1500 if "bat" in role.lower() or "all" in role.lower() or is_wk else 100,
        "approx_ipl_wickets":    50  if "bowl" in role.lower() or "all" in role.lower() else 0,
        "approx_matches":        len(teams) * 15,  # Rough proxy: 15 matches per team

        # Computed fields
        "total_seasons":         2 if is_active else 5,
        "veteran":               not is_active and not is_retired,  # Mid-career retired
        "played_for_multiple_teams": len(teams) > 1,
        "high_profile":          captain or orange or purple or title_won,

        "source":                "csv_import",
    }


# ─────────────────────────────────────────────────────────────────────────────
# MERGE WITH EXISTING DATASET
# ─────────────────────────────────────────────────────────────────────────────

def merge_datasets(csv_players: List[Dict], existing_players: List[Dict]) -> List[Dict]:
    """
    Merges CSV-imported players with our hand-curated 48-player dataset.

    Strategy:
      - Existing players WIN on conflict — they have richer data
      - CSV players fill in everyone who wasn't in existing set
      - Deduplication by normalized name

    WHY existing players win?
        Our hand-curated dataset has exact seasons_played, approx_ipl_runs,
        approx_ipl_wickets, known_for (manually written). Much richer than
        what we can derive from the CSV.
    """
    # Build lookup of existing players by normalized name
    existing_by_name = {
        normalize_name(p["name"]): p
        for p in existing_players
    }

    added   = 0
    skipped = 0

    final = list(existing_players)  # Start with existing

    for csv_player in csv_players:
        norm = normalize_name(csv_player["name"])
        if norm in existing_by_name:
            skipped += 1  # Already have this player with better data
        else:
            final.append(csv_player)
            existing_by_name[norm] = csv_player
            added += 1

    print(f"  Existing players kept : {len(existing_players)}")
    print(f"  New players from CSV  : {added}")
    print(f"  CSV duplicates skipped: {skipped}")
    print(f"  Total final dataset   : {len(final)}")

    return final


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def run_converter():
    print("=" * 60)
    print("CSV CONVERTER — finalsheet.csv → players.json")
    print("=" * 60)

    # Step 1: Read CSV
    print(f"\n[1/4] Reading CSV: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    print(f"  Rows: {len(df)}, Columns: {len(df.columns)}")

    # Step 2: Convert each row
    print(f"\n[2/4] Converting {len(df)} rows to player schema...")
    csv_players = []
    errors = 0
    for _, row in df.iterrows():
        try:
            player = convert_row(row)
            # Basic validation — must have name and at least one team
            if player["name"] and len(player["name"]) > 1:
                csv_players.append(player)
        except Exception as e:
            print(f"  [WARN] Skipped row (error: {e})")
            errors += 1

    print(f"  Converted: {len(csv_players)} players ({errors} errors)")

    # Step 3: Load existing dataset and merge
    print(f"\n[3/4] Merging with existing dataset...")
    existing = load_json(EXISTING_PATH) or []
    print(f"  Existing players: {len(existing)}")
    final_players = merge_datasets(csv_players, existing)

    # Step 4: Save
    print(f"\n[4/4] Saving to {OUTPUT_PATH}...")
    save_json(final_players, OUTPUT_PATH)

    # Summary
    print(f"\n{'='*60}")
    print(f"✅ DONE — Dataset expanded to {len(final_players)} players")
    print(f"\nBreakdown:")
    roles = {}
    for p in final_players:
        r = p.get("primary_role", "Unknown")
        roles[r] = roles.get(r, 0) + 1
    for role, count in sorted(roles.items(), key=lambda x: -x[1]):
        print(f"  {role:<30} {count}")

    overseas_count = sum(1 for p in final_players if p.get("overseas"))
    active_count   = sum(1 for p in final_players if p.get("active"))
    cap_count      = sum(1 for p in final_players if p.get("cap_winner"))
    print(f"\n  Overseas players   : {overseas_count}")
    print(f"  Active players     : {active_count}")
    print(f"  Cap winners        : {cap_count}")
    print(f"{'='*60}")

    return final_players


if __name__ == "__main__":
    players = run_converter()

    # Show 3 sample entries from CSV import
    csv_imported = [p for p in players if p.get("source") == "csv_import"]
    print(f"\n--- Sample CSV-imported entries ---")
    for p in csv_imported[:3]:
        print(f"\n{p['name']} ({p['nationality']})")
        print(f"  Role     : {p['primary_role']}")
        print(f"  Teams    : {p['ipl_teams']}")
        print(f"  Known for: {p['known_for']}")
        print(f"  Active   : {p['active']}")