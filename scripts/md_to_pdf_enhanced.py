#!/usr/bin/env python3
"""
Enhanced Markdown to PDF converter with images, bold text, headers, and code blocks.
Usage: python scripts/md_to_pdf_enhanced.py docs/USE_CASE_ANALYSIS.md docs/USE_CASE_ANALYSIS.pdf
"""
import sys
import re
from pathlib import Path
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak,
    Table, TableStyle, Preformatted
)
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def setup_styles():
    """Create custom styles for different markdown elements."""
    styles = getSampleStyleSheet()
    
    # Modify existing heading styles
    styles['Heading1'].fontSize = 24
    styles['Heading1'].textColor = colors.HexColor('#1a1a1a')
    styles['Heading1'].spaceAfter = 12
    styles['Heading1'].spaceBefore = 12
    styles['Heading1'].leading = 28
    
    styles['Heading2'].fontSize = 18
    styles['Heading2'].textColor = colors.HexColor('#2a2a2a')
    styles['Heading2'].spaceAfter = 10
    styles['Heading2'].spaceBefore = 10
    styles['Heading2'].leading = 22
    
    styles['Heading3'].fontSize = 14
    styles['Heading3'].textColor = colors.HexColor('#3a3a3a')
    styles['Heading3'].spaceAfter = 8
    styles['Heading3'].spaceBefore = 8
    styles['Heading3'].leading = 18
    
    # Add custom code block style
    styles.add(ParagraphStyle(
        name='CodeBlock',
        parent=styles['Normal'],
        fontSize=9,
        leftIndent=20,
        rightIndent=20,
        textColor=colors.black,
        backColor=colors.HexColor('#f8f9fa'),
        fontName='Courier',
        borderColor=colors.HexColor('#dee2e6'),
        borderWidth=1,
        borderPadding=8
    ))
    
    return styles

def convert_bold_italic(text):
    """Convert markdown bold/italic to ReportLab tags."""
    # Escape XML entities first
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    
    # Convert checkmarks and X marks
    text = text.replace('✅', '✓')
    text = text.replace('❌', '✗')
    
    # Bold: **text** or __text__ (but not in middle of words)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
    
    # Italic: *text* or _text_ (but not in middle of words)
    text = re.sub(r'(?<!\w)\*(.+?)\*(?!\w)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'<i>\1</i>', text)
    
    # Code: `text`
    text = re.sub(r'`(.+?)`', r'<font name="Courier" color="#d63384">\1</font>', text)
    
    return text

def parse_markdown(md_text, md_path):
    """Parse markdown text into ReportLab story elements."""
    styles = setup_styles()
    story = []
    
    lines = md_text.split('\n')
    i = 0
    in_code_block = False
    code_block_lines = []
    
    while i < len(lines):
        line = lines[i]
        
        # Code blocks
        if line.strip().startswith('```'):
            if in_code_block:
                # End of code block
                code_text = '\n'.join(code_block_lines)
                story.append(Preformatted(code_text, styles['CodeBlock']))
                story.append(Spacer(1, 0.2*inch))
                code_block_lines = []
                in_code_block = False
            else:
                # Start of code block
                in_code_block = True
            i += 1
            continue
        
        if in_code_block:
            code_block_lines.append(line)
            i += 1
            continue
        
        # Headers
        if line.startswith('# '):
            text = convert_bold_italic(line[2:])
            story.append(Paragraph(text, styles['Heading1']))
            story.append(Spacer(1, 0.1*inch))
        elif line.startswith('## '):
            text = convert_bold_italic(line[3:])
            story.append(Paragraph(text, styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))
        elif line.startswith('### '):
            text = convert_bold_italic(line[4:])
            story.append(Paragraph(text, styles['Heading3']))
            story.append(Spacer(1, 0.08*inch))
        
        # Images: ![alt](path)
        elif line.strip().startswith('!['):
            match = re.match(r'!\[.*?\]\((.+?)\)', line.strip())
            if match:
                img_path = match.group(1)
                # Resolve relative to markdown file
                if not Path(img_path).is_absolute():
                    img_path = (md_path.parent / img_path).resolve()
                
                if Path(img_path).exists():
                    try:
                        img = Image(str(img_path), width=5*inch, height=3*inch, kind='proportional')
                        story.append(img)
                        story.append(Spacer(1, 0.2*inch))
                    except Exception as e:
                        print(f"Warning: Could not load image {img_path}: {e}")
        
        # Tables (simple markdown tables)
        elif '|' in line and line.strip().startswith('|'):
            table_lines = [line]
            j = i + 1
            while j < len(lines) and '|' in lines[j] and lines[j].strip().startswith('|'):
                table_lines.append(lines[j])
                j += 1
            
            # Parse table
            table_data = []
            for tline in table_lines:
                if '---' in tline:  # Skip separator line
                    continue
                cells = [cell.strip() for cell in tline.split('|')[1:-1]]
                # Don't convert bold/italic for table cells - use Paragraph instead
                table_data.append(cells)
            
            if table_data:
                # Convert cells to Paragraphs for proper HTML rendering
                para_data = []
                for row_idx, row in enumerate(table_data):
                    para_row = []
                    for cell in row:
                        cell_text = convert_bold_italic(cell)
                        if row_idx == 0:  # Header row
                            para_row.append(Paragraph(cell_text, styles['BodyText']))
                        else:
                            para_row.append(Paragraph(cell_text, styles['BodyText']))
                    para_data.append(para_row)
                
                t = Table(para_data)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9ecef')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6'))
                ]))
                story.append(t)
                story.append(Spacer(1, 0.2*inch))
            i = j - 1
        
        # Regular paragraphs
        elif line.strip():
            text = convert_bold_italic(line.strip())
            story.append(Paragraph(text, styles['BodyText']))
            story.append(Spacer(1, 0.1*inch))
        
        # Empty lines
        else:
            story.append(Spacer(1, 0.05*inch))
        
        i += 1
    
    return story

def generate_pdf(md_path: Path, pdf_path: Path):
    """Generate PDF from markdown file."""
    print(f"Converting {md_path} to {pdf_path}...")
    
    # Read markdown
    md_text = md_path.read_text(encoding='utf-8')
    
    # Create PDF document
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=LETTER,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    # Parse and build
    story = parse_markdown(md_text, md_path)
    doc.build(story)
    
    print(f"✓ PDF generated: {pdf_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/md_to_pdf_enhanced.py <input.md> <output.pdf>")
        print("Example: python scripts/md_to_pdf_enhanced.py docs/USE_CASE_ANALYSIS.md docs/USE_CASE_ANALYSIS.pdf")
        sys.exit(1)
    
    md_in = Path(sys.argv[1])
    pdf_out = Path(sys.argv[2])
    
    if not md_in.exists():
        print(f"Error: Input file not found: {md_in}")
        sys.exit(1)
    
    generate_pdf(md_in, pdf_out)
