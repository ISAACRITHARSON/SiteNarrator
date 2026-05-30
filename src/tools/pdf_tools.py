"""SiteNarrator — PDF report generation via WeasyPrint.

Generates professional, client-ready construction daily narrative reports.
The document format follows industry standards used by general contractors
(Procore, Raken, AIA-aligned) with these sections:

1. Header (project, date, report #, superintendent, GC, sign-off block)
2. Weather & Site Conditions
3. Manpower Summary (table)
4. Work Completed by Trade (narrative + photo citations)
5. Equipment on Site (table)
6. Material Deliveries (table)
7. Safety Observations
8. Inspections & Visitors
9. Delays & Issues
10. Work Planned for Next Day
11. Photo Evidence Index
12. Sign-off Block (prepared by, reviewed/approved by, timestamps)

This is a legal document. It must be factual, timestamped, and traceable.
"""

from __future__ import annotations

from src.tools.tracing import traced


# ─── Professional Report HTML Template ─────────────────────────
# Modeled after industry-standard construction daily reports
# (Procore, Raken, AIA-aligned documentation)

REPORT_CSS = """
@page {
    size: letter;
    margin: 0.75in 0.75in 1in 0.75in;
    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 8pt;
        color: #666;
    }
    @bottom-left {
        content: "CONFIDENTIAL — Do Not Distribute Without Authorization";
        font-size: 7pt;
        color: #999;
    }
}
body {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    font-size: 9.5pt;
    line-height: 1.45;
    color: #1a1a1a;
}
.report-header {
    border-bottom: 3px solid #1e3a5f;
    padding-bottom: 14px;
    margin-bottom: 20px;
}
.report-header .gc-name {
    font-size: 14pt;
    font-weight: 700;
    color: #1e3a5f;
    margin: 0;
    letter-spacing: 0.5px;
}
.report-header .report-title {
    font-size: 11pt;
    font-weight: 600;
    color: #374151;
    margin: 4px 0 10px 0;
}
.header-grid {
    display: flex;
    justify-content: space-between;
    font-size: 8.5pt;
    color: #4b5563;
}
.header-grid .col {
    width: 48%;
}
.header-grid .label {
    font-weight: 600;
    color: #1f2937;
    display: inline-block;
    width: 110px;
}
h2 {
    font-size: 10.5pt;
    font-weight: 700;
    color: #1e3a5f;
    border-bottom: 1px solid #d1d5db;
    padding-bottom: 3px;
    margin: 18px 0 8px 0;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}
h3 {
    font-size: 9.5pt;
    font-weight: 600;
    color: #374151;
    margin: 10px 0 4px 0;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 6px 0 12px 0;
    font-size: 8.5pt;
}
th {
    background-color: #f0f4f8;
    border: 1px solid #cbd5e1;
    padding: 5px 7px;
    text-align: left;
    font-weight: 600;
    color: #1e3a5f;
    font-size: 8pt;
    text-transform: uppercase;
    letter-spacing: 0.2px;
}
td {
    border: 1px solid #e2e8f0;
    padding: 5px 7px;
    vertical-align: top;
}
tr:nth-child(even) td {
    background-color: #f8fafc;
}
.totals-row td {
    font-weight: 700;
    background-color: #f0f4f8 !important;
    border-top: 2px solid #cbd5e1;
}
p {
    margin: 4px 0;
}
.citation {
    color: #2563eb;
    font-weight: 600;
    font-size: 8.5pt;
}
.section-empty {
    color: #6b7280;
    font-style: italic;
    font-size: 9pt;
}
.delay-flag {
    background-color: #fef2f2;
    border-left: 3px solid #dc2626;
    padding: 4px 8px;
    margin: 4px 0;
    font-size: 9pt;
}
.safety-ok {
    background-color: #f0fdf4;
    border-left: 3px solid #16a34a;
    padding: 4px 8px;
    margin: 4px 0;
    font-size: 9pt;
}
.sign-off {
    margin-top: 30px;
    border-top: 2px solid #1e3a5f;
    padding-top: 12px;
}
.sign-off-grid {
    display: flex;
    justify-content: space-between;
}
.sign-off-block {
    width: 45%;
    font-size: 8.5pt;
}
.sign-off-block .role {
    font-weight: 600;
    color: #1e3a5f;
    margin-bottom: 4px;
}
.sign-off-block .line {
    border-bottom: 1px solid #1a1a1a;
    height: 20px;
    margin: 8px 0 4px 0;
}
.sign-off-block .field-label {
    font-size: 7.5pt;
    color: #6b7280;
}
.photo-index {
    font-size: 8.5pt;
}
.photo-index table td {
    font-size: 8pt;
}
"""

REPORT_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{css}</style>
</head>
<body>

<!-- ═══ HEADER ═══ -->
<div class="report-header">
    <p class="gc-name">{gc_company}</p>
    <p class="report-title">DAILY CONSTRUCTION REPORT</p>
    <div class="header-grid">
        <div class="col">
            <p><span class="label">Project:</span> {project_name}</p>
            <p><span class="label">Project No:</span> {project_id}</p>
            <p><span class="label">Location:</span> {project_location}</p>
            <p><span class="label">Contract No:</span> {contract_number}</p>
        </div>
        <div class="col">
            <p><span class="label">Report No:</span> {report_number}</p>
            <p><span class="label">Date:</span> {report_date}</p>
            <p><span class="label">Superintendent:</span> {superintendent}</p>
            <p><span class="label">Shift:</span> {shift}</p>
        </div>
    </div>
</div>

<!-- ═══ CONTENT ═══ -->
{content_html}

<!-- ═══ SIGN-OFF ═══ -->
<div class="sign-off">
    <div class="sign-off-grid">
        <div class="sign-off-block">
            <p class="role">Prepared By</p>
            <div class="line"></div>
            <p class="field-label">Name: {prepared_by}</p>
            <p class="field-label">Title: Superintendent</p>
            <p class="field-label">Date/Time: {prepared_at}</p>
        </div>
        <div class="sign-off-block">
            <p class="role">Reviewed &amp; Approved By</p>
            <div class="line"></div>
            <p class="field-label">Name: {approved_by}</p>
            <p class="field-label">Title: Project Coordinator</p>
            <p class="field-label">Date/Time: {approved_at}</p>
        </div>
    </div>
</div>

</body>
</html>"""


def _markdown_to_report_html(narrative: str) -> str:
    """Convert the agent's markdown narrative into professional report HTML.

    Handles: headings, tables, bold, citations, lists, delay flags, safety notes.
    """
    import re

    lines = narrative.split("\n")
    html_parts = []
    in_table = False
    is_first_table_row = False

    for line in lines:
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            if in_table:
                html_parts.append("</table>")
                in_table = False
            html_parts.append("")
            continue

        # H2 headings (## Section Name)
        match_h2 = re.match(r"^#{1,2}\s+\d*\.?\s*(.+)$", stripped)
        if match_h2:
            if in_table:
                html_parts.append("</table>")
                in_table = False
            html_parts.append(f"<h2>{match_h2.group(1)}</h2>")
            continue

        # H3 headings (### Subsection)
        match_h3 = re.match(r"^###\s+(.+)$", stripped)
        if match_h3:
            if in_table:
                html_parts.append("</table>")
                in_table = False
            html_parts.append(f"<h3>{match_h3.group(1)}</h3>")
            continue

        # Table rows (| col1 | col2 | ...)
        if "|" in stripped and stripped.startswith("|"):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            # Skip separator rows (|---|---|)
            if all(set(c) <= set("- :") for c in cells):
                continue
            if not in_table:
                html_parts.append("<table>")
                in_table = True
                is_first_table_row = True
                tag = "th"
            elif is_first_table_row:
                is_first_table_row = False
                tag = "td"
            else:
                tag = "td"
            row_html = "".join(f"<{tag}>{c}</{tag}>" for c in cells)
            html_parts.append(f"<tr>{row_html}</tr>")
            continue

        # Close table if we hit non-table content
        if in_table:
            html_parts.append("</table>")
            in_table = False

        # Process inline formatting
        processed = stripped

        # Bold
        processed = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", processed)

        # Photo citations -> styled spans
        processed = re.sub(
            r"\[Photo\s+(\d+)\]",
            r'<span class="citation">[Photo \1]</span>',
            processed,
        )

        # Delay lines (contain "delay" keyword)
        if "delay" in processed.lower() and ("hour" in processed.lower() or "hr" in processed.lower()):
            html_parts.append(f'<div class="delay-flag">{processed}</div>')
            continue

        # Safety OK lines
        if "no safety incident" in processed.lower() or "no incidents" in processed.lower():
            html_parts.append(f'<div class="safety-ok">{processed}</div>')
            continue

        # List items
        if processed.startswith("- ") or processed.startswith("* "):
            html_parts.append(f"<p style='margin-left:12px; text-indent:-8px;'>• {processed[2:]}</p>")
            continue

        # Section empty indicators
        if "nothing to report" in processed.lower() or "no open items" in processed.lower():
            html_parts.append(f'<p class="section-empty">{processed}</p>')
            continue

        # Regular paragraph
        html_parts.append(f"<p>{processed}</p>")

    if in_table:
        html_parts.append("</table>")

    return "\n".join(html_parts)


@traced("pdf.generate")
def generate_pdf(
    narrative: str,
    project_id: str,
    report_date: str,
    superintendent: str,
    project_name: str = "",
    gc_company: str = "",
    project_location: str = "",
    contract_number: str = "",
    report_number: int = 1,
    shift: str = "Day",
    prepared_at: str = "",
    approved_by: str = "",
    approved_at: str = "",
) -> bytes:
    """Generate a professional construction daily report PDF.

    This produces a document that meets industry standards for:
    - Client delivery (owner representatives)
    - Legal admissibility (contemporaneous documentation)
    - Claims support (delay evidence, change order backing)
    - Audit compliance (timestamped, signed, version-controlled)

    Args:
        narrative: The approved narrative text (markdown format with 10 sections).
        project_id: Project identifier / number.
        report_date: Report date (YYYY-MM-DD).
        superintendent: Superintendent who prepared the field data.
        project_name: Human-readable project name.
        gc_company: General contractor company name.
        project_location: Project site address.
        contract_number: Contract or PO number.
        report_number: Sequential report number for this project.
        shift: Shift description (e.g., "Day 07:00-17:00").
        prepared_at: Timestamp when report was prepared.
        approved_by: Name of the PC who approved.
        approved_at: Timestamp of approval.

    Returns:
        PDF file as bytes, ready for Box upload.
    """
    from weasyprint import HTML

    # Convert narrative markdown to professional HTML
    content_html = _markdown_to_report_html(narrative)

    # Assemble the full document
    html_content = REPORT_HTML_TEMPLATE.format(
        css=REPORT_CSS,
        gc_company=gc_company or "General Contractor",
        project_name=project_name or project_id,
        project_id=project_id,
        project_location=project_location or "See project records",
        contract_number=contract_number or "—",
        report_number=f"{report_number:04d}",
        report_date=report_date,
        superintendent=superintendent,
        shift=shift,
        content_html=content_html,
        prepared_by=superintendent,
        prepared_at=prepared_at or report_date,
        approved_by=approved_by or "Pending",
        approved_at=approved_at or "Pending",
    )

    # Generate PDF
    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes


# ─── Period Summary Report Template ───────────────────────────
# Extended template for multi-page period reports (5-25+ pages)

PERIOD_REPORT_CSS_ADDITIONS = """
.period-header {
    text-align: center;
    border-bottom: 3px solid #1e3a5f;
    padding-bottom: 16px;
    margin-bottom: 24px;
}
.period-header .gc-name {
    font-size: 16pt;
    font-weight: 700;
    color: #1e3a5f;
    margin: 0;
}
.period-header .report-title {
    font-size: 13pt;
    font-weight: 600;
    color: #374151;
    margin: 6px 0;
}
.period-header .period-dates {
    font-size: 10pt;
    color: #4b5563;
    margin: 4px 0;
}
.executive-summary {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 12px 16px;
    margin: 12px 0;
}
.executive-summary h3 {
    color: #1e3a5f;
    margin-top: 0;
}
.kpi-grid {
    display: flex;
    justify-content: space-between;
    margin: 12px 0;
}
.kpi-box {
    text-align: center;
    padding: 8px 12px;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    width: 22%;
}
.kpi-box .value {
    font-size: 16pt;
    font-weight: 700;
    color: #1e3a5f;
}
.kpi-box .label {
    font-size: 7.5pt;
    color: #6b7280;
    text-transform: uppercase;
}
.page-break {
    page-break-before: always;
}
"""


@traced("pdf.generate_period_report")
def generate_period_report_pdf(
    narrative: str,
    project_id: str,
    project_name: str,
    date_from: str,
    date_to: str,
    gc_company: str = "",
    superintendent: str = "",
    total_labor_hours: float = 0,
    working_days: int = 0,
    total_delay_hours: float = 0,
    approved_by: str = "",
    approved_at: str = "",
) -> bytes:
    """Generate a comprehensive period summary PDF report.

    This produces a longer document (5-25+ pages) covering a date range.
    Used for client progress meetings, pay applications, and monthly updates.

    Args:
        narrative: The period summary narrative (markdown, multi-section).
        project_id: Project identifier.
        project_name: Human-readable project name.
        date_from: Period start date (YYYY-MM-DD).
        date_to: Period end date (YYYY-MM-DD).
        gc_company: General contractor company name.
        superintendent: Superintendent name.
        total_labor_hours: Total labor-hours for the period.
        working_days: Number of working days in the period.
        total_delay_hours: Total delay hours in the period.
        approved_by: PC who approved.
        approved_at: Approval timestamp.

    Returns:
        PDF file as bytes.
    """
    from weasyprint import HTML

    # Convert narrative to HTML
    content_html = _markdown_to_report_html(narrative)

    # Build KPI section
    kpi_html = f"""
    <div class="kpi-grid">
        <div class="kpi-box">
            <div class="value">{working_days}</div>
            <div class="label">Working Days</div>
        </div>
        <div class="kpi-box">
            <div class="value">{total_labor_hours:,.0f}</div>
            <div class="label">Total Labor-Hours</div>
        </div>
        <div class="kpi-box">
            <div class="value">{total_delay_hours:.1f}</div>
            <div class="label">Delay Hours</div>
        </div>
        <div class="kpi-box">
            <div class="value">{working_days - int(total_delay_hours / 8)}</div>
            <div class="label">Productive Days</div>
        </div>
    </div>
    """

    full_css = REPORT_CSS + PERIOD_REPORT_CSS_ADDITIONS

    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{full_css}</style>
</head>
<body>

<div class="period-header">
    <p class="gc-name">{gc_company or 'General Contractor'}</p>
    <p class="report-title">PERIOD SUMMARY REPORT</p>
    <p class="period-dates">{date_from} through {date_to}</p>
    <p style="font-size: 9pt; color: #4b5563;">
        Project: {project_name} ({project_id}) |
        Superintendent: {superintendent}
    </p>
</div>

{kpi_html}

{content_html}

<div class="sign-off">
    <div class="sign-off-grid">
        <div class="sign-off-block">
            <p class="role">Prepared By</p>
            <div class="line"></div>
            <p class="field-label">Name: SiteNarrator AI (reviewed by {superintendent})</p>
            <p class="field-label">Date: {date_to}</p>
        </div>
        <div class="sign-off-block">
            <p class="role">Reviewed &amp; Approved By</p>
            <div class="line"></div>
            <p class="field-label">Name: {approved_by or 'Pending'}</p>
            <p class="field-label">Title: Project Coordinator</p>
            <p class="field-label">Date/Time: {approved_at or 'Pending'}</p>
        </div>
    </div>
</div>

</body>
</html>"""

    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes
