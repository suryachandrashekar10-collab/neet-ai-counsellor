from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from prediction_engine import predict, CollegeRecommendation

app = FastAPI(
    title="NEET Maharashtra CAP Counsellor API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request / Response models ─────────────────────────────────────────────────

VALID_CATEGORIES = {
    "OPEN", "OBC", "SC", "ST", "SEBC", "EWS",
    "VJA", "NTB", "NTC", "NTD", "HA", "D1", "D2", "D3"
}

class PredictRequest(BaseModel):
    air:         int             = Field(..., gt=0, le=2000000, description="All India Rank")
    category:    str             = Field(..., description="e.g. OPEN, OBC, SC, ST, SEBC, EWS")
    women_quota: bool            = Field(False,  description="Include women's quota seats")
    year:        int             = Field(2025,   description="Counselling year")
    top_n:       int             = Field(50,     ge=1, le=100)

class RoundInfo(BaseModel):
    round:        str
    closing_rank: int
    seats_filled: int

class CollegeOut(BaseModel):
    college_code:      str
    college_name:      str
    category:          str
    women_quota:       bool
    section:           str
    total_seats:       int
    r1_closing:        int
    best_closing:      int
    worst_closing:     int
    fill_rate:         float
    seat_movement:     int
    round_probability: float
    final_probability: float
    tier:              str
    rounds:            dict[str, RoundInfo]
    r1_cleared:        bool
    r2_cleared:        bool
    r3_cleared:        bool
    r4_cleared:        bool
    earliest_round:    str

class PredictResponse(BaseModel):
    student_air:     int
    category:        str
    women_quota:     bool
    year:            int
    safe:            list[CollegeOut]
    moderate:        list[CollegeOut]
    aggressive:      list[CollegeOut]
    total_options:   int
    safe_count:      int
    moderate_count:  int
    aggressive_count: int

# ── Helpers ───────────────────────────────────────────────────────────────────

def college_to_out(c: CollegeRecommendation) -> CollegeOut:
    return CollegeOut(
        college_code      = c.college_code,
        college_name      = c.college_name,
        category          = c.category,
        women_quota       = c.women_quota,
        section           = c.section,
        total_seats       = c.total_seats,
        r1_closing        = c.r1_closing,
        best_closing      = c.best_closing,
        worst_closing     = c.worst_closing,
        fill_rate         = round(c.fill_rate, 3),
        seat_movement     = c.seat_movement,
        round_probability = round(c.round_probability, 3),
        final_probability = round(c.final_probability, 3),
        tier              = c.tier,
        rounds            = {
            r: RoundInfo(
                round        = d.round,
                closing_rank = d.closing_rank,
                seats_filled = d.seats_filled,
            )
            for r, d in c.rounds.items()
        },
        r1_cleared        = c.r1_cleared,
        r2_cleared        = c.r2_cleared,
        r3_cleared        = c.r3_cleared,
        r4_cleared        = c.r4_cleared,
        earliest_round    = c.earliest_round,
    )

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/predict", response_model=PredictResponse)
def predict_colleges(req: PredictRequest):
    cat = req.category.upper().strip()
    if cat not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid category '{cat}'. Valid: {sorted(VALID_CATEGORIES)}"
        )

    result = predict(
        student_air  = req.air,
        category     = cat,
        women_quota  = req.women_quota,
        year         = req.year,
        top_n        = req.top_n,
    )

    return PredictResponse(
        student_air      = result.student_air,
        category         = result.category,
        women_quota      = result.women_quota,
        year             = result.year,
        safe             = [college_to_out(c) for c in result.safe],
        moderate         = [college_to_out(c) for c in result.moderate],
        aggressive       = [college_to_out(c) for c in result.aggressive],
        total_options    = len(result.all_colleges),
        safe_count       = len(result.safe),
        moderate_count   = len(result.moderate),
        aggressive_count = len(result.aggressive),
    )


@app.get("/colleges")
def list_colleges(year: int = 2025):
    """Return all colleges with their seat matrix info."""
    import pyodbc
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        r"SERVER=localhost\SQLEXPRESS;"
        "DATABASE=neet_counsellor;Trusted_Connection=yes;"
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT college_code, college_name, section
        FROM seat_matrix
        WHERE round = 'R1' AND year = ? AND row_type = 'GEN'
        ORDER BY college_code
    """, (year,))
    rows = cur.fetchall()
    conn.close()
    return [{"code": r.college_code, "name": r.college_name,
             "section": r.section} for r in rows]


@app.get("/cutoffs/{college_code}")
def college_cutoffs(college_code: str, year: int = 2025):
    """Return all cutoff data for a specific college across rounds and categories."""
    import pyodbc
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        r"SERVER=localhost\SQLEXPRESS;"
        "DATABASE=neet_counsellor;Trusted_Connection=yes;"
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT category, women_quota, round,
               opening_rank, closing_rank, seats_filled
        FROM cutoffs
        WHERE college_code = ? AND year = ?
        ORDER BY category, women_quota, round
    """, (college_code.upper(), year))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No data for college {college_code}")
    return [
        {
            "category":     r.category,
            "women_quota":  bool(r.women_quota),
            "round":        r.round,
            "opening_rank": r.opening_rank,
            "closing_rank": r.closing_rank,
            "seats_filled": r.seats_filled,
        }
        for r in rows
    ]


@app.get("/categories")
def list_categories():
    return {"categories": sorted(VALID_CATEGORIES)}
