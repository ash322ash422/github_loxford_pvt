
import pdfplumber
import pandas as pd

from app import config

pdf_path = config.DATA_UPLOAD_DIR / "01_tender_mini_version.pdf"

with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages, start=1):
        print(f"--- Page {page_num} ---")
        
        # 1. EXTRACT TABLES
        tables = page.extract_tables()
        if tables:
            for table_index, table in enumerate(tables):
                print(f"\n[Table {table_index + 1}]")
                # Convert to a DataFrame for clean viewing/exporting
                df = pd.DataFrame(table)
                print(df.to_string(index=False))
        else:
            print("\n[No tables found on this page]")

        # 2. EXTRACT PARAGRAPHS
        # Using layout=True helps preserve paragraph structures
        text = page.extract_text(layout=False) 
        
        print("\n\n\n")
        print("\n[Paragraph Text]")
        if text:
            # Split by double newlines to isolate actual paragraphs
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            for p in paragraphs:
                print(p)
                print("-" * 20) # Divider between paragraphs
