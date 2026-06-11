"""Debug seat matrix parsing line by line."""
import re
import pdfplumber

pdf_path = "data/raw/2025/SeatMatrix-MBBSBDS-R1.pdf"
COLLEGE_HDR_RE = re.compile(r"^\s*(\d{1,3})\s+(\d{4})\s+")

current_college = None

with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages[:3]):
        text = page.extract_text()
        if not text:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("---"):
                continue

            is_college = bool(COLLEGE_HDR_RE.match(line))
            has_gen = "GEN." in line
            has_wom = "WOM." in line

            if is_college:
                m = COLLEGE_HDR_RE.match(line)
                current_college = m.group(2)
                print(f"\n[COLLEGE {current_college}] {line[:80]}")
            elif has_gen:
                print(f"  [GEN ] {line[:100]}")
            elif has_wom:
                print(f"  [WOM ] {line[:100]}")
            elif current_college and any(t in line for t in ["ORP","PWD","HA"]):
                pass  # skip these rows
            else:
                # continuation or section header
                if any(kw in line for kw in ["GOVT.","PVT.","MBBS","BDS","Pg:"]):
                    print(f"[SECTION] {line[:80]}")
