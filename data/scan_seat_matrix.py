"""Scan seat matrix PDF to understand structure."""
import pdfplumber

pdf_path = "data/raw/2025/SeatMatrix-MBBSBDS-R1.pdf"

with pdfplumber.open(pdf_path) as pdf:
    print(f"Pages: {len(pdf.pages)}")
    page = pdf.pages[0]
    text = page.extract_text()
    lines = [l for l in text.splitlines() if l.strip()]
    for i, line in enumerate(lines[:60]):
        print(f"{i:3d}: {line}")
