from weasyprint import HTML
HTML('founder-os-raw.html').write_pdf('Founder OS 需求文档V1.pdf')
print("Done")
