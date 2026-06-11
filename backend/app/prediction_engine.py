"""
NEET Maharashtra CAP Prediction Engine v2.

Probability model uses:
  1. Multi-round weighted probability  (R1=40% R2=30% R3=20% R4=10%)
  2. Fill rate                         (seats_filled / total_seats)
  3. Seat movement trend               (did closing rank open up R1→R2?)
  4. Confidence score                  (how many rounds have data)

Tier classification is based on R1 closing rank (most important round).
"""

import os
import psycopg2
import psycopg2.extras
from dataclasses import dataclass, field
from statistics import stdev

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:NeuraNeet2026@db.sthzhfurxnvtcpovecsu.supabase.co:5432/postgres"
)

ROUND_WEIGHTS  = {"R1": 0.40, "R2": 0.30, "R3": 0.20, "R4": 0.10}
CATEGORY_TO_SM = {           # maps allotment category → seat_matrix column
    "SC":   "sc_seats",
    "ST":   "st_seats",
    "VJA":  "vja_seats",
    "NTB":  "ntb_seats",
    "NTC":  "ntc_seats",
    "NTD":  "ntd_seats",
    "OBC":  "obc_seats",
    "SEBC": "sebc_seats",
    "EWS":  "ews_seats",
    "OPEN": "open_seats",
}


def get_conn():
    return psycopg2.connect(DATABASE_URL, connect_timeout=30)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class RoundData:
    round:        str
    closing_rank: int
    seats_filled: int


@dataclass
class CollegeRecommendation:
    college_code:     str
    college_name:     str
    category:         str
    women_quota:      bool
    section:          str        # GOVT_MBBS / PVT_MBBS / GOVT_BDS etc.
    total_seats:      int
    # Per-round data
    rounds:           dict       # {round: RoundData}
    # Computed scores
    r1_closing:       int
    best_closing:     int        # lowest closing rank across all rounds
    worst_closing:    int        # highest closing rank (most open round)
    fill_rate:        float      # seats_filled_R1 / total_seats
    seat_movement:    int        # worst_closing - r1_closing (positive = opens up)
    round_probability: float     # weighted fraction of rounds student clears
    confidence:       float      # 0-1 based on data completeness
    final_probability: float     # combined score
    tier:             str        # Safe / Moderate / Aggressive
    # Per-round cleared flags
    r1_cleared:       bool = False
    r2_cleared:       bool = False
    r3_cleared:       bool = False
    r4_cleared:       bool = False
    earliest_round:   str  = ""   # earliest round student can get in


@dataclass
class PredictionResult:
    student_air:  int
    category:     str
    women_quota:  bool
    year:         int
    safe:         list[CollegeRecommendation] = field(default_factory=list)
    moderate:     list[CollegeRecommendation] = field(default_factory=list)
    aggressive:   list[CollegeRecommendation] = field(default_factory=list)

    @property
    def all_colleges(self):
        return self.safe + self.moderate + self.aggressive

    def summary(self):
        return {
            "student_air": self.student_air,
            "category": self.category,
            "total_options": len(self.all_colleges),
            "safe_count": len(self.safe),
            "moderate_count": len(self.moderate),
            "aggressive_count": len(self.aggressive),
        }


# ── Core prediction logic ─────────────────────────────────────────────────────

def _compute_round_probability(student_air: int,
                                rounds: dict[str, RoundData]) -> tuple[float, dict[str, bool]]:
    """
    Weighted probability + per-round cleared flags.
    Returns (weighted_prob, {round: cleared_bool})
    """
    total_w = 0.0
    cleared_w = 0.0
    per_round: dict[str, bool] = {}
    for rnd, data in rounds.items():
        w = ROUND_WEIGHTS.get(rnd, 0)
        if w == 0:
            continue
        total_w += w
        cleared = student_air <= data.closing_rank
        per_round[rnd] = cleared
        if cleared:
            cleared_w += w
    prob = round(cleared_w / total_w, 3) if total_w > 0 else 0.0
    return prob, per_round


def _compute_fill_rate(seats_filled: int, total_seats: int) -> float:
    if total_seats <= 0:
        return 0.5  # unknown
    return min(1.0, seats_filled / total_seats)


def _classify_tier(student_air: int, r1_closing: int) -> str:
    """Classify tier based on R1 closing rank (most predictive)."""
    if r1_closing <= 0:
        return None
    ratio = student_air / r1_closing
    if ratio <= 0.85:
        return "Safe"
    elif ratio <= 1.00:
        return "Moderate"
    elif ratio <= 1.25:
        return "Aggressive"
    return None


def _final_probability(round_prob: float, fill_rate: float,
                       movement: int, confidence: float,
                       per_round: dict[str, bool]) -> float:
    """
    Combine all signals into a realistic probability score (max 92%).

    round_prob  : weighted fraction of rounds cleared
    fill_rate   : seats_filled / total_seats
    movement    : seats opened in later rounds (positive = more opportunity)
    confidence  : data completeness (more rounds = higher confidence)
    per_round   : which specific rounds the student clears
    """
    # Penalty if student only qualifies in later rounds (R3/R4 only)
    # Those seats have already been partially filled by earlier rounds
    r1_ok = per_round.get("R1", False)
    r2_ok = per_round.get("R2", False)
    early_rounds = r1_ok or r2_ok

    # Base score weighted by confidence
    base = round_prob * confidence + round_prob * (1 - confidence) * 0.5

    # If student only qualifies from R3 onwards, seats are fewer and competition higher
    if not early_rounds and round_prob > 0:
        base = base * 0.65   # late-round penalty

    # Movement bonus for borderline students
    if movement > 0 and round_prob < 0.6:
        base = min(base * 1.15, base + 0.08)

    # Fill rate adjustment
    if fill_rate < 0.4:
        base = min(base * 1.08, base + 0.05)   # underfilled = easier
    elif fill_rate > 0.95:
        base = base * 0.93                       # overfull = competitive

    # Hard cap — never show 100%, there's always uncertainty
    return round(min(0.92, max(0.0, base)), 3)


def predict(
    student_air:  int,
    category:     str,
    women_quota:  bool  = False,
    year:         int   = 2025,
    top_n:        int   = 50,
) -> PredictionResult:
    """
    Main prediction function.

    Args:
        student_air : All India Rank
        category    : OPEN / OBC / SC / ST / SEBC / EWS / NTB / NTC / NTD / VJA
        women_quota : Include women's quota seats
        year        : Counselling year
        top_n       : Max colleges per tier
    """
    conn = get_conn()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Categories to query: student's own category + OPEN (reserved students
    # can fill open seats if their rank qualifies)
    categories = [category] if category == "OPEN" else [category, "OPEN"]
    wq_val = women_quota  # PostgreSQL boolean
    sm_col = CATEGORY_TO_SM.get(category, "open_seats")

    placeholders = ",".join(["%s"] * len(categories))

    cur.execute(f"""
        SELECT
            c.college_code, c.college_name, c.category,
            c.women_quota, c.round,
            c.opening_rank, c.closing_rank, c.seats_filled,
            COALESCE(sm_g.section, 'UNKNOWN') AS section,
            sm_g.state_pool,
            COALESCE(sm_g.{sm_col}, 0) AS gen_cat_seats,
            COALESCE(sm_w.{sm_col}, 0) AS wom_cat_seats,
            COALESCE(sm_g.{sm_col}, 0) +
                CASE WHEN %s THEN COALESCE(sm_w.{sm_col}, 0) ELSE 0 END
                AS total_cat_seats
        FROM cutoffs c
        LEFT JOIN seat_matrix sm_g
            ON  sm_g.college_code = c.college_code
            AND sm_g.round        = c.round
            AND sm_g.row_type     = 'GEN'
            AND sm_g.year         = c.year
            AND sm_g.{sm_col}     <= COALESCE(sm_g.state_pool, 9999)
        LEFT JOIN seat_matrix sm_w
            ON  sm_w.college_code = c.college_code
            AND sm_w.round        = c.round
            AND sm_w.row_type     = 'WOM'
            AND sm_w.year         = c.year
            AND sm_w.{sm_col}     <= COALESCE(sm_w.state_pool, 9999)
        WHERE c.category     IN ({placeholders})
          AND c.women_quota  = %s
          AND c.year         = %s
          AND c.closing_rank IS NOT NULL
        ORDER BY c.college_code, c.category, c.round
    """, (wq_val, *categories, wq_val, year))

    rows = cur.fetchall()
    conn.close()

    # Group by college+category
    from collections import defaultdict
    groups: dict[tuple, dict] = defaultdict(lambda: {
        "college_name": "", "section": "", "total_seats": 0,
        "state_pool": 0, "rounds": {}
    })

    for row in rows:
        key = (row["college_code"], row["category"], bool(row["women_quota"]))
        g = groups[key]
        g["college_name"] = row["college_name"] or "Unknown"
        g["section"]      = row["section"]
        g["state_pool"]   = row["state_pool"] or 0
        if row["round"] == "R1" and row["total_cat_seats"]:
            g["total_seats"] = row["total_cat_seats"]
        elif not g["total_seats"] and row["total_cat_seats"]:
            g["total_seats"] = row["total_cat_seats"]
        g["rounds"][row["round"]] = RoundData(
            round        = row["round"],
            closing_rank = row["closing_rank"],
            seats_filled = row["seats_filled"] or 0,
        )

    result = PredictionResult(
        student_air = student_air,
        category    = category,
        women_quota = women_quota,
        year        = year,
    )

    for (code, cat, wq), g in groups.items():
        rounds = g["rounds"]
        if not rounds:
            continue

        r1_closing   = rounds["R1"].closing_rank if "R1" in rounds else 0
        if r1_closing == 0:
            # Use earliest available round
            r1_closing = min(rounds.values(), key=lambda r: r.closing_rank).closing_rank

        tier = _classify_tier(student_air, r1_closing)
        if tier is None:
            continue

        best_closing  = min(r.closing_rank for r in rounds.values())
        worst_closing = max(r.closing_rank for r in rounds.values())
        movement      = worst_closing - r1_closing

        r1_filled     = rounds["R1"].seats_filled if "R1" in rounds else \
                        list(rounds.values())[0].seats_filled
        fill_rate              = _compute_fill_rate(r1_filled, g["total_seats"])
        round_prob, per_round  = _compute_round_probability(student_air, rounds)

        # Skip colleges the student cannot get into in any round
        if round_prob == 0:
            continue

        confidence             = min(1.0, len([r for r in rounds if r in ROUND_WEIGHTS]) / 3)
        final_prob             = _final_probability(round_prob, fill_rate, movement, confidence, per_round)

        # Earliest round the student can get in
        earliest = next(
            (r for r in ["R1", "R2", "R3", "R4"] if per_round.get(r)), ""
        )

        rec = CollegeRecommendation(
            college_code      = code,
            college_name      = g["college_name"],
            category          = cat,
            women_quota       = wq,
            section           = g["section"],
            total_seats       = g["total_seats"],
            rounds            = rounds,
            r1_closing        = r1_closing,
            best_closing      = best_closing,
            worst_closing     = worst_closing,
            fill_rate         = fill_rate,
            seat_movement     = movement,
            round_probability = round_prob,
            confidence        = confidence,
            final_probability = final_prob,
            tier              = tier,
            r1_cleared        = per_round.get("R1", False),
            r2_cleared        = per_round.get("R2", False),
            r3_cleared        = per_round.get("R3", False),
            r4_cleared        = per_round.get("R4", False),
            earliest_round    = earliest,
        )

        if tier == "Safe":
            result.safe.append(rec)
        elif tier == "Moderate":
            result.moderate.append(rec)
        else:
            result.aggressive.append(rec)

    # Sort by R1 closing rank (best college first within each tier)
    result.safe       = sorted(result.safe,       key=lambda r: r.r1_closing)[:top_n]
    result.moderate   = sorted(result.moderate,   key=lambda r: r.r1_closing)[:top_n]
    result.aggressive = sorted(result.aggressive, key=lambda r: r.r1_closing)[:top_n]

    return result


# ── Display helper ────────────────────────────────────────────────────────────

def print_result(result: PredictionResult):
    print(f"\n{'='*75}")
    print(f"Student AIR: {result.student_air:,}  |  Category: {result.category}"
          f"{'  (Women quota)' if result.women_quota else ''}")
    print(f"{'='*75}")

    for tier_name, colleges in [
        ("SAFE", result.safe),
        ("MODERATE", result.moderate),
        ("AGGRESSIVE", result.aggressive),
    ]:
        if not colleges:
            continue
        print(f"\n{tier_name} — {len(colleges)} colleges")
        print(f"  {'Code':<6} {'College':<38} {'Cat':<6} {'R1-Close':>9} "
              f"{'Movement':>10} {'Fill%':>6} {'Prob':>6}")
        print(f"  {'-'*85}")
        for c in colleges[:15]:
            mv = f"+{c.seat_movement:,}" if c.seat_movement > 0 else str(c.seat_movement)
            fill = f"{c.fill_rate:.0%}" if c.total_seats > 0 else "  N/A"
            rnd_detail = " ".join(
                f"{r}={c.rounds[r].closing_rank:,}"
                for r in ["R1","R2","R3","R4"] if r in c.rounds
            )
            print(f"  {c.college_code:<6} {c.college_name[:37]:<38} "
                  f"{c.category:<6} {c.r1_closing:>9,} "
                  f"{mv:>10} {fill:>6} {c.final_probability:>5.0%}")

    total = len(result.all_colleges)
    print(f"\nTotal: {total} colleges in range  "
          f"({len(result.safe)} safe / "
          f"{len(result.moderate)} moderate / "
          f"{len(result.aggressive)} aggressive)")


# ── Test ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        (5000,  "OPEN",  False),
        (25000, "OBC",   False),
        (80000, "SC",    False),
        (15000, "SEBC",  False),
        (3000,  "OPEN",  True),   # women's quota
    ]
    for air, cat, wq in tests:
        r = predict(student_air=air, category=cat, women_quota=wq)
        print_result(r)
