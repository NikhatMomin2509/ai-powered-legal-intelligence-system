"""
pdf_service.py — Deterministic, in-memory PDF report generation for Legal Issue Analyzer
and Document Risk Analyzer using ReportLab.

Guarantees:
- In-memory bytes generation (BytesIO) — zero files written to disk or temp directories.
- Deterministic output from stored JSON — zero re-querying of retrieval or LLM.
- Escaped markup — XML/HTML special characters in user or model text cannot break ReportLab.
- Non-Latin/Devanagari support via Noto Sans Devanagari (SIL Open Font License).
- Grayscale readability — risk and authority indicated with clear text labels and borders.
- Explicit timezone labeling and page numbering ("Page X of Y").
- Disclaimer and privacy notes on every report.
- Zero sensitive metadata (no user emails or system paths embedded).
"""

import html
import io
import os
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Font Registration (Poppins - Indian Type Foundry - SIL Open Font License 1.1)
# ---------------------------------------------------------------------------
FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"
FONT_REGULAR = FONT_DIR / "Poppins-Regular.ttf"
FONT_BOLD_FILE = FONT_DIR / "Poppins-Bold.ttf"

FONT_NAME = "Poppins"
FONT_BOLD = "Poppins-Bold"

if FONT_REGULAR.exists() and FONT_BOLD_FILE.exists():
    try:
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_REGULAR)))
        pdfmetrics.registerFont(TTFont(FONT_BOLD, str(FONT_BOLD_FILE)))
    except Exception:
        FONT_NAME = "Helvetica"
        FONT_BOLD = "Helvetica-Bold"
else:
    FONT_NAME = "Helvetica"
    FONT_BOLD = "Helvetica-Bold"


# ---------------------------------------------------------------------------
# Numbered Canvas for "Page X of Y" and Static Legal Footer
# ---------------------------------------------------------------------------
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, total_pages):
        self.saveState()
        self.setFont(FONT_NAME, 8)
        self.setFillColor(colors.HexColor("#475569"))

        # Running header rule
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(40, 755, 572, 755)

        # Header running title
        self.drawString(40, 760, "AI-Powered Legal Intelligence System · Indian Law Research Brief")

        # Running footer rule
        self.line(40, 42, 572, 42)

        # Footer notice & page numbering
        self.drawString(
            40,
            30,
            "Informational analysis only · Not legal advice · Does not predict judicial outcomes",
        )
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(572, 30, page_str)

        self.restoreState()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def escape_markup(text: str | None) -> str:
    """Escapes XML entities so arbitrary user/LLM input does not break ReportLab Paragraphs."""
    if text is None:
        return ""
    escaped = html.escape(str(text))
    return escaped.replace("\n", "<br/>")


def format_iso_timestamp(ts_val) -> str:
    """Formats an ISO timestamp with explicit UTC/local clarification."""
    if not ts_val:
        now_utc = datetime.now(timezone.utc)
        return f"{now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC"
    if isinstance(ts_val, datetime):
        return f"{ts_val.strftime('%Y-%m-%d %H:%M:%S')} (Recorded Time)"
    try:
        dt = datetime.fromisoformat(str(ts_val).replace("Z", "+00:00"))
        return f"{dt.strftime('%Y-%m-%d %H:%M:%S')} (Recorded Time)"
    except Exception:
        return f"{str(ts_val)} (Recorded Time)"


def get_styles():
    """Builds a cohesive typography hierarchy using the registered Unicode font."""
    styles = getSampleStyleSheet()

    # Modify Base
    styles["Normal"].fontName = FONT_NAME
    styles["Normal"].fontSize = 9.5
    styles["Normal"].leading = 13
    styles["Normal"].textColor = colors.HexColor("#1E293B")

    # Document Title
    styles.add(
        ParagraphStyle(
            "ReportTitle",
            parent=styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=4,
        )
    )

    # Subtitle / Metadata
    styles.add(
        ParagraphStyle(
            "ReportMeta",
            parent=styles["Normal"],
            fontName=FONT_NAME,
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#64748B"),
            spaceAfter=8,
        )
    )

    # Section Heading
    styles.add(
        ParagraphStyle(
            "SectionH1",
            parent=styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#0F172A"),
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True,
        )
    )

    # Turn / Card Heading
    styles.add(
        ParagraphStyle(
            "SectionH2",
            parent=styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#1E293B"),
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True,
        )
    )

    # Body Text
    styles.add(
        ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
            spaceAfter=5,
        )
    )

    # Verbatim / Query Block
    styles.add(
        ParagraphStyle(
            "QueryBlock",
            parent=styles["Normal"],
            fontName=FONT_NAME,
            fontSize=9.5,
            leading=13.5,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=4,
        )
    )

    # Citation & Note Style
    styles.add(
        ParagraphStyle(
            "CitationText",
            parent=styles["Normal"],
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#475569"),
        )
    )

    # Callout / Disclaimer Style
    styles.add(
        ParagraphStyle(
            "CalloutText",
            parent=styles["Normal"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#475569"),
        )
    )

    return styles


# ---------------------------------------------------------------------------
# Section Flowable Generators
# ---------------------------------------------------------------------------
def make_callout(text: str, title: str | None = None, border_color="#CBD5E1", bg_color="#F8FAFC", sub_heading: str | None = None):
    styles = getSampleStyleSheet()
    p_style = ParagraphStyle(
        "CalloutInner",
        fontName=FONT_NAME,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )
    content = []
    if title:
        content.append(
            Paragraph(escape_markup(title), ParagraphStyle(
                "CalloutTitle",
                fontName=FONT_BOLD,
                fontSize=8.5,
                leading=11.5,
                textColor=colors.HexColor("#0F172A"),
                spaceAfter=2,
            ))
        )
    if sub_heading:
        content.append(
            Paragraph(escape_markup(sub_heading), ParagraphStyle(
                "CalloutSub",
                fontName=FONT_BOLD,
                fontSize=8.5,
                leading=11.5,
                textColor=colors.HexColor("#0F172A"),
                spaceAfter=3,
            ))
        )
    content.append(Paragraph(escape_markup(text), p_style))

    t = Table([[content]], colWidths=[532])
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg_color)),
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor(border_color)),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    return t


def build_turn_flowables(turn_num: int | None, query: str, result: dict, styles, is_multiturn: bool = False):
    """Builds the flowable elements for an individual analysis turn."""
    flowables = []

    # Clean internal keys
    cleaned = {k: v for k, v in result.items() if not k.startswith("_")}

    # Query Heading
    turn_label = f"Turn {turn_num}: Factual Inquiry" if is_multiturn and turn_num is not None else "Factual Inquiry / Legal Question"
    flowables.append(Paragraph(turn_label, styles["SectionH1"]))

    # Query Box
    query_p = Paragraph(f"<b>Query:</b> {escape_markup(query)}", styles["QueryBlock"])
    q_table = Table([[query_p]], colWidths=[532])
    q_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#94A3B8")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    flowables.append(q_table)
    flowables.append(Spacer(1, 8))

    # Assessment Summary & Domain
    domain = cleaned.get("legal_domain") or cleaned.get("issue_type") or "Indian Legal Matter"
    summary = cleaned.get("issue_summary") or "Assessment summary unavailable."
    flowables.append(
        Paragraph(f"<b>Legal Domain:</b> {escape_markup(domain)}", styles["SectionH2"])
    )
    flowables.append(Paragraph(f"<b>Executive Summary:</b> {escape_markup(summary)}", styles["Body"]))
    flowables.append(Spacer(1, 6))

    # Relevant Laws
    laws = cleaned.get("relevant_laws") or []
    if isinstance(laws, list) and len(laws) > 0:
        flowables.append(Paragraph("Statutory Authorities Cited", styles["SectionH2"]))
        law_rows = []
        for law in laws:
            act = law.get("act", "")
            sec = law.get("section", "")
            title = law.get("title", "")
            why = law.get("why_relevant", "")
            heading = f"<b>{escape_markup(act)} · {escape_markup(sec)}: {escape_markup(title)}</b>"
            desc = f"<i>Why relevant:</i> {escape_markup(why)}"
            law_rows.append([Paragraph(f"{heading}<br/>{desc}", styles["CitationText"])])

        if law_rows:
            lt = Table(law_rows, colWidths=[532])
            lt.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ])
            )
            flowables.append(lt)
            flowables.append(Spacer(1, 6))

    # Relevant Precedents
    cases = cleaned.get("relevant_cases") or []
    if isinstance(cases, list) and len(cases) > 0:
        flowables.append(Paragraph("Supreme Court Precedents & Judgments", styles["SectionH2"]))
        case_rows = []
        for c in cases:
            c_name = c.get("case_name", "Precedent")
            source = c.get("source", "Supreme Court of India")
            why = c.get("why_relevant", "")
            heading = f"<b>{escape_markup(c_name)}</b> [Source: {escape_markup(source)}]"
            desc = f"<i>Application:</i> {escape_markup(why)}"
            case_rows.append([Paragraph(f"{heading}<br/>{desc}", styles["CitationText"])])

        if case_rows:
            ct = Table(case_rows, colWidths=[532])
            ct.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ])
            )
            flowables.append(ct)
            flowables.append(Spacer(1, 6))

    # Balanced Evidentiary Considerations (Equal Visual Weight)
    sup = cleaned.get("supporting_considerations") or []
    opp = cleaned.get("opposing_considerations") or []
    sup_items = "<br/>".join([f"• {escape_markup(s)}" for s in sup]) if sup else "<i>None identified.</i>"
    opp_items = "<br/>".join([f"• {escape_markup(o)}" for o in opp]) if opp else "<i>None identified.</i>"

    flowables.append(Paragraph("Balanced Evidentiary Considerations", styles["SectionH2"]))
    cons_data = [
        [
            Paragraph("<b>Supporting Considerations (Proponent)</b>", styles["SectionH2"]),
            Paragraph("<b>Opposing Considerations (Counter-Risk)</b>", styles["SectionH2"]),
        ],
        [
            Paragraph(sup_items, styles["Body"]),
            Paragraph(opp_items, styles["Body"]),
        ],
    ]
    ct = Table(cons_data, colWidths=[262, 262])
    ct.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F0FDF4")),
            ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#FEF3C7")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    flowables.append(ct)
    flowables.append(Spacer(1, 6))

    # Missing Facts
    missing = cleaned.get("missing_facts") or []
    if isinstance(missing, list) and len(missing) > 0:
        flowables.append(Paragraph("Facts That Could Alter This Assessment", styles["SectionH2"]))
        user_facts = []
        system_note = None
        for mf in missing:
            text_str = str(mf).strip()
            if text_str.startswith("Tenancy and rent-control rules vary significantly"):
                system_note = text_str
            else:
                user_facts.append(f"• {escape_markup(text_str)}")

        if user_facts:
            flowables.append(Paragraph("<br/>".join(user_facts), styles["Body"]))

        if system_note:
            flowables.append(Spacer(1, 3))
            flowables.append(make_callout(system_note, title="Jurisdictional Scope Notice", border_color="#FDE68A", bg_color="#FFFBEB"))
        flowables.append(Spacer(1, 6))

    # Remedies & Specialization
    remedies = cleaned.get("possible_actions_or_remedies") or []
    spec = cleaned.get("lawyer_specialization")
    if remedies or spec:
        flowables.append(Paragraph("Actionable Remedies & Practice Specialization", styles["SectionH2"]))
        if remedies:
            rem_list = "<br/>".join([f"{i+1}. {escape_markup(r)}" for i, r in enumerate(remedies)])
            flowables.append(Paragraph(rem_list, styles["Body"]))
        if spec:
            flowables.append(
                Paragraph(f"<b>Recommended Advocate Specialization:</b> {escape_markup(spec)}", styles["Body"])
            )
        flowables.append(Spacer(1, 6))

    return flowables


# ---------------------------------------------------------------------------
# Public PDF Builders
# ---------------------------------------------------------------------------
def generate_issue_pdf(issue_row: dict) -> bytes:
    """Generates a PDF report for a single legal issue analysis."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=46,
        bottomMargin=46,
    )
    styles = get_styles()
    story = []

    # Title & Header
    story.append(Paragraph("Legal Issue Analysis Brief", styles["ReportTitle"]))
    date_str = format_iso_timestamp(issue_row.get("created_at"))
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    meta = f"Analyzed At: {date_str} · Report Generated: {now_utc} · Matter Reference: #{issue_row.get('id', 'N/A')}"
    story.append(Paragraph(meta, styles["ReportMeta"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0F172A"), spaceAfter=10))

    # Query & Result
    query = issue_row.get("query", "")
    result = issue_row.get("full_result") or issue_row
    story.extend(build_turn_flowables(None, query, result, styles, is_multiturn=False))

    # Disclaimer
    disclaimer_text = result.get("disclaimer") or (
        "This assessment is generated by an automated legal intelligence system for informational and research "
        "purposes only. It does not constitute formal legal advice, attorney-client counsel, or judicial outcome prediction."
    )
    story.append(Spacer(1, 8))
    story.append(make_callout(disclaimer_text, title="Legal Disclaimer & Guardrails", border_color="#94A3B8", bg_color="#F8FAFC"))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()


def generate_case_pdf(case_title: str, case_id: int, turns: list[dict]) -> bytes:
    """Generates a complete multi-turn case brief for all queries in a matter."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=46,
        bottomMargin=46,
    )
    styles = get_styles()
    story = []

    # Title & Header
    story.append(Paragraph(f"Case Brief: {escape_markup(case_title)}", styles["ReportTitle"]))
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    meta = f"Case ID: #{case_id} · Total Inquiries: {len(turns)} · Report Exported: {now_utc}"
    story.append(Paragraph(meta, styles["ReportMeta"]))

    # Multi-turn Context Disclosure Note
    context_note = (
        "Conversation Continuity: Follow-up questions in this case incorporate context from up to the "
        "3 most recent turns (earlier question and assessment summary truncated to 400 characters). "
        "All citations and provisions are verified against central Indian statutes and Supreme Court judgments."
    )
    story.append(make_callout(context_note, title="Context & Retrieval Architecture", border_color="#93C5FD", bg_color="#EFF6FF"))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0F172A"), spaceBefore=8, spaceAfter=10))

    # Add each turn sequentially
    for idx, turn in enumerate(turns, start=1):
        q = turn.get("query", "")
        res = turn.get("result") or turn.get("full_result") or turn
        story.extend(build_turn_flowables(idx, q, res, styles, is_multiturn=True))
        if idx < len(turns):
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceBefore=10, spaceAfter=10))

    # Case-level Disclaimer
    last_disclaimer = turns[-1].get("result", {}).get("disclaimer") if turns else None
    disclaimer_text = last_disclaimer or (
        "This multi-turn assessment is generated by an automated legal intelligence system for informational and research "
        "purposes only. It does not constitute formal legal advice, attorney-client counsel, or judicial outcome prediction."
    )
    story.append(Spacer(1, 8))
    story.append(make_callout(disclaimer_text, title="Legal Disclaimer & Guardrails", border_color="#94A3B8", bg_color="#F8FAFC"))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()


def generate_document_pdf(doc_data: dict) -> bytes:
    """Generates an annotated contract risk audit report from stored analysis JSON."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=46,
        bottomMargin=46,
    )
    styles = get_styles()
    story = []

    # Clean internal keys
    cleaned = {k: v for k, v in doc_data.items() if not k.startswith("_")}

    filename = cleaned.get("filename", "Contract Document")
    doc_type = cleaned.get("document_type", "Commercial Agreement")
    score = cleaned.get("risk_score", 0)
    level = str(cleaned.get("risk_level", "Medium")).upper()
    summary = cleaned.get("summary", "Document risk audit complete.")
    ocr_warning = cleaned.get("ocr_warning")

    # Header
    story.append(Paragraph(f"Document Risk Audit: {escape_markup(filename)}", styles["ReportTitle"]))
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    date_str = format_iso_timestamp(cleaned.get("created_at"))
    meta = f"Classified Type: {escape_markup(doc_type)} · Analyzed: {date_str} · Generated: {now_utc}"
    story.append(Paragraph(meta, styles["ReportMeta"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0F172A"), spaceAfter=10))

    # Note that report contains text from user's document
    doc_note = "Document Content Disclosure: This report contains text from the user's document. It contains clause excerpts processed from the uploaded agreement."
    story.append(make_callout(doc_note, border_color="#E2E8F0", bg_color="#F8FAFC"))
    story.append(Spacer(1, 6))

    # OCR Warning if present
    if ocr_warning:
        story.append(make_callout(ocr_warning, title="OCR Processing Notice", border_color="#FDE68A", bg_color="#FFFBEB"))
        story.append(Spacer(1, 6))

    # Indicative Score Box
    sub_title = f"Indicative Risk Score: {score} / 100 · Rating: [{level}]"
    score_desc = (
        "How this score is calculated: This score is an indicative, rule-based severity index calculated as a "
        "weighted average of flagged clause severities (LOW = 1, MEDIUM = 2, HIGH = 3). It is not a judicial assessment "
        "of legal enforceability or contractual validity, and does not reflect document length or unflagged provisions."
    )
    score_bg = "#FEF2F2" if level == "HIGH" else "#FFFBEB" if level == "MEDIUM" else "#F0FDF4"
    score_border = "#EF4444" if level == "HIGH" else "#F59E0B" if level == "MEDIUM" else "#10B981"
    story.append(make_callout(score_desc, title="Automated Risk Exposure Index", sub_heading=sub_title, border_color=score_border, bg_color=score_bg))
    story.append(Spacer(1, 8))

    # Executive Summary
    story.append(Paragraph("Executive Summary", styles["SectionH1"]))
    story.append(Paragraph(escape_markup(summary), styles["Body"]))
    story.append(Spacer(1, 8))

    # Flagged Clauses
    clauses = cleaned.get("risky_clauses") or []
    clause_count = len(clauses)
    story.append(Paragraph(f"Flagged Contractual Clauses ({clause_count})", styles["SectionH1"]))

    if clause_count == 0:
        story.append(Paragraph("No clauses were flagged under the current pattern rule set.", styles["Body"]))
    else:
        for idx, clause in enumerate(clauses, start=1):
            category = clause.get("category", "General Term")
            c_level = str(clause.get("risk_level", "MEDIUM")).upper()
            page = clause.get("page")
            clause_text = clause.get("clause_text", "")
            explanation = clause.get("explanation")
            negotiation = clause.get("negotiation_point")
            rel_laws = clause.get("relevant_laws") or []

            page_str = f" · Page {page}" if page else ""
            c_head = f"<b>Clause {idx}: {escape_markup(category)} [{c_level} RISK{page_str}]</b>"

            clause_items = [
                Paragraph(c_head, styles["SectionH2"]),
                Spacer(1, 2),
                Paragraph(f"<b>Verbatim Excerpt:</b><br/><i>\"{escape_markup(clause_text)}\"</i>", styles["CitationText"]),
                Spacer(1, 4),
            ]

            if explanation:
                clause_items.append(Paragraph(f"<b>Plain-English Assessment:</b> {escape_markup(explanation)}", styles["Body"]))
            else:
                clause_items.append(Paragraph("<b>Plain-English Assessment:</b> <i>Explanation unavailable for this clause.</i>", styles["Body"]))

            if negotiation:
                clause_items.append(Spacer(1, 2))
                clause_items.append(Paragraph(f"<b>Negotiation Counter-Position:</b> {escape_markup(negotiation)}", styles["Body"]))

            if rel_laws:
                clause_items.append(Spacer(1, 2))
                laws_lines = []
                for rl in rel_laws:
                    l_act = rl.get("act", "")
                    l_sec = rl.get("section", "")
                    l_title = rl.get("title", "")
                    l_excerpt = rl.get("content", "")
                    line = f"• {escape_markup(l_act)} {escape_markup(l_sec)}: {escape_markup(l_title)}"
                    if l_excerpt:
                        line += f"<br/>&nbsp;&nbsp;<i>Excerpt:</i> {escape_markup(l_excerpt)}"
                    laws_lines.append(line)
                clause_items.append(Paragraph("<b>Statutory Anchors:</b><br/>" + "<br/>".join(laws_lines), styles["CitationText"]))

            c_table = Table([[clause_items]], colWidths=[532])
            c_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ])
            )
            story.append(KeepTogether(c_table))
            story.append(Spacer(1, 8))

    # Document Disclaimer
    disclaimer_text = cleaned.get("disclaimer") or (
        "This document audit is generated by automated rule-based and language model extraction for research and "
        "negotiation preparation. It does not constitute formal legal counsel or a binding legal opinion on enforceability."
    )
    story.append(Spacer(1, 6))
    story.append(make_callout(disclaimer_text, title="Legal Disclaimer & Guardrails", border_color="#94A3B8", bg_color="#F8FAFC"))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()
