"""Quick test - only first 10 pages of Round 1"""
import pdfplumber
from parse_mh_cap import parse_row, bucket_word

pdf_path = "data/raw/2025/SellList+R1-MBBS-BDS.pdf"
records = []

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    for page_num, page in enumerate(pdf.pages[:10]):
        print(f"\n--- Page {page_num + 1} ---")
        words = page.extract_words()

        # Group by baseline
        rows = {}
        for w in words:
            baseline = round(w["top"] / 2) * 2
            rows.setdefault(baseline, []).append(w)

        for baseline in sorted(rows):
            row_words = sorted(rows[baseline], key=lambda w: w["x0"])
            record = parse_row(row_words)
            if record:
                records.append(record)
                print(f"  sr={record['sr_no']:5s} air={record['air']:7s} "
                      f"name={record['name']:35s} "
                      f"gender={record['gender']} cat={record['category']:6s} "
                      f"quota={str(record['quota']):6s} "
                      f"W={record['women_quota']} "
                      f"allotted={record['allotted']} "
                      f"college={record['college_code']}:{record['college_name']}")

print(f"\nTotal records from 10 pages: {len(records)}")
