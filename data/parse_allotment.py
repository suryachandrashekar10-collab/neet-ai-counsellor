"""
Parse MCC NEET UG allotment result PDFs into structured CSV.

Each row in the PDF represents one allotment:
  S.No | Roll Number | Quota | College Name + Address | Course | Category | Status
"""

import re
import csv
import sys
from pathlib import Path
import pdfplumber


# Known quota types as they appear in the PDF
QUOTA_PATTERNS = [
    "All India",
    "Non-Resident Indian",
    "Delhi University",
    "Central University",
    "Deemed University",
    "ESIC",
    "B.Sc Nursing All India",
    "Armed Forces",
]

COURSE_PATTERNS = ["MBBS", "BDS", "B.Sc. Nursing", "B.Sc Nursing"]

CATEGORY_PATTERNS = [
    "UR", "OBC", "SC", "ST", "EWS",
    "OBC PwD", "SC PwD", "ST PwD", "UR PwD", "EWS PwD",
    "Open",
]


def extract_text(pdf_path: str) -> str:
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n".join(text_parts)


def parse_allotment_block(block: str) -> dict | None:
    """Parse a single allotment record from a text block."""
    lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
    if not lines:
        return None

    # First line: S.No + Roll Number + start of Quota
    first = lines[0]
    m = re.match(r"^(\d+)\s+(\d+)\s+(.+)$", first)
    if not m:
        return None

    sno = m.group(1)
    roll = m.group(2)
    rest = m.group(3)

    # Detect quota from known patterns
    quota = None
    for q in QUOTA_PATTERNS:
        if rest.startswith(q):
            quota = q
            rest = rest[len(q):].strip()
            break
    if not quota:
        quota = rest.split()[0] if rest else "Unknown"

    # Detect course
    course = None
    for c in COURSE_PATTERNS:
        if c in block:
            course = c
            break

    # Detect allotted category (appears before "Allotted")
    allotted_category = None
    allotted_match = re.search(
        r"(UR PwD|OBC PwD|SC PwD|ST PwD|EWS PwD|UR|OBC|SC|ST|EWS|Open)\s+Allotted",
        block
    )
    if allotted_match:
        allotted_category = allotted_match.group(1)

    # NRI priority
    nri_priority = None
    nri_match = re.search(r"NRI\s+Priority\s*:\s*(\d+)", block)
    if nri_match:
        nri_priority = nri_match.group(1)

    # College name: everything between quota and the course keyword
    # Join all lines and extract college block
    full = " ".join(lines)
    college_name = None
    state = None
    pincode = None

    # Pincode is a 6-digit number near end of address
    pin_match = re.search(r"\b(\d{6})\b", full)
    if pin_match:
        pincode = pin_match.group(1)

    # State appears before pincode in the address
    state_match = re.search(r",\s*([A-Za-z\s()]+),\s*\d{6}", full)
    if state_match:
        state = state_match.group(1).strip()

    # College name: after quota, before first comma in address
    college_match = re.search(
        rf"{re.escape(quota)}\s+(.+?),", full
    )
    if college_match:
        college_name = college_match.group(1).strip()

    return {
        "sno": sno,
        "roll_number": roll,
        "quota": quota,
        "college_name": college_name,
        "state": state,
        "pincode": pincode,
        "course": course,
        "allotted_category": allotted_category,
        "nri_priority": nri_priority,
    }


def parse_pdf(pdf_path: str, year: int, round_name: str) -> list[dict]:
    print(f"Extracting text from {pdf_path}...")
    raw_text = extract_text(pdf_path)

    # Split into blocks by S.No pattern (number at start of line)
    blocks = re.split(r"(?=^\d{4,6}\s+\d{7,})", raw_text, flags=re.MULTILINE)

    records = []
    for block in blocks:
        parsed = parse_allotment_block(block)
        if parsed:
            parsed["year"] = year
            parsed["round"] = round_name
            records.append(parsed)

    print(f"  Parsed {len(records)} records")
    return records


def save_csv(records: list[dict], output_path: str):
    if not records:
        print("No records to save.")
        return
    fieldnames = list(records[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    print(f"Saved {len(records)} rows to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python parse_allotment.py <pdf_path> <year> <round_name>")
        print("Example: python parse_allotment.py data/raw/round1_2025.pdf 2025 Round1")
        sys.exit(1)

    pdf_path = sys.argv[1]
    year = int(sys.argv[2])
    round_name = sys.argv[3]

    output_dir = Path("data/parsed")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"allotment_{year}_{round_name}.csv"

    records = parse_pdf(pdf_path, year, round_name)
    save_csv(records, str(output_path))
