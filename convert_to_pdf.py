#!/usr/bin/env python3
"""Convert markdown files to PDF."""

import os
from md2pdf.converter import convert
from pathlib import Path

# Define files to convert
files_to_convert = [
    ("docs/IMPLEMENTATION_GUIDE.md", "docs/IMPLEMENTATION_GUIDE.pdf"),
    ("docs/IMPLEMENTATION_PLAN.md", "docs/IMPLEMENTATION_PLAN.pdf"),
    ("docs/manuals/USER_MANUAL.md", "docs/manuals/USER_MANUAL.pdf"),
    ("README.md", "README.pdf"),
    ("docs/LLM_SETUP_GUIDE.md", "docs/LLM_SETUP_GUIDE.pdf"),
]

# Change to workspace directory
os.chdir("c:\\MySQL\\intell_swe")

print("Converting markdown to PDF...\n")

for md_file, pdf_file in files_to_convert:
    md_path = Path(md_file)
    pdf_path = Path(pdf_file)
    
    if not md_path.exists():
        print(f"❌ {md_file} not found")
        continue
    
    try:
        convert(md_file, pdf_file)
        print(f"✓ {md_file} → {pdf_file}")
    except Exception as e:
        print(f"❌ {md_file}: {e}")

print("\nPDF generation complete!")
