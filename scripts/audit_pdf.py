"""
Deep audit of Maharashtra CAP allotment PDF using pdfplumber.
"""
import pdfplumber
import json
import sys

PDF_PATH = r"C:\Users\surya\Projects\neet-ai-counsellor\data\raw\2025\SellList+R1-MBBS-BDS.pdf"
SAMPLE_PAGES = [1, 2, 3, 10, 50, 100]  # 1-indexed

def audit_page(page, page_num):
    result = {
        "page": page_num,
        "width": page.width,
        "height": page.height,
        "tables": [],
        "raw_text_snippet": "",
        "text_lines": [],
    }

    # Raw text
    text = page.extract_text(x_tolerance=2, y_tolerance=2)
    if text:
        lines = text.split("\n")
        result["raw_text_snippet"] = "\n".join(lines[:30])
        result["text_lines"] = lines

    # Tables
    tables = page.extract_tables(table_settings={
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
    })
    if not tables:
        # Try text-based
        tables = page.extract_tables(table_settings={
            "vertical_strategy": "text",
            "horizontal_strategy": "lines",
        })
    if not tables:
        tables = page.extract_tables()

    for ti, tbl in enumerate(tables):
        tinfo = {
            "table_index": ti,
            "row_count": len(tbl),
            "col_count": len(tbl[0]) if tbl else 0,
            "header_row": tbl[0] if tbl else [],
            "sample_rows": tbl[1:6] if len(tbl) > 1 else [],
            "all_rows": tbl,
        }
        result["tables"].append(tinfo)

    return result


def find_pwd_rows(page, page_num):
    """Scan ALL rows for PWD/PH/special earmark values."""
    found = []
    tables = page.extract_tables()
    for tbl in tables:
        for row in tbl:
            row_str = " ".join([str(c) for c in row if c])
            if any(kw in row_str.upper() for kw in ["PWD", "PH", "DAWS", "ORPHAN", "J&K", "EWS", "NRI", "TFWS", "MI ", "VJ", "NT", "OBC", "SC", "ST"]):
                found.append({"page": page_num, "row": row})
    return found


with pdfplumber.open(PDF_PATH) as pdf:
    total_pages = len(pdf.pages)
    print(f"=== TOTAL PAGES: {total_pages} ===\n")

    pwd_samples = []

    for page_num in SAMPLE_PAGES:
        if page_num > total_pages:
            print(f"Page {page_num} does not exist (total={total_pages})")
            continue

        page = pdf.pages[page_num - 1]
        print(f"\n{'='*80}")
        print(f"PAGE {page_num} (size: {page.width:.0f}x{page.height:.0f})")
        print(f"{'='*80}")

        # Raw text
        text = page.extract_text(x_tolerance=2, y_tolerance=2)
        if text:
            lines = text.split("\n")
            print(f"\n--- RAW TEXT (first 40 lines) ---")
            for i, line in enumerate(lines[:40]):
                print(f"  [{i:03d}] {repr(line)}")
            print(f"  ... total lines: {len(lines)}")
        else:
            print("  [NO TEXT EXTRACTED]")

        # Tables
        tables = page.extract_tables()
        print(f"\n--- TABLES FOUND: {len(tables)} ---")
        for ti, tbl in enumerate(tables):
            print(f"\n  Table {ti}: {len(tbl)} rows x {len(tbl[0]) if tbl else 0} cols")
            if tbl:
                print(f"  HEADER ROW: {tbl[0]}")
                print(f"  SAMPLE ROWS:")
                for ri, row in enumerate(tbl[1:6], 1):
                    print(f"    Row {ri}: {row}")
                # Check for PWD/PH/special in this table
                specials = []
                for row in tbl:
                    row_str = " ".join([str(c) for c in row if c])
                    if any(kw in row_str.upper() for kw in ["PWD", "PH", " EW", "ORPHAN", "J&K", "TFWS", "NRI"]):
                        specials.append(row)
                if specials:
                    print(f"  SPECIAL/PWD ROWS FOUND ({len(specials)}):")
                    for r in specials[:5]:
                        print(f"    {r}")

        # Check for header row repeat using words
        words = page.extract_words()
        header_words = ["Sr", "AIR", "NEET", "Name", "Category", "Quota", "College"]
        found_headers = [w["text"] for w in words if w["text"] in header_words]
        print(f"\n  Header-like words on page: {found_headers}")

    # Now scan pages for PWD rows (sample 20 pages)
    print(f"\n\n{'='*80}")
    print("SCANNING FOR PWD/PH ROWS (pages 1-20 + 50-60)...")
    print(f"{'='*80}")
    scan_pages = list(range(1, 21)) + list(range(50, 61))
    for page_num in scan_pages:
        if page_num > total_pages:
            break
        page = pdf.pages[page_num - 1]
        rows = find_pwd_rows(page, page_num)
        if rows:
            for r in rows[:3]:
                print(f"  Page {r['page']}: {r['row']}")
            if len(rows) > 3:
                print(f"    ... and {len(rows)-3} more on page {page_num}")
            pwd_samples.extend(rows[:2])
        if len(pwd_samples) >= 10:
            break

    if not pwd_samples:
        print("  No PWD/PH rows found in scanned pages")

    # Column position analysis: compare header x-positions across pages
    print(f"\n\n{'='*80}")
    print("COLUMN POSITION ANALYSIS (checking if columns shift)")
    print(f"{'='*80}")
    for page_num in [1, 2, 3, 10]:
        if page_num > total_pages:
            continue
        page = pdf.pages[page_num - 1]
        tables = page.extract_tables()
        if tables and tables[0]:
            print(f"  Page {page_num} col count: {len(tables[0][0])} | headers: {tables[0][0]}")

print("\nDONE.")
