---
name: pdf-generator
description: "Generate PDF documents with full Chinese language support. Converts user-provided text content into clean, formatted PDF files using fpdf2 + system Chinese fonts."
metadata: {"openclaw":{"requires":{"bins":["python3"]}}}
---

# PDF Generator

Generate PDF documents with proper Chinese character rendering.

## When to Use

- User wants to convert text/markdown content to PDF
- User says "做成PDF", "生成PDF", "转PDF"
- Any document that needs Chinese text in PDF format

## Dependencies

- `fpdf2`: `pip3 install fpdf2`
- System font: `/System/Library/Fonts/STHeiti Medium.ttc` (macOS built-in)

## Workflow

### Step 1: Save Content
Save the user's raw text to a `.txt` file in the skill's `output/` directory.

### Step 2: Generate PDF
Run the generation script:
```bash
python3 skills/pdf-generator/scripts/generate.py <input.txt> <output.pdf>
```

### Step 3: Self-Check
**MANDATORY**: Before sending to user, use the `pdf` tool to verify:
1. Chinese characters display correctly (not blank/boxes)
2. All sections are complete
3. No page break issues

### Step 4: Send
Only after self-check passes, send the PDF to the user.

## Lessons Learned
- Chrome headless PDF generation does NOT support Chinese fonts — always use fpdf2
- Use `align="L"` (left-align) to avoid Chinese-English spacing issues
- Long tables break across pages badly — use list format instead
- Emoji characters (🚀✅❌) are not supported in STHeiti font, acceptable to skip
- Always self-check before sending, never send unchecked PDFs

## Notes
- Output directory: `skills/pdf-generator/output/` (create if needed)
- Font warnings about "feat NOT subset" and "morx NOT subset" are harmless, ignore them
