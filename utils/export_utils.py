from __future__ import annotations

import io
from typing import List
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode('utf-8')


def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='comparison')
    buf.seek(0)
    return buf.read()


def df_to_pdf_bytes(title: str, df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    elems = []
    elems.append(Paragraph(title, styles['Heading1']))
    elems.append(Spacer(1, 12))

    # create table data
    data = [list(df.columns)] + df.astype(str).values.tolist()
    table = Table(data, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
    ]))
    elems.append(table)
    elems.append(Spacer(1, 12))

    # Add a simple chart if possible using matplotlib
    try:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 2))
        if 'net_total_cost' in df.columns:
            ax.plot(df.index, df['net_total_cost'], marker='o')
            ax.set_title('Net Total Cost')
        elif 'cheese_mass_kg' in df.columns:
            ax.plot(df.index, df['cheese_mass_kg'], marker='o')
            ax.set_title('Mass')
        else:
            ax.plot(df.index, df.iloc[:, 0], marker='o')
        ax.grid(True, linestyle='--', alpha=0.3)
        from reportlab.lib.utils import ImageReader
        img_buf = io.BytesIO()
        fig.tight_layout()
        fig.savefig(img_buf, format='png', dpi=150)
        plt.close(fig)
        img_buf.seek(0)
        elems.append(ImageReader(img_buf))
    except Exception:
        pass

    doc.build(elems)
    buf.seek(0)
    return buf.read()
