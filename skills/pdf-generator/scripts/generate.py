#!/usr/bin/env python3
"""PDF Generator with Chinese support using fpdf2 + STHeiti."""
import sys
import os
from fpdf import FPDF

FONT_PATH = "/System/Library/Fonts/STHeiti Medium.ttc"

class ChinesePDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("zh", "", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

def generate_pdf(input_file, output_file):
    pdf = ChinesePDF()
    pdf.add_font("zh", "", FONT_PATH)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    pdf.add_page()
    pdf.set_font("zh", "", 11)

    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()

    for line in content.split("\n"):
        line = line.rstrip()
        if not line:
            pdf.ln(3)
        elif line.startswith("# "):
            pdf.set_font("zh", "", 18)
            pdf.multi_cell(0, 10, line[2:], align="L")
            pdf.ln(3)
            pdf.set_font("zh", "", 11)
        elif line.startswith("## "):
            pdf.ln(2)
            pdf.set_font("zh", "", 14)
            pdf.multi_cell(0, 8, line[3:], align="L")
            pdf.line(15, pdf.get_y(), 195, pdf.get_y())
            pdf.ln(3)
            pdf.set_font("zh", "", 11)
        elif line.startswith("### "):
            pdf.ln(1)
            pdf.set_font("zh", "", 12)
            pdf.multi_cell(0, 7, line[4:], align="L")
            pdf.ln(2)
            pdf.set_font("zh", "", 11)
        elif line.startswith(" * ") or line.startswith("- "):
            prefix_len = 3 if line.startswith(" * ") else 2
            pdf.cell(5)
            pdf.multi_cell(0, 6, "\u2022 " + line[prefix_len:], align="L")
            pdf.ln(1)
        elif line.startswith("```") or line.startswith("//"):
            pdf.set_font("zh", "", 9)
            pdf.set_fill_color(245, 245, 245)
            pdf.multi_cell(0, 5, line, fill=True, align="L")
            pdf.set_fill_color(255, 255, 255)
            pdf.set_font("zh", "", 11)
        else:
            pdf.multi_cell(0, 6, line, align="L")
            pdf.ln(1)

    pdf.output(output_file)
    size = os.path.getsize(output_file)
    print(f"PDF generated: {output_file} ({size} bytes)")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 generate.py <input.txt> <output.pdf>")
        sys.exit(1)
    generate_pdf(sys.argv[1], sys.argv[2])
