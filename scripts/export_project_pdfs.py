from pathlib import Path
import re
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf"

DOCUMENTS = [
    ("PROJECT_REPORT.md", "FinWise AI Project Report", "FinWise_AI_Project_Report.pdf"),
    ("VIVA_NOTES.md", "FinWise AI Viva Notes", "FinWise_AI_Viva_Notes.pdf"),
    ("DEMO_CHECKLIST.md", "FinWise AI Demo Checklist", "FinWise_AI_Demo_Checklist.pdf"),
]


def money_safe(text):
    return text.replace("Rs", "Rs")


def escape(text):
    return (
        money_safe(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def make_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=28,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0f766e"),
            spaceAfter=14,
        ),
        "h1": ParagraphStyle(
            "Heading1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=22,
            textColor=colors.HexColor("#0f766e"),
            spaceBefore=12,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "Heading2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#1f2937"),
            spaceBefore=9,
            spaceAfter=5,
        ),
        "h3": ParagraphStyle(
            "Heading3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=15,
            textColor=colors.HexColor("#374151"),
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#111827"),
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            leftIndent=13,
            firstLineIndent=-8,
            bulletIndent=4,
            textColor=colors.HexColor("#111827"),
            spaceAfter=4,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=base["Code"],
            fontName="Courier",
            fontSize=8.2,
            leading=10.5,
            leftIndent=6,
            rightIndent=6,
            backColor=colors.HexColor("#f3f4f6"),
            borderColor=colors.HexColor("#d1d5db"),
            borderWidth=0.4,
            borderPadding=5,
            spaceBefore=5,
            spaceAfter=8,
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=colors.HexColor("#6b7280"),
        ),
    }


def page(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(colors.HexColor("#d1d5db"))
    canvas.line(18 * mm, height - 15 * mm, width - 18 * mm, height - 15 * mm)
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawString(18 * mm, 9 * mm, "FinWise AI")
    canvas.drawRightString(width - 18 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


def markdown_to_story(markdown_text, title, styles):
    story = [Paragraph(escape(title), styles["title"]), Spacer(1, 4)]
    in_code = False
    code_lines = []
    paragraph_lines = []

    def flush_paragraph():
        nonlocal paragraph_lines
        if paragraph_lines:
            text = " ".join(line.strip() for line in paragraph_lines).strip()
            if text:
                story.append(Paragraph(escape(text), styles["body"]))
            paragraph_lines = []

    def flush_code():
        nonlocal code_lines
        if code_lines:
            story.append(Preformatted("\n".join(code_lines), styles["code"]))
            code_lines = []

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()

        if line.startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_paragraph()
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not line.strip():
            flush_paragraph()
            continue

        if line.startswith("# "):
            flush_paragraph()
            continue
        if line.startswith("## "):
            flush_paragraph()
            story.append(Paragraph(escape(line[3:]), styles["h1"]))
            continue
        if line.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(escape(line[4:]), styles["h2"]))
            continue
        if line.startswith("#### "):
            flush_paragraph()
            story.append(Paragraph(escape(line[5:]), styles["h3"]))
            continue

        bullet_match = re.match(r"^\s*-\s+(.*)$", line)
        numbered_match = re.match(r"^\s*(\d+)\.\s+(.*)$", line)
        if bullet_match:
            flush_paragraph()
            story.append(
                Paragraph(
                    f"- {escape(bullet_match.group(1))}",
                    styles["bullet"],
                )
            )
            continue
        if numbered_match:
            flush_paragraph()
            story.append(
                Paragraph(
                    f"{numbered_match.group(1)}. {escape(numbered_match.group(2))}",
                    styles["bullet"],
                )
            )
            continue

        paragraph_lines.append(line)

    flush_paragraph()
    flush_code()
    return story


def build_pdf(markdown_files, output_pdf, title):
    styles = make_styles()
    doc = SimpleDocTemplate(
        str(output_pdf),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title=title,
        author="FinWise AI",
    )

    story = []
    for index, (source, doc_title, _unused) in enumerate(markdown_files):
        if index:
            story.append(PageBreak())
        text = (ROOT / source).read_text(encoding="utf-8")
        story.extend(markdown_to_story(text, doc_title, styles))

    doc.build(story, onFirstPage=page, onLaterPages=page)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    generated = []

    for source, title, filename in DOCUMENTS:
        target = OUTPUT / filename
        build_pdf([(source, title, filename)], target, title)
        generated.append(target)

    combined = OUTPUT / "FinWise_AI_Complete_Project_Pack.pdf"
    build_pdf(DOCUMENTS, combined, "FinWise AI Complete Project Pack")
    generated.append(combined)

    for path in generated:
        print(path)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"PDF export failed: {exc}", file=sys.stderr)
        raise
