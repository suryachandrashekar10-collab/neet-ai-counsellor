"""
Parse MCC NEET UG allotment result PDFs into structured CSV.

Per-record structure (pdfplumber extracts as 2 lines):
  Line 1: SNo Rank Quota  College,AddressPart1  Course  AllottedCat  CandidateCat  Remarks
  Line 2: AddressPart2, State, Pincode
"""

import re
import csv
import sys
from pathlib import Path
import pdfplumber


# Full quota names as they appear in PDFs (longest first to avoid partial match)
QUOTA_PHRASES = [
    "Deemed/Paid Seats Quota",
    "Delhi NCR Children/Widows of Personnel of the Armed Forces (CW) DU Quota",
    "Delhi NCR Children/Widows of Personnel of the Armed Forces (CW) IP Quota",
    "Employees State Insurance Scheme Nursing Quota",
    "Employees State Insurance Scheme",
    "B.Sc Nursing Delhi NCR CW Quota",
    "B.Sc Nursing Delhi NCR",
    "B.Sc Nursing IP CW Quota",
    "B.Sc Nursing All India",
    "Non-Resident Indian(AMU)Quota",
    "Non-Resident Indian(Jamia)Quota",
    "Non-Resident Indian",
    "Aligarh Muslim University (AMU) Quota",
    "Internal -Puducherry UT Domicile",
    "Delhi University Quota",
    "IP University Quota",
    "Muslim Minority Quota",
    "Muslim Women Quota",
    "Muslim OBC Quota",
    "Muslim ST Quota",
    "Muslim Quota",
    "Jain Minority Quota",
    "Jamia Internal Quota",
    "Foreign Country Quota",
    "Open Seat Quota",
    "All India",
]

COURSE_RE = re.compile(r"\b(MBBS|BDS|B\.Sc\.?\s*Nursing)\b")

# Category tokens (order matters: longer first)
CAT_TOKENS = ["OBC PwD", "SC PwD", "ST PwD", "EW PwD", "GN PwD",
               "General", "Open", "OBC", "EWS", "EW", "GN", "SC", "ST"]
CAT_RE = re.compile(
    r"\b(OBC PwD|SC PwD|ST PwD|EW PwD|GN PwD|General|Open|OBC|EWS|EW|GN|SC|ST)\b"
)

REMARKS_RE = re.compile(
    r"(Allotted\s*\(\s*NRI\s*Priority\s*:\s*\d+\s*\)|Allotted|Not Allotted|Upgraded|Freeze)"
)

PINCODE_RE = re.compile(r"\b(\d{6})\b")
# State appears as: ", StateName, 6digits" or ", StateName (something), 6digits"
STATE_RE = re.compile(r",\s*([A-Za-z][A-Za-z\s\(\)]+?),\s*\d{6}")

RECORD_START_RE = re.compile(r"^(\d{1,6})\s+(\d{1,7})\s+(.+)$")
HEADER_KEYWORDS = ["SNo Rank", "NEET-UG", "Quota Abbrevation", "Abbrevation",
                   "Note*", "Allotted Category", "Category Category", "Schedule"]


def is_header(line: str) -> bool:
    return any(kw in line for kw in HEADER_KEYWORDS)


def extract_quota(text: str):
    for q in QUOTA_PHRASES:
        if text.startswith(q):
            return q, text[len(q):].strip()
    return None, text


def extract_categories(text: str):
    """Extract up to 2 category tokens from text."""
    cats = CAT_RE.findall(text)
    allotted_cat = cats[0] if len(cats) > 0 else None
    candidate_cat = cats[1] if len(cats) > 1 else None
    return allotted_cat, candidate_cat


def parse_record(main_line: str, addr_line: str) -> dict | None:
    m = RECORD_START_RE.match(main_line)
    if not m:
        return None

    sno = m.group(1)
    rank = m.group(2)
    rest = m.group(3)

    # Extract quota
    quota, after_quota = extract_quota(rest)

    # Find course position — everything before course is college+address
    course_m = COURSE_RE.search(after_quota)
    if not course_m:
        return None

    course = course_m.group(0).strip()
    college_address = after_quota[:course_m.start()].strip().rstrip(",").strip()
    after_course = after_quota[course_m.end():].strip()

    # College name = everything up to the first comma in the address
    # e.g. "AIIMS, New Delhi,AIIMS ANSARI NAGAR..." → "AIIMS, New Delhi"
    # Split on comma, first part is college name, rest is street address
    addr_parts = college_address.split(",")
    if len(addr_parts) >= 2:
        college_name = (addr_parts[0] + ", " + addr_parts[1]).strip()
    else:
        college_name = addr_parts[0].strip()

    # Extract remarks
    remarks_m = REMARKS_RE.search(after_course)
    remarks = remarks_m.group(0).strip() if remarks_m else None

    # Extract categories from between course and remarks
    cat_text = after_course[:remarks_m.start()].strip() if remarks_m else after_course
    allotted_cat, candidate_cat = extract_categories(cat_text)

    # State and pincode from address continuation line
    full_addr = college_address + " " + addr_line
    pin_m = PINCODE_RE.search(full_addr)
    pincode = pin_m.group(1) if pin_m else None

    state_m = STATE_RE.search(full_addr)
    state = state_m.group(1).strip() if state_m else None

    return {
        "sno": sno,
        "rank": rank,
        "quota": quota,
        "college_name": college_name,
        "state": state,
        "pincode": pincode,
        "course": course,
        "allotted_category": allotted_cat,
        "candidate_category": candidate_cat,
        "remarks": remarks,
    }


def parse_pdf(pdf_path: str, year: int, round_name: str) -> list[dict]:
    print(f"Extracting text from {pdf_path}...")
    lines = []
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                lines.extend(t.splitlines())

    print(f"  Total pages: {total}, lines: {len(lines)}")

    records = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if not line or is_header(line):
            i += 1
            continue

        m = RECORD_START_RE.match(line)
        if not m:
            i += 1
            continue

        # Collect address continuation lines (lines that don't start a new record)
        addr_parts = []
        j = i + 1
        while j < len(lines):
            next_line = lines[j].strip()
            if not next_line or is_header(next_line) or RECORD_START_RE.match(next_line):
                break
            addr_parts.append(next_line)
            j += 1

        addr_line = " ".join(addr_parts)
        record = parse_record(line, addr_line)
        if record:
            record["year"] = year
            record["round"] = round_name
            records.append(record)

        i = j  # skip consumed continuation lines

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
        print('Example: python parse_allotment.py "data/raw/2025/Round 1.pdf" 2025 Round1')
        sys.exit(1)

    pdf_path = sys.argv[1]
    year = int(sys.argv[2])
    round_name = sys.argv[3]

    output_dir = Path("data/parsed")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"allotment_{year}_{round_name}.csv"

    records = parse_pdf(pdf_path, year, round_name)
    save_csv(records, str(output_path))
