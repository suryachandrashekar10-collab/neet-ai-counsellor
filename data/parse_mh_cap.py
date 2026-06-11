"""
Maharashtra CAP Round allotment PDF parser.
- Processes PDF in small page batches to avoid memory crashes
- Saves progress to SQLite after each batch (crash-safe resume)
- Zero dependencies beyond pdfplumber + Python stdlib
"""

import re
import sqlite3
import sys
from pathlib import Path
import pdfplumber

# ── Constants ────────────────────────────────────────────────────────────────

CATEGORY_CODES = {
    "OBC", "SC", "ST", "SEBC", "EWS",
    "VJA", "NTB", "NTC", "NTD",
    "HA", "D1", "D2", "D3",
    "ORP-A", "ORP-B", "ORP-C",
    "Min", "IQ"
}

QUOTA_TYPES = {
    "OPEN", "OBC", "SC", "ST", "SEBC", "EWS",
    "VJA", "NTB", "NTC", "NTD",
    "HA", "D1", "D2", "D3",
    "ORP-A", "ORP-B", "ORP-C",
    "Min", "IQ"
}

EARMARKS = {"EMD", "EMR"}
COLLEGE_CODE_RE = re.compile(r"^(\d{4}):(.*)$")

BATCH_SIZE = 10  # pages per batch — keep low to avoid memory issues

# ── Row parser ────────────────────────────────────────────────────────────────

def parse_row(row_words: list[dict]) -> dict | None:
    texts = [w["text"] for w in row_words]

    # Find gender (M/F) as pivot
    gender_idx = None
    for i, t in enumerate(texts):
        if t in ("M", "F"):
            gender_idx = i
            break
    if gender_idx is None:
        return None

    left = texts[:gender_idx]
    if len(left) < 4:
        return None

    # Find neet_roll (10 digits) and cet_form (9 digits) scanning right-to-left
    neet_idx = cet_idx = None
    for i in range(len(left) - 1, -1, -1):
        t = left[i]
        if t.isdigit():
            if cet_idx is None and len(t) == 9:
                cet_idx = i
            elif neet_idx is None and len(t) == 10:
                neet_idx = i
        if neet_idx is not None and cet_idx is not None:
            break

    # Fallback to positional
    if neet_idx is None or cet_idx is None:
        if len(left) >= 4 and left[2].isdigit() and left[3].isdigit():
            neet_idx, cet_idx = 2, 3
        else:
            return None

    if not left[0].isdigit() or not left[1].isdigit():
        return None

    sr_no = left[0]
    air   = left[1]
    name  = " ".join(left[max(neet_idx, cet_idx) + 1:]).strip()
    if not name:
        name = " ".join(left[4:]).strip()

    # Right of gender: category, quota, college
    right = texts[gender_idx + 1:]
    not_allotted = "Choice" in right
    category = quota_type = earmark = None
    women_quota = retained = False
    college_code = college_name = None

    i = 0
    while i < len(right):
        tok   = right[i]
        clean = tok.strip("()")

        if clean in CATEGORY_CODES and category is None and quota_type is None:
            category = clean
        elif clean in QUOTA_TYPES and quota_type is None:
            quota_type = clean
        elif clean == "W":
            women_quota = True
        elif clean in EARMARKS:
            earmark = clean
        elif clean in ("Ret.", "Change"):
            retained = True
        elif clean == "Not" and i + 1 < len(right) and right[i+1] == "Available":
            not_allotted = True
            i += 1
        else:
            m = COLLEGE_CODE_RE.match(tok)
            if m:
                college_code = m.group(1)
                parts = [m.group(2)] if m.group(2) else []
                for t2 in right[i + 1:]:
                    if t2.strip("()") not in ("Ret.", "No", "Change", ""):
                        parts.append(t2)
                college_name = " ".join(parts).strip()
                break
        i += 1

    if quota_type is None and not not_allotted:
        quota_type = "OPEN"

    return {
        "sr_no":        sr_no,
        "air":          int(air),
        "neet_roll":    texts[neet_idx],
        "cet_form":     texts[cet_idx],
        "name":         name,
        "gender":       texts[gender_idx],
        "category":     category or "OPEN",
        "quota":        quota_type,
        "women_quota":  1 if women_quota else 0,
        "earmark":      earmark,
        "retained":     1 if retained else 0,
        "allotted":     0 if not_allotted else 1,
        "college_code": college_code,
        "college_name": college_name,
    }


def parse_page(page) -> list[dict]:
    words = page.extract_words()
    if not words:
        return []
    # Group words by baseline (2px snap)
    rows: dict[int, list] = {}
    for w in words:
        baseline = round(w["top"] / 2) * 2
        rows.setdefault(baseline, []).append(w)
    records = []
    for baseline in sorted(rows):
        row_words = sorted(rows[baseline], key=lambda w: w["x0"])
        rec = parse_row(row_words)
        if rec:
            records.append(rec)
    return records


# ── SQLite helpers ────────────────────────────────────────────────────────────

def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS allotments (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            sr_no         TEXT,
            air           INTEGER,
            neet_roll     TEXT,
            cet_form      TEXT,
            name          TEXT,
            gender        TEXT,
            category      TEXT,
            quota         TEXT,
            women_quota   INTEGER,
            earmark       TEXT,
            retained      INTEGER,
            allotted      INTEGER,
            college_code  TEXT,
            college_name  TEXT,
            year          INTEGER,
            round         TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            file_key   TEXT PRIMARY KEY,
            last_page  INTEGER
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_air      ON allotments(air)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_college  ON allotments(college_code, category, round, year)
    """)
    conn.commit()
    return conn


def get_resume_page(conn: sqlite3.Connection, file_key: str) -> int:
    row = conn.execute(
        "SELECT last_page FROM progress WHERE file_key = ?", (file_key,)
    ).fetchone()
    return row[0] if row else 0


def save_batch(conn: sqlite3.Connection, records: list[dict], file_key: str, last_page: int):
    if records:
        conn.executemany("""
            INSERT INTO allotments
              (sr_no, air, neet_roll, cet_form, name, gender, category,
               quota, women_quota, earmark, retained, allotted,
               college_code, college_name, year, round)
            VALUES
              (:sr_no, :air, :neet_roll, :cet_form, :name, :gender, :category,
               :quota, :women_quota, :earmark, :retained, :allotted,
               :college_code, :college_name, :year, :round)
        """, records)
    conn.execute("""
        INSERT INTO progress(file_key, last_page)
        VALUES (?, ?)
        ON CONFLICT(file_key) DO UPDATE SET last_page = excluded.last_page
    """, (file_key, last_page))
    conn.commit()


# ── Main pipeline ─────────────────────────────────────────────────────────────

ROUND_MAP = {
    "SellList+R1-MBBS-BDS.pdf": ("R1", 2025),
    "SellList+R2-MBBS-BDS.pdf": ("R2", 2025),
    "SellList+R3-MBBS-BDS.pdf": ("R3", 2025),
    "SellList+R4-MBBS-BDS.pdf": ("R4", 2025),
    "SellList+R5-MBBS-BDS.pdf": ("R5", 2025),
}


def process_pdf(pdf_path: Path, round_no: str, year: int, conn: sqlite3.Connection):
    file_key = pdf_path.name
    start_page = get_resume_page(conn, file_key)

    with pdfplumber.open(str(pdf_path)) as pdf:
        total = len(pdf.pages)

        if start_page >= total:
            print(f"  {file_key}: already complete ({total} pages)")
            return

        if start_page > 0:
            print(f"  {file_key}: resuming from page {start_page + 1}/{total}")
        else:
            print(f"  {file_key}: starting ({total} pages, batch size={BATCH_SIZE})")

        page_num = start_page
        while page_num < total:
            batch_end  = min(page_num + BATCH_SIZE, total)
            batch_recs = []

            for p in range(page_num, batch_end):
                recs = parse_page(pdf.pages[p])
                for r in recs:
                    r["year"]  = year
                    r["round"] = round_no
                batch_recs.extend(recs)

            save_batch(conn, batch_recs, file_key, batch_end)
            print(f"    pages {page_num + 1}–{batch_end}/{total}  "
                  f"({len(batch_recs)} rows saved)", flush=True)
            page_num = batch_end

    print(f"  {file_key}: done")


def print_summary(conn: sqlite3.Connection):
    total = conn.execute("SELECT COUNT(*) FROM allotments").fetchone()[0]
    allotted = conn.execute("SELECT COUNT(*) FROM allotments WHERE allotted=1").fetchone()[0]
    colleges = conn.execute("SELECT COUNT(DISTINCT college_code) FROM allotments WHERE college_code IS NOT NULL").fetchone()[0]
    print(f"\n{'='*50}")
    print(f"  Total rows     : {total:,}")
    print(f"  Allotted seats : {allotted:,}")
    print(f"  Unique colleges: {colleges}")
    print("\n  Category breakdown:")
    for row in conn.execute(
        "SELECT category, COUNT(*) as n FROM allotments GROUP BY category ORDER BY n DESC"
    ):
        print(f"    {row[0]:10s}: {row[1]:,}")
    print("\n  Per round:")
    for row in conn.execute(
        "SELECT round, COUNT(*) as n FROM allotments GROUP BY round ORDER BY round"
    ):
        print(f"    {row[0]:5s}: {row[1]:,}")


if __name__ == "__main__":
    raw_dir = Path("data/raw/2025")
    db_path = "data/mh_cap_2025.db"

    conn = init_db(db_path)
    print(f"Database: {db_path}\n")

    for filename, (round_no, year) in ROUND_MAP.items():
        pdf_path = raw_dir / filename
        if not pdf_path.exists():
            print(f"SKIP (not found): {filename}")
            continue
        process_pdf(pdf_path, round_no, year, conn)

    print_summary(conn)
    conn.close()
    print(f"\nDone. Open {db_path} to query the data.")
