"""
Parse Maharashtra CAP Seat Matrix PDFs.

Column order after GEN./WOM. token:
  SC  ST  VJ  N1(NTB)  N2(NTC)  N3(NTD)  OBC  OBC_TOT  SEBC  EWS  OPEN | STATE_TOT BAL | D1 D2 D3 MK IQ IQ_TOT | GRAND BAL
"""

import re
import pyodbc
from pathlib import Path
import pdfplumber

SQL_SERVER = r"localhost\SQLEXPRESS"
DB_NAME    = "neet_counsellor"

NUM_RE         = re.compile(r"\d+")
# Captures: code, name, govt_aided, intake, then remaining text (for AIQ/GOI extraction)
COLLEGE_HDR_RE = re.compile(r"^\s*\d{1,3}\s+(\d{4})\s+(.+?)\s+([YN])\s+(\d+)\s+(.*)")
AIQ_RE         = re.compile(r"^(\d+)\s*(?:(\d+)\s+)?GEN\.")  # AIQ [GOI] GEN.


def parse_nums(text: str) -> list[int]:
    return [int(x) for x in NUM_RE.findall(text)]


def nums_to_record(college: dict, row_type: str, nums: list[int],
                   round_name: str, year: int) -> dict | None:
    if len(nums) < 11:
        return None
    # nums: SC ST VJ NTB NTC NTD OBC OBC_TOT SEBC EWS OPEN [STATE_TOT BAL ...]
    state_total = nums[12] if len(nums) > 12 else nums[11] if len(nums) > 11 else 0
    state_pool  = college["intake"] - college["aiq"] - college["goi"]
    return {
        "college_code": college["code"],
        "college_name": college["name"],
        "intake":       college["intake"],
        "aiq":          college["aiq"],
        "goi":          college["goi"],
        "state_pool":   state_pool,
        "section":      college["section"],
        "row_type":     row_type,
        "sc_seats":     nums[0],
        "st_seats":     nums[1],
        "vja_seats":    nums[2],
        "ntb_seats":    nums[3],
        "ntc_seats":    nums[4],
        "ntd_seats":    nums[5],
        "obc_seats":    nums[6],
        "sebc_seats":   nums[8],
        "ews_seats":    nums[9],
        "open_seats":   nums[10],
        "state_total":  state_total,
        "round":        round_name,
        "year":         year,
    }


def detect_section(line: str) -> str | None:
    if "GOVT. COLLEGES: MBBS" in line or "GOVT. COLLEGES : MBBS" in line:
        return "GOVT_MBBS"
    if "GOVT. COLLEGES: BDS" in line or "GOVT. COLLEGES : BDS" in line:
        return "GOVT_BDS"
    if "PVT. COLLEGES: MBBS" in line or ("PRIVATE" in line and "MBBS" in line):
        return "PVT_MBBS"
    if "PVT. COLLEGES: BDS" in line or ("PRIVATE" in line and "BDS" in line):
        return "PVT_BDS"
    if "MINORITY" in line and "MBBS" in line:
        return "MIN_MBBS"
    if "MINORITY" in line and "BDS" in line:
        return "MIN_BDS"
    return None


def parse_pdf(pdf_path: str, round_name: str, year: int) -> list[dict]:
    records   = []
    college   = None
    section   = "GOVT_MBBS"

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            for raw_line in text.splitlines():
                line = raw_line.strip()
                if not line or line.startswith("---"):
                    continue

                # Section detection
                sec = detect_section(line)
                if sec:
                    section = sec
                    continue

                # Skip pure header/notes lines
                if any(line.startswith(p) for p in
                       ["Sr ", "Aided", "Admissions", "Provisional", "Legends",
                        "Note", "1.", "2.", "3.", "Status"]):
                    continue

                # ── College header line ───────────────────────────────────
                m = COLLEGE_HDR_RE.match(line)
                if m:
                    code      = m.group(1)
                    name      = m.group(2).strip()
                    intake    = int(m.group(4))
                    remainder = m.group(5)  # text after intake: "38 2 GEN. ..." or "38 GEN. ..."

                    # Extract AIQ and optional GOI from remainder before GEN.
                    aiq, goi = 0, 0
                    aiq_m = AIQ_RE.match(remainder.strip())
                    if aiq_m:
                        aiq = int(aiq_m.group(1))
                        goi = int(aiq_m.group(2)) if aiq_m.group(2) else 0

                    college = {"code": code, "name": name, "intake": intake,
                               "aiq": aiq, "goi": goi, "section": section}

                    # GEN. data is always on this same line
                    if "GEN." in line:
                        after = line[line.index("GEN.") + 4:]
                        rec = nums_to_record(college, "GEN", parse_nums(after),
                                             round_name, year)
                        if rec:
                            records.append(rec)
                    continue

                # ── WOM. row ──────────────────────────────────────────────
                # May have college name continuation prefix: "THANE WOM. 3 2..."
                if "WOM." in line and college:
                    after = line[line.index("WOM.") + 4:]
                    rec = nums_to_record(college, "WOM", parse_nums(after),
                                         round_name, year)
                    if rec:
                        records.append(rec)
                    continue

    print(f"  {Path(pdf_path).name}: {len(records)} rows")
    return records


def load_to_sqlserver(records: list[dict]):
    if not records:
        print("No records to load.")
        return

    conn = pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={DB_NAME};"
        f"Trusted_Connection=yes;",
        autocommit=True
    )
    cur = conn.cursor()

    cur.execute("IF OBJECT_ID('seat_matrix','U') IS NOT NULL DROP TABLE seat_matrix")
    cur.execute("""
        CREATE TABLE seat_matrix (
            id            INT IDENTITY PRIMARY KEY,
            college_code  VARCHAR(6),
            college_name  NVARCHAR(100),
            intake        INT,
            aiq           INT,          -- All India Quota seats (go to MCC)
            goi           INT,          -- Govt of India nominee seats
            state_pool    INT,          -- intake - aiq - goi = actual state seats
            section       VARCHAR(20),
            row_type      VARCHAR(5),   -- GEN or WOM
            sc_seats      INT, st_seats   INT, vja_seats  INT,
            ntb_seats     INT, ntc_seats  INT, ntd_seats  INT,
            obc_seats     INT, sebc_seats INT, ews_seats  INT,
            open_seats    INT, state_total INT,
            round         VARCHAR(5),
            year          SMALLINT
        )
    """)
    cur.execute("""
        CREATE INDEX idx_sm_lookup
        ON seat_matrix(college_code, row_type, round, year)
    """)

    cur.executemany("""
        INSERT INTO seat_matrix
          (college_code, college_name, intake, aiq, goi, state_pool,
           section, row_type,
           sc_seats, st_seats, vja_seats, ntb_seats, ntc_seats, ntd_seats,
           obc_seats, sebc_seats, ews_seats, open_seats, state_total, round, year)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, [(r["college_code"], r["college_name"], r["intake"], r["aiq"], r["goi"],
           r["state_pool"], r["section"], r["row_type"],
           r["sc_seats"], r["st_seats"], r["vja_seats"],
           r["ntb_seats"], r["ntc_seats"], r["ntd_seats"], r["obc_seats"],
           r["sebc_seats"], r["ews_seats"], r["open_seats"], r["state_total"],
           r["round"], r["year"]) for r in records])

    total = cur.execute("SELECT COUNT(*) FROM seat_matrix").fetchone()[0]
    print(f"\nLoaded {total:,} rows into seat_matrix")

    print("\nSample — GEN + WOM seats for govt MBBS colleges R1:")
    for row in cur.execute("""
        SELECT g.college_code, g.college_name,
               g.intake, g.aiq, g.goi, g.state_pool,
               g.sc_seats  + COALESCE(w.sc_seats,0)   AS sc_total,
               g.obc_seats + COALESCE(w.obc_seats,0)  AS obc_total,
               g.open_seats+ COALESCE(w.open_seats,0) AS open_total,
               g.state_total + COALESCE(w.state_total,0) AS state_total
        FROM seat_matrix g
        LEFT JOIN seat_matrix w
            ON w.college_code=g.college_code AND w.round=g.round
            AND w.year=g.year AND w.row_type='WOM'
        WHERE g.round='R1' AND g.row_type='GEN' AND g.section='GOVT_MBBS'
        ORDER BY g.college_code
    """):
        print(f"  {row.college_code}  {row.college_name:35s} "
              f"intake={row.intake} AIQ={row.aiq} GOI={row.goi} "
              f"state_pool={row.state_pool} "
              f"SC={row.sc_total} OBC={row.obc_total} "
              f"OPEN={row.open_total} Total={row.state_total}")

    conn.close()


ROUND_MAP = {
    "SeatMatrix-MBBSBDS-R1.pdf": ("R1", 2025),
    "SeatMatrix-MBBSBDS-R2.pdf": ("R2", 2025),
    "SeatMatrix-MBBSBDS-R3.pdf": ("R3", 2025),
    "SeatMatrix-MBBSBDS-R4.pdf": ("R4", 2025),
    "SeatMatrix-MBBSBDS-IL.pdf": ("IL", 2025),
}

if __name__ == "__main__":
    raw_dir     = Path("data/raw/2025")
    all_records = []

    for filename, (round_no, year) in ROUND_MAP.items():
        pdf_path = raw_dir / filename
        if not pdf_path.exists():
            print(f"SKIP: {filename}")
            continue
        all_records.extend(parse_pdf(str(pdf_path), round_no, year))

    print(f"\nTotal records parsed: {len(all_records)}")
    load_to_sqlserver(all_records)
