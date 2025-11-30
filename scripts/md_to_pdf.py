import sys
from pathlib import Path
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch

def md_to_plain(md_text: str) -> str:
    # Minimal: strip markdown headers and code fences for plain rendering
    lines = []
    for line in md_text.splitlines():
        if line.strip().startswith("```"):
            continue
        if line.startswith("#"):
            line = line.lstrip('#').strip()
        lines.append(line)
    return "\n".join(lines)

def generate_pdf(md_path: Path, pdf_path: Path):
    text = md_path.read_text(encoding="utf-8")
    plain = md_to_plain(text)

    doc = SimpleDocTemplate(str(pdf_path), pagesize=LETTER,
                            leftMargin=0.75*inch, rightMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    story = []
    for para in plain.split("\n\n"):
        story.append(Paragraph(para.replace("\n", "<br/>"), styles["BodyText"]))
        story.append(Spacer(1, 0.15*inch))
    doc.build(story)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/md_to_pdf.py <input.md> <output.pdf>")
        sys.exit(1)
    md_in = Path(sys.argv[1])
    pdf_out = Path(sys.argv[2])
    generate_pdf(md_in, pdf_out)