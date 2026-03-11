#!/usr/bin/env python3
from fpdf import FPDF

FONT_PATH = "/System/Library/Fonts/STHeiti Medium.ttc"

pdf = FPDF()
pdf.add_font("zh", "", FONT_PATH)
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()

with open("founder-os-content.txt", "r", encoding="utf-8") as f:
    content = f.read()

pdf.set_font("zh", "", 11)

for line in content.split("\n"):
    line = line.rstrip()
    if not line:
        pdf.ln(4)
    elif line.startswith("# "):
        pdf.set_font("zh", "", 18)
        pdf.multi_cell(0, 10, line[2:])
        pdf.ln(3)
        pdf.set_font("zh", "", 11)
    elif line.startswith("## "):
        pdf.set_font("zh", "", 14)
        pdf.multi_cell(0, 8, line[3:])
        pdf.ln(2)
        pdf.set_font("zh", "", 11)
    elif line.startswith("### "):
        pdf.set_font("zh", "", 12)
        pdf.multi_cell(0, 7, line[4:])
        pdf.ln(2)
        pdf.set_font("zh", "", 11)
    elif line.startswith("|"):
        # Table: render as small text
        pdf.set_font("zh", "", 8)
        # Clean up markdown table separators
        if line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        row_text = "  |  ".join(cells)
        pdf.multi_cell(0, 5, row_text)
        pdf.ln(1)
        pdf.set_font("zh", "", 11)
    elif line.startswith(" * "):
        pdf.multi_cell(0, 6, "  \u2022 " + line[3:])
        pdf.ln(1)
    else:
        pdf.multi_cell(0, 6, line)
        pdf.ln(1)

pdf.output("Founder OS \u9700\u6c42\u6587\u6863V1.pdf")
print("Done!")
