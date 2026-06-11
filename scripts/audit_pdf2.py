"""
Deep audit part 2: parse text rows, find PWD/PH rows, analyze structure.
"""
import pdfplumber
import re

PDF_PATH = r"C:\Users\surya\Projects\neet-ai-counsellor\data\raw\2025\SellList+R1-MBBS-BDS.pdf"

# Regex to match data rows
# Format: sr_no AIR neet_roll cet_form name G cat quota [earmark] college_code:college_name
# OR: sr_no AIR neet_roll cet_form name G cat quota "Choice Not Available"
DATA_ROW = re.compile(
    r'^(\d+)\s+'          # sr_no
    r'(\d+)\s+'          # AIR
    r'(\d{10,13})\s+'    # NEET roll (10-13 digits)
    r'(\d{9,12})\s+'     # CET form no
    r'(.+?)\s+'          # Name (greedy until gender)
    r'([MF])\s+'         # Gender
    r'(.+)$'             # everything after gender
)

def parse_row(line):
    m = DATA_ROW.match(line.strip())
    if not m:
        return None
    sr, air, neet, cet, name, gender, rest = m.groups()
    # rest = "OBC OPEN (EMD) 1103:GSMC MUMBAI"
    # or "OPEN (W) 1103:GSMC MUMBAI"
    # or "D1 DEF1 W 1103:GSMC MUMBAI"
    # or "Choice Not Available"
    return {
        "sr_no": sr,
        "air": air,
        "neet_roll": neet,
        "cet_form": cet,
        "name": name.strip(),
        "gender": gender,
        "rest": rest.strip(),
    }

def parse_rest(rest):
    """Parse the 'rest' field into category, quota, earmark, college."""
    if rest.startswith("Choice Not Available"):
        return {"category": None, "quota": "Choice Not Available", "earmark": None, "college": None}

    # Try to find college code pattern: 4 digits colon
    college_match = re.search(r'(\d{4}:.+)$', rest)
    college = college_match.group(1) if college_match else None
    before_college = rest[:college_match.start()].strip() if college_match else rest

    # Parse category + quota from before_college
    # Patterns observed:
    # "OPEN" -> cat=OPEN, quota=OPEN
    # "OBC OPEN (EMD)" -> cat=OBC, quota=OPEN, earmark=EMD
    # "OBC OBC" -> cat=OBC, quota=OBC
    # "OBC OBC(W)" -> cat=OBC, quota=OBC, earmark=W
    # "OPEN (W)" -> cat=OPEN, quota=OPEN, earmark=W
    # "OBC OPEN (W) (EMD)" -> cat=OBC, quota=OPEN, earmarks=[W, EMD]
    # "D1 DEF1 W" -> cat=D1, quota=DEF1, earmark=W
    # "D2 DEF2" -> cat=D2, quota=DEF2
    # "HA HOPEN" -> cat=HA, quota=HOPEN
    # "HA HOPENW" -> cat=HA, quota=HOPENW (women)
    # "SC SC (W)" -> cat=SC, quota=SC, earmark=W
    # "EWS EWS" -> cat=EWS, quota=EWS
    # "SEBCHA SEBC" -> cat=SEBCHA (HA+SEBC?), quota=SEBC

    tokens = before_college.split()

    result = {"category": None, "quota": None, "earmark": [], "college": college}

    if not tokens:
        return result

    result["category"] = tokens[0]

    # Collect parenthesized tokens as earmarks
    earmarks = []
    non_paren = []
    i = 0
    combined = " ".join(tokens[1:])
    # Extract (X) patterns
    parens = re.findall(r'\((\w+)\)', combined)
    result["earmark"] = parens
    # Quota is what's left after removing parens
    quota_str = re.sub(r'\s*\(\w+\)\s*', ' ', combined).strip()
    result["quota"] = quota_str if quota_str else None

    return result

def scan_for_pwd_ph(pdf, max_pages=None):
    """Scan all pages for PWD/PH keywords."""
    results = []
    total = len(pdf.pages)
    scan_count = min(total, max_pages) if max_pages else total

    for page_num in range(1, scan_count + 1):
        page = pdf.pages[page_num - 1]
        text = page.extract_text(x_tolerance=2, y_tolerance=2)
        if not text:
            continue
        lines = text.split("\n")
        for line in lines:
            if re.search(r'\bPWD\b|\bPH\b|\bDAWS\b|\bORPHAN\b|\bJ&K\b|\bTFWS\b|\bNRI\b', line, re.IGNORECASE):
                parsed = parse_row(line)
                if parsed:
                    results.append({"page": page_num, "raw": line, "parsed": parsed})
    return results

# First, deeply parse pages 1, 2, 3, 10, 50, 100
SAMPLE_PAGES = [1, 2, 3, 10, 50, 100]

with pdfplumber.open(PDF_PATH) as pdf:
    total_pages = len(pdf.pages)
    print(f"Total pages: {total_pages}\n")

    # SAMPLE PAGE ANALYSIS
    for page_num in SAMPLE_PAGES:
        if page_num > total_pages:
            continue
        page = pdf.pages[page_num - 1]
        text = page.extract_text(x_tolerance=2, y_tolerance=2)
        if not text:
            print(f"Page {page_num}: NO TEXT")
            continue
        lines = text.split("\n")

        print(f"\n{'='*80}")
        print(f"PAGE {page_num} - PARSED ROWS")
        print(f"{'='*80}")

        # Find header line indices
        header_idx = None
        for i, line in enumerate(lines):
            if 'Sr.' in line and 'AIR' in line and 'NEET' in line:
                header_idx = i
                print(f"  Header found at line {i}: {repr(line)}")

        # Second header line (quota/code/college)
        if header_idx is not None and header_idx + 1 < len(lines):
            print(f"  Header line 2:           {repr(lines[header_idx+1])}")

        # Parse data rows
        parsed_rows = []
        for line in lines:
            parsed = parse_row(line)
            if parsed:
                details = parse_rest(parsed["rest"])
                parsed.update(details)
                del parsed["rest"]
                parsed_rows.append(parsed)

        print(f"  Parsed data rows: {len(parsed_rows)}")
        print()

        # Show first 5 rows
        print("  FIRST 5 ROWS:")
        for r in parsed_rows[:5]:
            print(f"    sr={r['sr_no']:>5} | air={r['air']:>6} | neet={r['neet_roll']} | cet={r['cet_form']} | "
                  f"name={r['name'][:30]:<30} | G={r['gender']} | cat={str(r['category']):<8} | "
                  f"quota={str(r['quota']):<20} | earmark={r['earmark']} | college={r['college']}")

        # Show special rows (earmarks, special categories)
        specials = [r for r in parsed_rows if r["earmark"] or
                    r.get("category") in ["D1","D2","HA","EWS","TFWS","NRI"] or
                    "DEF" in str(r.get("quota","")) or
                    "HOPEN" in str(r.get("quota",""))]
        if specials:
            print(f"\n  SPECIAL/EARMARK ROWS ({len(specials)} found):")
            for r in specials[:10]:
                print(f"    sr={r['sr_no']:>5} | cat={str(r['category']):<8} | quota={str(r['quota']):<20} | "
                      f"earmark={r['earmark']} | name={r['name'][:30]}")

    # SCAN FOR PWD/PH/TFWS/NRI ROWS across first 200 pages
    print(f"\n\n{'='*80}")
    print("SCANNING FOR PWD/PH/TFWS/NRI ROWS (all pages)...")
    print(f"{'='*80}")

    pwd_rows = scan_for_pwd_ph(pdf, max_pages=total_pages)
    print(f"Total PWD/PH/TFWS/NRI rows found: {len(pwd_rows)}")
    for r in pwd_rows[:20]:
        print(f"  Page {r['page']:4d} | {r['raw']}")

    # ANALYZE LINES that didn't parse (could be split rows)
    print(f"\n\n{'='*80}")
    print("UNPARSEABLE LINES ANALYSIS (page 1)")
    print(f"{'='*80}")
    page = pdf.pages[0]
    text = page.extract_text(x_tolerance=2, y_tolerance=2)
    lines = text.split("\n")
    for i, line in enumerate(lines):
        parsed = parse_row(line)
        # Skip header/note lines
        if not parsed and line.strip() and not line.startswith("Note") and not line.startswith("GOVERNMENT") \
           and not line.startswith("State") and not line.startswith("Admission") \
           and not line.startswith("PROVISIONAL") and not line.startswith("Printed") \
           and not line.startswith("---") and not line.startswith("Sr.") \
           and not line.startswith("No.") and not line.startswith("be confirm") \
           and not line.startswith("stipulated") and not line.startswith("6.") \
           and not line.strip().startswith("Quota") and not line.strip().startswith("2.") \
           and not line.strip().startswith("3.") and not line.strip().startswith("4.") \
           and not line.strip().startswith("5."):
            print(f"  [{i:03d}] UNPARSED: {repr(line)}")

    # WORD POSITION ANALYSIS - extract column boundaries from page 1
    print(f"\n\n{'='*80}")
    print("WORD POSITION ANALYSIS (page 1, data rows)")
    print(f"{'='*80}")
    page = pdf.pages[0]
    words = page.extract_words(x_tolerance=2, y_tolerance=2)
    # Group by approximate y position
    from collections import defaultdict
    by_y = defaultdict(list)
    for w in words:
        y_key = round(w["top"] / 5) * 5  # 5-point buckets
        by_y[y_key].append(w)

    # Show x positions of a few data rows
    data_y_keys = sorted(by_y.keys())
    data_rows_shown = 0
    for y_key in data_y_keys:
        row_words = sorted(by_y[y_key], key=lambda w: w["x0"])
        row_text = " ".join([w["text"] for w in row_words])
        # Only show data rows (start with digit)
        if row_words and re.match(r'^\d+$', row_words[0]["text"]):
            print(f"  y~{y_key:4.0f} | x positions: {[round(w['x0']) for w in row_words]}")
            print(f"         | texts:      {[w['text'] for w in row_words]}")
            data_rows_shown += 1
            if data_rows_shown >= 5:
                break
