import pdfplumber

pdfs = [
    "data/raw/2025/SellList+R1-MBBS-BDS.pdf",
    "data/raw/2025/SellList+R2-MBBS-BDS.pdf",
    "data/raw/2025/SellList+R3-MBBS-BDS.pdf",
    "data/raw/2025/SellList+R4-MBBS-BDS.pdf",
    "data/raw/2025/SellList+R5-MBBS-BDS.pdf",
]

for path in pdfs:
    print(f"\n{'='*60}")
    print(f"FILE: {path}")
    with pdfplumber.open(path) as pdf:
        print(f"  Pages: {len(pdf.pages)}")
        # Check first and last data pages
        for page_idx in [0, len(pdf.pages)//2, -1]:
            page = pdf.pages[page_idx]
            text = page.extract_text()
            if text:
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                # Find first data line (starts with a number)
                for line in lines:
                    parts = line.split()
                    if parts and parts[0].isdigit():
                        print(f"  [page {page_idx}] sample row: {line[:120]}")
                        break
        # Check x-positions of words on page 0
        words = pdf.pages[0].extract_words()
        # Find words around a data row by looking for M/F gender tokens
        for i, w in enumerate(words):
            if w['text'] in ('M', 'F') and i > 5:
                # Print surrounding context
                row_top = w['top']
                row_words = [x for x in words if abs(x['top'] - row_top) < 3]
                print(f"  Column x0 positions for a data row:")
                for rw in row_words:
                    print(f"    '{rw['text']:30s}'  x0={rw['x0']:7.1f}")
                break
