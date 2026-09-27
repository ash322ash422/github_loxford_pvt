from pathlib import Path

import pdfplumber
import pandas as pd

from app import config

pdf_path = config.DATA_UPLOAD_DIR / "01_tender_mini_version.pdf"
excel_output_path = Path(__file__).resolve().parent / "extracted_tables.xlsx"

# Initialize an Excel writer object
with pd.ExcelWriter(excel_output_path, engine='openpyxl') as writer:
    table_counter = 1
    
    # Open the PDF
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            # Extract all tables on the current page
            tables = page.extract_tables()
            
            for table in tables:
                # 1. Convert the raw list of rows into a Pandas DataFrame
                # We assume the first row contains the column headers
                df = pd.DataFrame(table[1:], columns=table[0])
                
                # 2. Clean the data (optional: remove empty rows/columns)
                df = df.dropna(how='all')
                
                # 3. Create a unique sheet name (Excel sheets max limit is 31 characters)
                sheet_name = f"Page{page_num}_Table{table_counter}"
                
                # 4. Write the DataFrame to the Excel file
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                print(f"Saved: {sheet_name}")
                table_counter += 1

print(f"\nSuccess! All tables saved to '{excel_output_path}'")
