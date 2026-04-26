from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

def build_pdf_report(payload: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = [Paragraph("Aegis Comply — Compliance Dossier", styles['Title']), Spacer(1, 12)]
    score = payload.get('score', '—')
    story.append(Paragraph(f"Risk score: {score}/100", styles['Heading2']))
    concl = payload.get('legal_conclusion', {})
    story.append(Paragraph(concl.get('summary',''), styles['BodyText']))
    story.append(Spacer(1, 12))
    flags = payload.get('red_flags', [])
    data = [["Level", "Red flag", "Required documents"]]
    for f in flags:
        data.append([f.get('level',''), f.get('title',''), ', '.join(f.get('requested_documents', []))])
    if len(data) == 1:
        data.append(["low", "No material red flags", "Standard KYC file"])
    table = Table(data, colWidths=[60, 180, 260])
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#244f9e')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.25,colors.grey),('VALIGN',(0,0),(-1,-1),'TOP')]))
    story.append(table)
    doc.build(story)
    return buf.getvalue()
