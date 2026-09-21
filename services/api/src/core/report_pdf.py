from __future__ import annotations

import io

from core.schemas import ConsumptionReport


def build_report_pdf(report: ConsumptionReport) -> bytes:
    """Render a monthly consumption report as a PDF (Chinese-capable, no external font files)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        title=f"月度消费报告 {report.month}",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ctitle", parent=styles["Title"], fontName="STSong-Light", fontSize=18, leading=22, spaceAfter=6)
    heading = ParagraphStyle("chead", parent=styles["Heading2"], fontName="STSong-Light", fontSize=13, leading=18, spaceBefore=10, spaceAfter=6)
    body = ParagraphStyle("cbody", parent=styles["Normal"], fontName="STSong-Light", fontSize=10.5, leading=16)

    story = [
        Paragraph(f"月度消费报告 {report.month}", title_style),
        Paragraph(f"生成时间：{report.generated_at.strftime('%Y-%m-%d %H:%M')}", body),
        Paragraph(f"总消耗：{report.total_consumed_qty}　总浪费：{report.total_wasted_qty}", body),
    ]

    def _table(header: list[str], rows: list[list[str]]) -> Table:
        table = Table([header] + rows, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e7c84f")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return table

    story.append(Paragraph("消耗 Top 10", heading))
    if report.top_consumed:
        story.append(_table(["品类", "消耗量", "单位"], [[e.item_name, f"{e.consumed_qty:.1f}", e.unit] for e in report.top_consumed]))
    else:
        story.append(Paragraph("本月无消耗记录", body))

    story.append(Paragraph("浪费明细", heading))
    if report.wasted:
        story.append(_table(["品类", "浪费量", "单位"], [[e.item_name, f"{e.wasted_qty:.1f}", e.unit] for e in report.wasted]))
    else:
        story.append(Paragraph("本月无浪费", body))

    story.append(Paragraph("周转天数（当前库存可支撑）", heading))
    if report.turnover:
        story.append(
            _table(
                ["品类", "周转天数"],
                [[e.item_name, f"{e.turnover_days:.1f}" if e.turnover_days is not None else "-"] for e in report.turnover],
            )
        )
    else:
        story.append(Paragraph("暂无周转数据", body))

    story.append(Paragraph("建议采购清单", heading))
    if report.suggested_purchase:
        story.append(
            _table(
                ["品类", "建议采购量", "单位"],
                [[s.item_key, f"{s.suggested_qty:.1f}", s.unit] for s in report.suggested_purchase],
            )
        )
    else:
        story.append(Paragraph("暂无采购建议", body))

    doc.build(story)
    return buf.getvalue()
