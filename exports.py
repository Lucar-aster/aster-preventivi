import io
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Table, TableStyle

# ==========================================
# 1. ESPORTAZIONE EXCEL (Controllo Interno)
# ==========================================
def genera_excel_preventivo(
    df_moduli, progetto_nome, ricarico_proj, sconto_fin, ricarico_mont
):
  output = io.BytesIO()

  # Prepara le colonne per l'Excel
  df_export = df_moduli[[
      'ambiente',
      'categoria',
      'nome_modulo',
      'larghezza_mm',
      'altezza_mm',
      'profondita_mm',
      'costo_industriale',
  ]].copy()

  df_export.columns = [
      'Ambiente',
      'Categoria',
      'Modulo',
      'L (mm)',
      'H (mm)',
      'P (mm)',
      'Costo Ind. (€)',
  ]

  # Calcola prezzi di vendita ricaricati
  df_export['Prezzo Vendita (€)'] = df_export['Costo Ind. (€)'].apply(
      lambda x: round(float(x) * (1 + (ricarico_proj / 100)), 2)
  )

  with pd.ExcelWriter(output, engine='openpyxl') as writer:
    df_export.to_excel(writer, sheet_name='Dettaglio Moduli', index=False)

    # Crea un foglio separato con i Totali Economici
    tot_costo_ind = df_export['Costo Ind. (€)'].sum()
    tot_listino = df_export['Prezzo Vendita (€)'].sum()
    tot_scontato = tot_listino * (1 - (sconto_fin / 100))
    tot_finale = tot_scontato * (1 + (ricarico_mont / 100))

    df_totali = pd.DataFrame({
        'Parametro': [
            'Totale Costo Industriale (€)',
            f'Totale Listino (Ricarico {ricarico_proj}%) (€)',
            f'Totale Scontato ({sconto_fin}%) (€)',
            f'Totale Finale con Montaggio ({ricarico_mont}%) (€)',
        ],
        'Valore (€)': [
            round(tot_costo_ind, 2),
            round(tot_listino, 2),
            round(tot_scontato, 2),
            round(tot_finale, 2),
        ],
    })
    df_totali.to_excel(writer, sheet_name='Sintesi Economica', index=False)

  output.seek(0)
  return output


# ==========================================
# 2. ESPORTAZIONE PDF (Per Cliente Finale)
# ==========================================
def genera_pdf_preventivo(
    df_moduli, cliente_nome, indirizzo, sconto_fin, ricarico_mont, ricarico_proj
):
  buffer = io.BytesIO()
  doc = SimpleDocTemplate(
      buffer,
      pagesize=A4,
      rightMargin=36,
      leftMargin=36,
      topMargin=36,
      bottomMargin=36,
  )
  story = []
  styles = getSampleStyleSheet()

  # Stili personalizzati
  title_style = ParagraphStyle(
      'DocTitle',
      parent=styles['Heading1'],
      fontSize=20,
      leading=24,
      textColor=colors.HexColor('#1E293B'),
  )
  subtitle_style = ParagraphStyle(
      'DocSubtitle',
      parent=styles['Normal'],
      fontSize=10,
      textColor=colors.HexColor('#64748B'),
  )

  # Intestazione Documento
  story.append(Paragraph('<b>PREVENTIVO ARREDI SU MISURA</b>', title_style))
  story.append(
      Paragraph(
          f'Cliente: <b>{cliente_nome}</b> | Indirizzo:'
          f' {indirizzo or "N/D"}',
          subtitle_style,
      )
  )
  story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#CBD5E1'), spaceAfter=15))

  # Tabella Moduli (Vengono mostrati al cliente i prezzi ricaricati, SENZA mostrare i costi industriali)
  headers = ['Ambiente', 'Modulo', 'Dimensioni (LxHxP)', 'Prezzo Listino']
  data_table = [headers]

  tot_listino = 0.0
  for _, row in df_moduli.iterrows():
    prezzo_ricaricato = float(row['costo_industriale']) * (
        1 + (ricarico_proj / 100)
    )
    tot_listino += prezzo_ricaricato

    dims = f"{row['larghezza_mm']}x{row['altezza_mm']}x{row['profondita_mm']} mm"
    data_table.append([
        row['ambiente'],
        row['nome_modulo'],
        dims,
        f'€ {prezzo_ricaricato:.2f}',
    ])

  # Calcoli Totali
  tot_scontato = tot_listino * (1 - (sconto_fin / 100))
  tot_finale = tot_scontato * (1 + (ricarico_mont / 100))

  t_moduli = Table(data_table, colWidths=[120, 200, 110, 90])
  t_moduli.setStyle(
      TableStyle([
          ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
          ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
          ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
          ('FONTSIZE', (0, 0), (-1, -1), 9),
          ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
          ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
          ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
      ])
  )
  story.append(t_moduli)
  story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#CBD5E1'), spaceBefore=15, spaceAfter=10))

  # Tabella Totali Finale
  data_totali = [
      ['Totale Listino Interventi:', f'€ {tot_listino:.2f}'],
      [f'Sconto Concesso ({sconto_fin}%):', f'- € {(tot_listino - tot_scontato):.2f}'],
      [f'Servizio Trasporto & Montaggio ({ricarico_mont}%):', f'+ € {(tot_finale - tot_scontato):.2f}'],
      ['TOTALE GENERALE PREVENTIVO (IVA Esclusa):', f'€ {tot_finale:.2f}'],
  ]

  t_totali = Table(data_totali, colWidths=[330, 190])
  t_totali.setStyle(
      TableStyle([
          ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
          ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
          ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
          ('FONTSIZE', (0, -1), (-1, -1), 11),
          ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#0F766E')),
          ('TOPPADDING', (0, -1), (-1, -1), 8),
      ])
  )
  story.append(t_totali)

  doc.build(story)
  buffer.seek(0)
  return buffer
