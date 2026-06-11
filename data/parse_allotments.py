"""
Maharashtra CAP Allotment PDF Parser — batch mode, 50 pages at a time.

Parses SellList PDFs and cross-validates against existing SQL Server data.
Reports mismatches before touching anything.

Usage:
    python data\parse_allotments.py --pdf data\raw\2025\SellList+R1-MBBS-BDS.pdf --round R1 --batch 50
    python data\parse_allotments.py --pdf data\raw\2025\SellList+R1-MBBS-BDS.pdf --round R1 --batch 50 --apply
"""

import re
import sys
import argparse
import pdfplumber
import pyodbc
from dataclasses import dataclass
from typing import Optional

# ── DB connection ─────────────────────────────────────────────────────────────

def get_conn():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost\\SQLEXPRESS;"
        "DATABASE=neet_counsellor;Trusted_Connection=yes;"
    )

# ── Constants ─────────────────────────────────────────────────────────────────

SKIP_PATTERNS = [
    re.compile(r"^-{5,}"),                         # separator lines
    re.compile(r"^Sr\.\s+AIR"),                     # header row 1
    re.compile(r"^No\.\s+Roll"),                    # header row 2
    re.compile(r"^Printed\s+On"),                   # page stamp
    re.compile(r"^Note\s*:"),                       # notes
    re.compile(r"^\d+\.\s+[A-Z].*admission"),       # numbered notes
    re.compile(r"^IQ=|^W=|^EMD=|^EMR=|^ORP"),      # legend
    re.compile(r"^This\s+list|^Candidates|^The\s+"), # prose lines
    re.compile(r"^\s*$"),                            # blank lines
]

# College pattern: 3-5 digit code followed by colon
COLLEGE_RE = re.compile(r"(\d{3,5}):(.+)$")

# Earmarks in parentheses e.g. (W), (EMD), (EMR), (EMD, W)
EARMARK_PAREN_RE = re.compile(r"\(([^)]+)\)")

# PWD compound categories
PWD_TOKENS = {"PWD", "PH"}

# Known quota keywords (helps separate quota from earmark)
QUOTA_KEYWORDS = {
    "OPEN", "OBC", "SC", "ST", "SEBC", "EWS", "NTB", "NTC", "NTD", "VJA",
    "PWD-OPEN", "PWD-OBC", "PWD-SC", "PWD-ST", "PWD-SEBC", "PWD-EWS",
    "PWD-NTB", "PWD-NTC", "PWD-NTD", "PWD-VJA",
    "EMOBC", "EMSC", "EMST", "EMNTB", "EMNTC", "EMNTD", "EMVJA", "EMSEBC",
    "EMEWS", "EMOPEN", "EMNTD",
    "DEF1", "DEF2", "DEF3",
    "HOPEN", "HOBC", "HSC", "HST", "HNTS", "HEWS", "HOPENW", "HOBCW",
    "OBC(W)", "OPEN(W)",
    "MIN", "IQ",
}

# ── Row dataclass ─────────────────────────────────────────────────────────────

@dataclass
class ParsedRow:
    sr_no:        str
    air:          int
    neet_roll:    str
    cet_form:     str
    name:         str
    gender:       str
    category:     str
    quota:        Optional[str]
    women_quota:  bool
    earmark:      Optional[str]
    college_code: Optional[str]
    college_name: Optional[str]
    allotted:     bool
    page:         int
    raw:          str           # original line for debugging

# ── Line parser ───────────────────────────────────────────────────────────────

def should_skip(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    for pat in SKIP_PATTERNS:
        if pat.search(stripped):
            return True
    return False


def parse_line(line: str, page: int) -> Optional[ParsedRow]:
    """
    Parse one data line from the PDF.
    Format (space-separated, fixed-width columns):
        sr_no  air  neet_roll  cet_form  name...  [M|F]  cat [quota] [earmarks] [college_code:college_name]
    Gender M/F is the reliable anchor between name and category.
    """
    stripped = line.strip()

    # Must start with a number (sr_no)
    if not re.match(r"^\d+\s", stripped):
        return None

    # Split at gender anchor [M|F] — rightmost occurrence before category section
    # Gender is a standalone M or F surrounded by spaces
    gender_match = list(re.finditer(r"\s([MF])\s", stripped))
    if not gender_match:
        return None

    # Take the LAST gender match (handles names with M/F initials)
    gm = gender_match[-1]
    gender = gm.group(1)
    left  = stripped[:gm.start()].strip()   # sr_no air neet cet name
    right = stripped[gm.end():].strip()     # category quota earmarks college

    # Parse left side: sr_no air neet_roll cet_form name
    left_parts = left.split()
    if len(left_parts) < 4:
        return None
    try:
        sr_no     = left_parts[0]
        air       = int(left_parts[1])
        neet_roll = left_parts[2]
        cet_form  = left_parts[3]
        name      = " ".join(left_parts[4:]) if len(left_parts) > 4 else ""
    except (ValueError, IndexError):
        return None

    # Validate key numeric fields
    if air <= 0 or air > 2000000:
        return None
    if len(neet_roll) < 9 or len(cet_form) < 8:
        return None

    # Parse right side: category quota earmarks college
    # PDF column order after gender: <category> <quota> [earmarks] [college]
    # Step 1: extract college (4+ digit code : name at the end)
    college_code = None
    college_name = None
    allotted = False

    col_match = COLLEGE_RE.search(right)
    if col_match:
        college_code = col_match.group(1)
        college_name = col_match.group(2).strip()
        allotted = True
        right = right[:col_match.start()].strip()
    elif "Choice Not Available" in right:
        allotted = False
        right = right.replace("Choice Not Available", "").strip()

    # Step 2: extract parenthetical earmarks e.g. (W), (EMD), (EMR)
    paren_earmarks = EARMARK_PAREN_RE.findall(right)
    right = EARMARK_PAREN_RE.sub("", right).strip()

    # Step 3: split remaining into tokens
    tokens = right.split()

    # Step 4: pull trailing bare earmarks (PH, W) from the end
    # W is typically in parens but sometimes bare; PH is always bare
    TRAILING_EARMARKS = {"PH", "W"}
    bare_earmarks = []
    while tokens and tokens[-1].upper() in TRAILING_EARMARKS:
        bare_earmarks.insert(0, tokens.pop())

    # Step 5: first token = student category (always)
    if not tokens:
        category = "OPEN"
        quota = None
    else:
        category = tokens[0].upper()
        remaining = tokens[1:]

        # Normalise compound no-space suffixes on category token
        # SEBCPWD → SEBC + PWD earmark; SEBCHA → SEBC + HA quota; SEBCD1 → SEBC + D1
        m_pwd = re.match(r"^(OPEN|OBC|SC|ST|SEBC|EWS|NTB|NTC|NTD|VJA)(PWD)$", category)
        m_ha  = re.match(r"^(OPEN|OBC|SC|ST|SEBC|EWS|NTB|NTC|NTD|VJA)(HA)$", category)
        m_d   = re.match(r"^(OPEN|OBC|SC|ST|SEBC|EWS|NTB|NTC|NTD|VJA)(D\d+)$", category)
        if m_pwd:
            category = m_pwd.group(1)
            bare_earmarks.insert(0, "PWD")
        elif m_ha:
            category = m_ha.group(1)
            # HA acts as a quota modifier — prepend to remaining
            remaining = ["HA"] + remaining
        elif m_d:
            category = m_d.group(1)
            remaining = [m_d.group(2)] + remaining

        # SOBC → OBC (Maharashtra "State OBC" appears as SOBC in some printouts)
        if category == "SOBC":
            category = "OBC"

        # Special: IQ / I.Q. seats count as OPEN
        if category in ("I.Q.", "IQ", "I.Q"):
            category = "OPEN"

        # MKB (Maratha-Kunabi-Bhakar) — treat as OPEN for prediction
        if category in ("MKB", "MINO"):
            pass  # keep as-is, these are real quota types

        # If next token is bare "PWD" (disability modifier), treat as earmark
        if remaining and remaining[0].upper() == "PWD":
            bare_earmarks.insert(0, "PWD")
            remaining = remaining[1:]

        # Remaining tokens = quota string (e.g. "OPEN", "PWD-OPEN", "ST", "HA")
        # But guard against city names bleeding in (e.g. "SOLAPUR", "MUMBAI")
        # City names appear when the college_code pattern wasn't matched (3-digit codes etc.)
        # If remaining contains a known city-like token (all caps, no digits, len > 5),
        # and we don't have a college code yet, skip those tokens
        filtered_remaining = []
        for t in remaining:
            # Keep if it looks like a quota code (short, no space, known pattern)
            # Drop if it looks like a place name (long, all alpha, >5 chars not a known quota)
            if re.match(r"^[A-Z]{6,}$", t) and t not in {
                "EMOPEN", "EMSEBC", "EMOBC", "EMNTB", "EMNTC", "EMNTD", "EMVJA",
                "EMOBCW", "EMSEBCW", "EMEWSW", "MINO", "MKB", "DEF1", "DEF2", "DEF3",
                "HOPEN", "HOBC", "EMNTD"
            }:
                continue  # skip city names
            filtered_remaining.append(t)

        raw_quota = " ".join(filtered_remaining).strip() or None
        # Hard-cap quota at 20 chars — anything longer is a parsing artifact
        quota = raw_quota[:20] if raw_quota else None

    # Build earmark string — combine parens + bare
    all_earmarks = paren_earmarks + bare_earmarks
    earmark = ", ".join(all_earmarks) if all_earmarks else None

    # Women quota: W in earmarks
    women_quota = "W" in all_earmarks

    return ParsedRow(
        sr_no=sr_no, air=air, neet_roll=neet_roll, cet_form=cet_form,
        name=name, gender=gender, category=category, quota=quota,
        women_quota=women_quota, earmark=earmark,
        college_code=college_code, college_name=college_name,
        allotted=allotted, page=page, raw=stripped,
    )

# ── PDF batch reader ──────────────────────────────────────────────────────────

def parse_pdf_batch(pdf_path: str, start_page: int, end_page: int) -> list[ParsedRow]:
    """Parse pages [start_page, end_page) (0-indexed)."""
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        end_page = min(end_page, total)
        for i in range(start_page, end_page):
            page = pdf.pages[i]
            text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
            for line in text.splitlines():
                if should_skip(line):
                    continue
                parsed = parse_line(line, i + 1)
                if parsed:
                    rows.append(parsed)
    return rows

# ── Validation against SQL Server ─────────────────────────────────────────────

def load_db_rows(conn, round_label: str) -> dict:
    """Load existing allotment rows keyed by neet_roll."""
    cur = conn.cursor()
    cur.execute("""
        SELECT neet_roll, cet_form, air, name, category, quota, earmark,
               women_quota, college_code, college_name, allotted
        FROM allotments
        WHERE round = ?
    """, (round_label,))
    result = {}
    for r in cur.fetchall():
        result[r.neet_roll] = r
    return result


def compare(parsed: ParsedRow, db_row) -> list[str]:
    """Return list of field differences between parsed and DB row."""
    diffs = []

    def norm(v):
        if v is None:
            return ""
        return str(v).strip().upper()

    # category: core fix target
    pcat, dcat = norm(parsed.category), norm(db_row.category)
    if pcat != dcat:
        diffs.append(f"category: PDF='{pcat}' DB='{dcat}'")

    # quota: treat '' and 'OPEN' as equivalent (original parser defaulted to OPEN)
    pquo, dquo = norm(parsed.quota), norm(db_row.quota)
    if pquo != dquo and not (pquo in ("", "OPEN") and dquo in ("", "OPEN")):
        diffs.append(f"quota: PDF='{pquo}' DB='{dquo}'")

    # earmark: ignore W-only differences since women_quota boolean covers it
    pear = norm(parsed.earmark)
    dear = norm(db_row.earmark)
    # Strip W from both sides for comparison (it's in women_quota boolean)
    pear_no_w = ", ".join(e for e in pear.split(", ") if e.strip() not in ("W", ""))
    dear_no_w = ", ".join(e for e in dear.split(", ") if e.strip() not in ("W", ""))
    if pear_no_w != dear_no_w:
        diffs.append(f"earmark: PDF='{pear}' DB='{dear}'")

    # women_quota: actual boolean mismatch
    pwq = bool(parsed.women_quota)
    dwq = bool(db_row.women_quota)
    if pwq != dwq:
        diffs.append(f"women_quota: PDF='{pwq}' DB='{dwq}'")

    # college_code and allotted
    if norm(parsed.college_code) != norm(db_row.college_code):
        diffs.append(f"college_code: PDF='{norm(parsed.college_code)}' DB='{norm(db_row.college_code)}'")
    if parsed.allotted != bool(db_row.allotted):
        diffs.append(f"allotted: PDF='{parsed.allotted}' DB='{bool(db_row.allotted)}'")

    return diffs

# ── Apply corrections ─────────────────────────────────────────────────────────

def apply_correction(conn, parsed: ParsedRow, round_label: str):
    cur = conn.cursor()
    cur.execute("""
        UPDATE allotments
        SET category     = ?,
            quota        = ?,
            earmark      = ?,
            women_quota  = ?,
            college_code = ?,
            college_name = ?,
            allotted     = ?
        WHERE neet_roll = ? AND round = ?
    """, (
        parsed.category,
        parsed.quota,
        parsed.earmark,
        1 if parsed.women_quota else 0,
        parsed.college_code,
        parsed.college_name,
        1 if parsed.allotted else 0,
        parsed.neet_roll,
        round_label,
    ))
    conn.commit()

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf",   required=True,  help="Path to SellList PDF")
    parser.add_argument("--round", required=True,  help="Round label e.g. R1")
    parser.add_argument("--batch", type=int, default=50, help="Pages per batch")
    parser.add_argument("--start", type=int, default=0,  help="Start page (0-indexed)")
    parser.add_argument("--apply", action="store_true",  help="Apply corrections to DB")
    args = parser.parse_args()

    conn = get_conn()
    print(f"\nLoading existing DB rows for {args.round}...")
    db_rows = load_db_rows(conn, args.round)
    print(f"  {len(db_rows):,} rows in DB for {args.round}")

    with pdfplumber.open(args.pdf) as pdf:
        total_pages = len(pdf.pages)
    print(f"  {total_pages:,} pages in PDF\n")

    total_parsed   = 0
    total_matched  = 0
    total_mismatch = 0
    total_missing  = 0   # in PDF but not in DB
    total_fixed    = 0

    start = args.start
    while start < total_pages:
        end = min(start + args.batch, total_pages)
        print(f"-- Batch pages {start+1}-{end} of {total_pages} --")

        rows = parse_pdf_batch(args.pdf, start, end)
        print(f"   Parsed {len(rows)} rows")

        batch_mismatch = 0
        batch_missing  = 0

        for r in rows:
            total_parsed += 1
            db = db_rows.get(r.neet_roll)

            if db is None:
                batch_missing += 1
                total_missing += 1
                if batch_missing <= 3:   # show first 3 per batch
                    print(f"   [MISSING IN DB] AIR={r.air:,} {r.name} roll={r.neet_roll}")
                continue

            diffs = compare(r, db)
            if diffs:
                batch_mismatch += 1
                total_mismatch += 1
                print(f"   [MISMATCH] AIR={r.air:,} {r.name[:30]}")
                for d in diffs:
                    print(f"             {d}")
                if args.apply:
                    apply_correction(conn, r, args.round)
                    total_fixed += 1
            else:
                total_matched += 1

        print(f"   Mismatches: {batch_mismatch}  Missing: {batch_missing}\n")
        start = end

    conn.close()

    print("=" * 60)
    print(f"SUMMARY for {args.round}")
    print(f"  Total parsed from PDF : {total_parsed:,}")
    print(f"  Matched (no diff)     : {total_matched:,}")
    print(f"  Mismatches found      : {total_mismatch:,}")
    print(f"  Missing in DB         : {total_missing:,}")
    if args.apply:
        print(f"  Corrections applied   : {total_fixed:,}")
    else:
        print(f"  (Run with --apply to fix mismatches)")
    print("=" * 60)


if __name__ == "__main__":
    main()
