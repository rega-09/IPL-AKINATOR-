# engine/question_bank.py  — v2 (calibrated for 802 players)
# ─────────────────────────────────────────────────────────────────────────────
# Every question is calibrated against the real 802-player dataset.
# Target split: 35-65% YES for maximum information gain.
# Poor questions from v1 are replaced or re-thresholded.
# New questions added from CSV boolean columns.
# ─────────────────────────────────────────────────────────────────────────────

from typing import Dict, List, Callable, Any
from enum import Enum


class Answer(Enum):
    YES        = "yes"
    NO         = "no"
    MAYBE      = "maybe"
    DONT_KNOW  = "dont_know"


LIKELIHOOD = {
    Answer.YES:       {"fits": 0.95, "doesnt": 0.05},
    Answer.NO:        {"fits": 0.05, "doesnt": 0.95},
    Answer.MAYBE:     {"fits": 0.50, "doesnt": 0.50},
    Answer.DONT_KNOW: {"fits": 0.60, "doesnt": 0.60},
}


def make_question(id: str, text: str, category: str, scorer: Callable) -> Dict:
    return {"id": id, "text": text, "category": category, "scorer": scorer}


QUESTION_BANK: List[Dict] = [

    # ── ROLE (51% bowlers in dataset — highest IG questions) ─────────────────

    make_question(
        id="is_pure_bowler",
        text="Is your player primarily a bowler?",
        category="role",
        scorer=lambda p: p.get("primary_role") == "Bowler"
        # 51% YES — best first question
    ),

    make_question(
        id="is_batsman",
        text="Is your player primarily a batsman (not an all-rounder or keeper)?",
        category="role",
        scorer=lambda p: p.get("primary_role") == "Batsman"
        # 31% YES
    ),

    make_question(
        id="is_wicketkeeper",
        text="Is your player a wicketkeeper?",
        category="role",
        scorer=lambda p: (
            p.get("primary_role") == "Wicketkeeper-Batsman" or
            "wicketkeeper" in " ".join(p.get("known_for", []))
        )
        # 6% YES — low but very decisive when YES
    ),

    make_question(
        id="is_allrounder",
        text="Is your player a genuine all-rounder who both bats and bowls significantly?",
        category="role",
        scorer=lambda p: p.get("primary_role") == "All-rounder"
        # 12% YES
    ),

    make_question(
        id="bowls_pace",
        text="Does your player bowl pace (fast or medium-fast)?",
        category="role",
        scorer=lambda p: any(
            kw in (p.get("bowling_style") or "").lower()
            for kw in ["fast", "medium", "pace"]
        ) or "pace bowling" in " ".join(p.get("known_for", []))
        # 44% YES — good split
    ),

    make_question(
        id="bowls_spin",
        text="Does your player bowl spin?",
        category="role",
        scorer=lambda p: any(
            kw in (p.get("bowling_style") or "").lower()
            for kw in ["off-break", "leg-break", "orthodox", "wrist", "spin", "chinaman"]
        ) or "spin bowling" in " ".join(p.get("known_for", []))
        # 5% YES — low but very decisive
    ),

    make_question(
        id="left_hand_bat",
        text="Does your player bat left-handed?",
        category="role",
        scorer=lambda p: "left" in (p.get("batting_style") or "").lower()
        # 8% YES
    ),

    # ── NATIONALITY — regional groupings (better splits than per-country) ─────

    make_question(
        id="is_indian",
        text="Is your player Indian?",
        category="nationality",
        scorer=lambda p: not p.get("overseas", False)
        # 56% YES — great split
    ),

    make_question(
        id="is_overseas",
        text="Is your player from outside India (an overseas player)?",
        category="nationality",
        scorer=lambda p: p.get("overseas", False)
        # 44% YES — great split
    ),

    make_question(
        id="from_subcontinent",
        text="Is your player from the subcontinent (India, Pakistan, Sri Lanka, Bangladesh, Afghanistan)?",
        category="nationality",
        # India(447) + Pakistan(12) + SL(35) + BD(6) + AF(10) ≈ 510 = 64%
        scorer=lambda p: any(
            kw in (p.get("nationality") or "").lower()
            for kw in ["india", "indian", "pakistan", "sri lanka", "bangladesh", "afghanistan", "afghan"]
        )
    ),

    make_question(
        id="from_australia_nz",
        text="Is your player from Australia or New Zealand?",
        category="nationality",
        # Australia(97) + NZ(36) ≈ 133 = 17%
        scorer=lambda p: any(
            kw in (p.get("nationality") or "").lower()
            for kw in ["australia", "australian", "new zealand", "new zealander", "kiwi"]
        )
    ),

    make_question(
        id="from_africa_caribbean",
        text="Is your player from South Africa or the West Indies?",
        category="nationality",
        # SA(63) + WI(40) ≈ 103 = 13%
        scorer=lambda p: any(
            kw in (p.get("nationality") or "").lower()
            for kw in ["south africa", "south african", "west ind"]
        )
    ),

    make_question(
        id="from_england",
        text="Is your player from England?",
        category="nationality",
        # England(48) = 6%
        scorer=lambda p: any(
            kw in (p.get("nationality") or "").lower()
            for kw in ["england", "english"]
        )
    ),

    # ── BATTING POSITION ──────────────────────────────────────────────────────

    make_question(
        id="is_opener",
        text="Does your player typically open the batting?",
        category="batting_position",
        scorer=lambda p: (
            p.get("batting_position") == "opener" or
            "opening batsman" in " ".join(p.get("known_for", []))
        )
        # 16% YES
    ),

    make_question(
        id="is_finisher",
        text="Is your player known as a finisher who bats in the death overs?",
        category="batting_position",
        scorer=lambda p: (
            p.get("batting_position") == "finisher" or
            "finisher" in " ".join(p.get("known_for", []))
        )
        # 7% YES
    ),

    make_question(
        id="bats_in_top_half",
        text="Does your player bat in the top half of the order (positions 1-5)?",
        category="batting_position",
        scorer=lambda p: p.get("batting_position") in ["opener", "middle-order"] or
                         p.get("primary_role") in ["Batsman", "Wicketkeeper-Batsman"]
        # ~40% YES
    ),

    make_question(
        id="is_aggressive_batter",
        text="Is your player known for aggressive, attacking batting?",
        category="batting_position",
        scorer=lambda p: (
            "aggressive batting" in " ".join(p.get("known_for", [])) or
            "aggressive opener" in " ".join(p.get("known_for", []))
        )
        # 6% YES — decisive when YES
    ),

    # ── TEAM — all major teams kept, thresholds verified ─────────────────────

    make_question(
        id="played_for_dc",
        text="Has your player ever played for Delhi Capitals or Delhi Daredevils?",
        category="team",
        scorer=lambda p: "DC" in p.get("ipl_teams", []) or "DC_OLD" in p.get("ipl_teams", [])
        # 29% YES — best team question
    ),

    make_question(
        id="played_for_rcb",
        text="Has your player ever played for Royal Challengers Bangalore (RCB)?",
        category="team",
        scorer=lambda p: "RCB" in p.get("ipl_teams", [])
        # 23% YES
    ),

    make_question(
        id="played_for_pbks",
        text="Has your player ever played for Punjab Kings or Kings XI Punjab?",
        category="team",
        scorer=lambda p: "PBKS" in p.get("ipl_teams", [])
        # 23% YES
    ),

    make_question(
        id="played_for_mi",
        text="Has your player ever played for Mumbai Indians (MI)?",
        category="team",
        scorer=lambda p: "MI" in p.get("ipl_teams", [])
        # 22% YES
    ),

    make_question(
        id="played_for_rr",
        text="Has your player ever played for Rajasthan Royals (RR)?",
        category="team",
        scorer=lambda p: "RR" in p.get("ipl_teams", [])
        # 22% YES
    ),

    make_question(
        id="played_for_kkr",
        text="Has your player ever played for Kolkata Knight Riders (KKR)?",
        category="team",
        scorer=lambda p: "KKR" in p.get("ipl_teams", [])
        # 19% YES
    ),

    make_question(
        id="played_for_csk",
        text="Has your player ever played for Chennai Super Kings (CSK)?",
        category="team",
        scorer=lambda p: "CSK" in p.get("ipl_teams", [])
        # 15% YES
    ),

    make_question(
        id="played_for_srh",
        text="Has your player ever played for Sunrisers Hyderabad (SRH)?",
        category="team",
        scorer=lambda p: "SRH" in p.get("ipl_teams", [])
        # 15% YES
    ),

    make_question(
        id="played_for_newer_teams",
        text="Has your player played for any newer IPL franchise (GT, LSG, PWI, GL, RPS)?",
        category="team",
        scorer=lambda p: any(
            t in p.get("ipl_teams", [])
            for t in ["GT", "LSG", "PWI", "GL", "RPS", "KTK"]
        )
        # GT(6%) + LSG(6%) + PWI(6%) + GL(4%) + RPS(4%) ≈ ~20% YES
    ),

    make_question(
        id="one_team_only",
        text="Has your player played for only one IPL team throughout their career?",
        category="team",
        scorer=lambda p: not p.get("played_for_multiple_teams", True)
        # 48% YES — great split
    ),

    make_question(
        id="multiple_teams",
        text="Has your player played for more than two different IPL teams?",
        category="team",
        scorer=lambda p: len(set(p.get("ipl_teams", []))) > 2
        # 27% YES
    ),

    make_question(
        id="played_for_big_four",
        text="Has your player played for any of the original 'Big Four' franchises (MI, CSK, RCB, KKR)?",
        category="team",
        scorer=lambda p: any(t in p.get("ipl_teams", []) for t in ["MI", "CSK", "RCB", "KKR"])
        # MI(22)+CSK(15)+RCB(23)+KKR(19) with overlap ≈ 45% YES
    ),

    # ── ERA / EXPERIENCE ──────────────────────────────────────────────────────

    make_question(
        id="is_active",
        text="Is your player currently active in the IPL (playing in recent seasons)?",
        category="era",
        scorer=lambda p: p.get("active", False)
        # 36% YES — good split
    ),

    make_question(
        id="is_retired",
        text="Has your player retired from IPL cricket?",
        category="era",
        scorer=lambda p: not p.get("active", False)
        # 64% YES
    ),

    make_question(
        id="played_many_matches",
        text="Has your player played more than 20 IPL matches in their career?",
        category="era",
        scorer=lambda p: (p.get("approx_matches") or 0) > 20
        # 53% YES — near perfect split
    ),

    make_question(
        id="played_30_plus",
        text="Has your player played more than 30 IPL matches?",
        category="era",
        scorer=lambda p: (p.get("approx_matches") or 0) > 30
        # 30% YES
    ),

    make_question(
        id="is_veteran",
        text="Is your player a long-serving IPL veteran who has been around since the early seasons?",
        category="era",
        scorer=lambda p: p.get("veteran", False) or p.get("first_season", 2020) <= 2012
        # ~15% YES
    ),

    # ── ACHIEVEMENTS ─────────────────────────────────────────────────────────

    make_question(
        id="has_captained",
        text="Has your player ever captained an IPL team?",
        category="achievement",
        scorer=lambda p: p.get("is_captain_ever", False) or len(p.get("captained_teams", [])) > 0
        # 7% YES — decisive
    ),

    make_question(
        id="won_ipl_title",
        text="Has your player won an IPL title?",
        category="achievement",
        scorer=lambda p: p.get("won_title", False) or p.get("titles_won", 0) > 0
        # 4% YES — decisive
    ),

    make_question(
        id="won_orange_cap",
        text="Has your player ever won the Orange Cap (most runs in a season)?",
        category="achievement",
        scorer=lambda p: p.get("orange_cap", False)
        # 3% YES — very decisive
    ),

    make_question(
        id="won_purple_cap",
        text="Has your player ever won the Purple Cap (most wickets in a season)?",
        category="achievement",
        scorer=lambda p: p.get("purple_cap", False)
        # 3% YES — very decisive
    ),

    make_question(
        id="won_any_cap",
        text="Has your player ever won the Orange Cap or Purple Cap?",
        category="achievement",
        scorer=lambda p: p.get("cap_winner", False) or p.get("orange_cap", False) or p.get("purple_cap", False)
        # 6% YES — useful combination
    ),

    make_question(
        id="high_profile",
        text="Is your player one of the most well-known, high-profile names in IPL history?",
        category="achievement",
        scorer=lambda p: p.get("high_profile", False)
        # 12% YES
    ),

    # ── PLAYING STYLE — from CSV boolean columns ───────────────────────────

    make_question(
        id="is_death_bowler",
        text="Is your player known for bowling in the death overs (overs 16-20)?",
        category="style",
        scorer=lambda p: (
            "death bowling" in " ".join(p.get("known_for", [])) or
            "yorker" in " ".join(p.get("known_for", []))
        )
        # 7% YES — very decisive
    ),

    make_question(
        id="is_aggressive_batting",
        text="Is your player particularly known for aggressive, attacking batting?",
        category="style",
        scorer=lambda p: "aggressive batting" in " ".join(p.get("known_for", []))
        # 6% YES
    ),

    make_question(
        id="is_power_hitter",
        text="Is your player known as a power hitter who hits big sixes?",
        category="style",
        scorer=lambda p: any(
            kw in " ".join(p.get("known_for", []))
            for kw in ["power hitting", "six", "aggressive batting", "aggressive opener"]
        )
        # ~8% YES
    ),

    make_question(
        id="scored_runs",
        text="Has your player scored significant runs in the IPL (over 500 runs total)?",
        category="stats",
        scorer=lambda p: (p.get("approx_ipl_runs") or 0) > 500
        # ~49% YES — great split (batters/allrounders vs pure bowlers)
    ),

    make_question(
        id="taken_wickets",
        text="Has your player taken significant wickets in the IPL (over 50 wickets total)?",
        category="stats",
        scorer=lambda p: (p.get("approx_ipl_wickets") or 0) > 50
        # ~4% YES — decisive for specialist bowlers
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

QUESTION_MAP: Dict[str, Dict] = {q["id"]: q for q in QUESTION_BANK}


def get_question(question_id: str) -> Dict:
    if question_id not in QUESTION_MAP:
        raise KeyError(f"Question ID '{question_id}' not found.")
    return QUESTION_MAP[question_id]


def get_questions_by_category(category: str) -> List[Dict]:
    return [q for q in QUESTION_BANK if q["category"] == category]


def compute_player_fit(question: Dict, player: Dict) -> bool:
    try:
        result = question["scorer"](player)
        if isinstance(result, float):
            return result >= 0.5
        return bool(result)
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys, json
    sys.path.insert(0, ".")
    from engine.probability_engine import CandidatePool

    with open("data/processed/players.json") as f:
        players = json.load(f)

    pool = CandidatePool(players)

    print(f"Question bank v2: {len(QUESTION_BANK)} questions")
    print(f"Players         : {len(players)}")
    print(f"Starting entropy: {pool.entropy():.4f} bits\n")

    print(f"{'Question ID':<35} {'YES%':>6} {'IG':>8} {'Quality'}")
    print("-" * 65)

    results = []
    for q in QUESTION_BANK:
        yes = sum(1 for p in players if compute_player_fit(q, p))
        pct = yes / len(players) * 100
        ig  = pool.information_gain(q["id"])
        qual = "✅" if 30 <= pct <= 70 else ("⚠️ " if 15 <= pct <= 85 else "❌")
        results.append((ig, q["id"], pct, qual))

    results.sort(key=lambda x: -x[0])
    good = sum(1 for _, _, pct, q in results if q == "✅")
    warn = sum(1 for _, _, pct, q in results if q == "⚠️ ")
    poor = sum(1 for _, _, pct, q in results if q == "❌")

    for ig, qid, pct, qual in results:
        print(f"{qid:<35} {pct:>5.1f}%  {ig:>6.4f}  {qual}")

    print(f"\nGood (30-70%): {good}  |  Weak: {warn}  |  Poor: {poor}")
    print(f"Top IG question: '{results[0][1]}' at {results[0][0]:.4f} bits")