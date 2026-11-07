# Handwritten Notes Generator - Version 1

Converts Markdown, plain text, or a text-based PDF into PNG/JPG notebook pages with blue writing, ruled lines, a red margin, paper texture, and optional binder holes.

## Install

```bash
python -m pip install -r requirements.txt
```

## Run

```bash
python handwritten_notes.py sample_class_notes.md -o output
python handwritten_notes.py sample_class_notes.pdf -o output_pdf --format jpg
```

For a more convincing result, supply a handwriting font that you are licensed to use:

```bash
python handwritten_notes.py sample_class_notes.md -o output --font "C:/path/to/handwriting.ttf"
```

## Supported Markdown in Version 1

- Headings (`#` through `######`)
- Bulleted and numbered lists
- Task lists
- Block quotes
- Paragraphs
- Horizontal rules
- Fenced code blocks
- Basic inline-markup cleanup

## Important limitations

- PDF input must contain selectable text. Scanned/image-only PDFs need OCR, which is not included in Version 1.
- PDFs do not reliably preserve semantic structure during extraction, so headings and lists are detected using simple heuristics.
- This version simulates handwriting with a font plus small word-position and ink variations. It is not a handwriting neural model.
