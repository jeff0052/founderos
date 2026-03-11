#!/usr/bin/env python3
from fpdf import FPDF

FONT_PATH = "/System/Library/Fonts/STHeiti Medium.ttc"

class MyPDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("zh", "", 8)
        self.cell(0, 10, f"Founder OS Three-Layer World Model  -  Page {self.page_no()}", align="C")

pdf = MyPDF()
pdf.add_font("zh", "", FONT_PATH)
pdf.set_auto_page_break(auto=True, margin=20)
pdf.set_left_margin(15)
pdf.set_right_margin(15)

with open("founder-os-3layer-content.txt", "r", encoding="utf-8") as f:
    content = f.read()

pdf.add_page()
pdf.set_font("zh", "", 11)

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
    elif line.startswith(" * "):
        pdf.cell(5)
        pdf.multi_cell(0, 6, "\u2022 " + line[3:], align="L")
        pdf.ln(1)
    elif line.startswith("- "):
        pdf.cell(5)
        pdf.multi_cell(0, 6, "\u2022 " + line[2:], align="L")
        pdf.ln(1)
    else:
        pdf.multi_cell(0, 6, line, align="L")
        pdf.ln(1)

pdf.output("Founder OS \u4e09\u5c42\u4e16\u754c\u6a21\u578b.pdf")
print("Done!")
