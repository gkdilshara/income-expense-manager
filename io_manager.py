"""
io_manager.py - Import/Export manager for multiple file formats
"""

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from models import Transaction, Account


# ─── Export ───────────────────────────────────────────────────────────────────

def export_transactions(transactions: List[Transaction],
                        filepath: str,
                        fmt: str,
                        account_name: str = "") -> Tuple[bool, str]:
    """Export transactions to various formats."""
    fmt = fmt.lower().strip()
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if fmt == "csv":
            return _export_csv(transactions, path)
        elif fmt == "json":
            return _export_json(transactions, path)
        elif fmt == "xlsx":
            return _export_xlsx(transactions, path)
        elif fmt == "txt":
            return _export_txt(transactions, path, account_name)
        elif fmt == "pdf":
            return _export_pdf(transactions, path, account_name)
        else:
            return False, f"Unsupported format: {fmt}"
    except Exception as e:
        return False, f"Export failed: {e}"


def _export_csv(transactions: List[Transaction], path: Path) -> Tuple[bool, str]:
    if not transactions:
        return False, "No transactions to export."
    fields = ["id", "date", "type", "amount", "category", "description",
              "method_name", "tags", "notes", "is_recurring", "recurrence", "created_at"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for t in transactions:
            row = {k: getattr(t, k, "") for k in fields}
            writer.writerow(row)
    return True, f"Exported {len(transactions)} transactions to {path}"


def _export_json(transactions: List[Transaction], path: Path) -> Tuple[bool, str]:
    data = {
        "exported_at": datetime.now().isoformat(),
        "count": len(transactions),
        "transactions": [t.to_dict() for t in transactions]
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    return True, f"Exported {len(transactions)} transactions to {path}"


def _export_xlsx(transactions: List[Transaction], path: Path) -> Tuple[bool, str]:
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        return False, "openpyxl not installed. Run: pip install openpyxl"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Transactions"

    # Header style
    hdr_font = Font(bold=True, color="FFFFFF")
    hdr_fill = PatternFill("solid", fgColor="1F4E79")
    hdr_align = Alignment(horizontal="center", vertical="center")

    headers = ["Date", "Type", "Amount", "Category", "Description",
               "Method", "Tags", "Notes", "Recurring", "Created At"]
    fields  = ["date", "type", "amount", "category", "description",
               "method_name", "tags", "notes", "is_recurring", "created_at"]

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = hdr_align

    # Alternate row colors
    green_fill = PatternFill("solid", fgColor="E8F5E9")
    red_fill   = PatternFill("solid", fgColor="FFEBEE")

    for row_idx, t in enumerate(transactions, 2):
        row_fill = green_fill if t.type == "income" else red_fill
        for col, field in enumerate(fields, 1):
            val = getattr(t, field, "")
            cell = ws.cell(row=row_idx, column=col, value=val)
            cell.fill = row_fill
            if field == "amount":
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal="right")

    # Auto-width
    for col in range(1, len(headers) + 1):
        max_len = 0
        col_letter = get_column_letter(col)
        for row in ws.iter_rows(min_col=col, max_col=col):
            for cell in row:
                try:
                    max_len = max(max_len, len(str(cell.value or "")))
                except Exception:
                    pass
        ws.column_dimensions[col_letter].width = min(max_len + 4, 40)

    # Summary sheet
    ws2 = wb.create_sheet("Summary")
    total_income  = sum(t.amount for t in transactions if t.type == "income")
    total_expense = sum(t.amount for t in transactions if t.type == "expense")
    summary_data = [
        ("Generated At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Total Transactions", len(transactions)),
        ("Total Income",   total_income),
        ("Total Expenses", total_expense),
        ("Net Balance",    total_income - total_expense),
    ]
    for row_idx, (k, v) in enumerate(summary_data, 1):
        ws2.cell(row=row_idx, column=1, value=k).font = Font(bold=True)
        ws2.cell(row=row_idx, column=2, value=v)

    wb.save(path)
    return True, f"Exported {len(transactions)} transactions to {path} (Excel)"


def _export_txt(transactions: List[Transaction], path: Path, account_name: str) -> Tuple[bool, str]:
    total_income  = sum(t.amount for t in transactions if t.type == "income")
    total_expense = sum(t.amount for t in transactions if t.type == "expense")
    net = total_income - total_expense

    with open(path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write(f"  INCOME & EXPENSES REPORT\n")
        if account_name:
            f.write(f"  Account: {account_name}\n")
        f.write(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"  Total Transactions : {len(transactions)}\n")
        f.write(f"  Total Income       : {total_income:,.2f}\n")
        f.write(f"  Total Expenses     : {total_expense:,.2f}\n")
        f.write(f"  Net Balance        : {net:,.2f}\n\n")
        f.write("-" * 70 + "\n")
        f.write(f"{'Date':<12} {'Type':<10} {'Amount':>12} {'Category':<20} {'Description':<20}\n")
        f.write("-" * 70 + "\n")

        for t in transactions:
            sign = "+" if t.type == "income" else "-"
            f.write(f"{t.date:<12} {t.type:<10} {sign}{t.amount:>11,.2f} "
                    f"{(t.category or '')[:20]:<20} {(t.description or '')[:20]:<20}\n")

        f.write("=" * 70 + "\n")
        f.write("  Created by Sasindu Dilshara | Income & Expenses Manager CLI\n")
        f.write("=" * 70 + "\n")

    return True, f"Exported {len(transactions)} transactions to {path} (TXT)"


def _export_pdf(transactions: List[Transaction], path: Path, account_name: str) -> Tuple[bool, str]:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import cm
    except ImportError:
        # Fallback: generate PDF-like TXT
        txt_path = path.with_suffix(".txt")
        ok, msg = _export_txt(transactions, txt_path, account_name)
        return ok, msg + " (PDF not available, saved as TXT — install reportlab for PDF)"

    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle("title", parent=styles["Title"],
                                  textColor=colors.HexColor("#1F4E79"))
    story.append(Paragraph("Income & Expenses Report", title_style))
    if account_name:
        story.append(Paragraph(f"Account: {account_name}", styles["Normal"]))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
    story.append(Spacer(1, 0.5 * cm))

    # Summary table
    total_income  = sum(t.amount for t in transactions if t.type == "income")
    total_expense = sum(t.amount for t in transactions if t.type == "expense")
    net = total_income - total_expense
    summary_data = [
        ["Metric", "Value"],
        ["Total Transactions", str(len(transactions))],
        ["Total Income",   f"{total_income:,.2f}"],
        ["Total Expenses", f"{total_expense:,.2f}"],
        ["Net Balance",    f"{net:,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[8*cm, 8*cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.lightgrey, colors.white]),
        ("BOX",   (0,0), (-1,-1), 0.5, colors.grey),
        ("GRID",  (0,0), (-1,-1), 0.25, colors.grey),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.5 * cm))

    # Transactions table
    headers = ["Date", "Type", "Amount", "Category", "Description"]
    rows = [headers]
    for t in transactions:
        sign = "+" if t.type == "income" else "-"
        rows.append([
            t.date,
            t.type.capitalize(),
            f"{sign}{t.amount:,.2f}",
            (t.category or "")[:25],
            (t.description or "")[:30],
        ])

    txn_table = Table(rows, colWidths=[2.5*cm, 2.5*cm, 3*cm, 4*cm, 5*cm])
    txn_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2E7D32")),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#E8F5E9"), colors.white]),
        ("BOX",  (0,0), (-1,-1), 0.5, colors.grey),
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
    ]))
    story.append(txn_table)
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("Created by Sasindu Dilshara | Income & Expenses Manager CLI",
                            styles["Normal"]))

    doc.build(story)
    return True, f"Exported {len(transactions)} transactions to {path} (PDF)"


# ─── Import ───────────────────────────────────────────────────────────────────

def import_transactions(filepath: str, account_id: str,
                         fmt: str = None) -> Tuple[bool, str, List[Transaction]]:
    """Import transactions from file."""
    path = Path(filepath)
    if not path.exists():
        return False, f"File not found: {filepath}", []

    if fmt is None:
        fmt = path.suffix.lstrip(".").lower()

    try:
        if fmt == "csv":
            return _import_csv(path, account_id)
        elif fmt == "json":
            return _import_json(path, account_id)
        elif fmt in ("xlsx", "xls"):
            return _import_xlsx(path, account_id)
        else:
            return False, f"Unsupported import format: {fmt}", []
    except Exception as e:
        return False, f"Import failed: {e}", []


def _import_csv(path: Path, account_id: str) -> Tuple[bool, str, List[Transaction]]:
    txns = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                t = _row_to_transaction(row, account_id)
                if t:
                    txns.append(t)
            except Exception:
                continue
    return True, f"Imported {len(txns)} transactions from CSV", txns


def _import_json(path: Path, account_id: str) -> Tuple[bool, str, List[Transaction]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = data if isinstance(data, list) else data.get("transactions", [])
    txns = []
    for row in rows:
        try:
            row["account_id"] = account_id
            t = Transaction.from_dict(row)
            txns.append(t)
        except Exception:
            continue
    return True, f"Imported {len(txns)} transactions from JSON", txns


def _import_xlsx(path: Path, account_id: str) -> Tuple[bool, str, List[Transaction]]:
    try:
        import openpyxl
    except ImportError:
        return False, "openpyxl not installed.", []

    wb = openpyxl.load_workbook(path)
    ws = wb.active
    headers = [str(c.value).lower().strip() if c.value else "" for c in ws[1]]
    txns = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        row_dict = dict(zip(headers, row))
        row_dict["account_id"] = account_id
        try:
            t = _row_to_transaction(row_dict, account_id)
            if t:
                txns.append(t)
        except Exception:
            continue
    return True, f"Imported {len(txns)} transactions from Excel", txns


def _row_to_transaction(row: dict, account_id: str) -> Optional[Transaction]:
    """Convert a dict row to a Transaction object with robust column header lookup."""
    try:
        from models import Transaction, new_id
        norm_row = {str(k).lower().strip(): v for k, v in row.items() if k is not None}

        def get_val(*keys, default=""):
            for k in keys:
                if k in norm_row and norm_row[k] is not None and str(norm_row[k]).strip() != "":
                    return norm_row[k]
            return default

        txn_type = str(get_val("type", "transaction_type", default="expense")).lower().strip()
        if txn_type not in ("income", "expense"):
            txn_type = "expense"

        amount_raw = get_val("amount", "val", "price", "cost", "value", default="0")
        try:
            amount = float(str(amount_raw).replace(",", "").replace("$", "").replace("+", "").replace("-", "").strip())
        except Exception:
            amount = 0.0

        date_raw = str(get_val("date", "created_at", "timestamp", "txn_date", default=datetime.now().strftime("%Y-%m-%d")))
        txn_date = date_raw[:10].strip()

        return Transaction(
            id=str(get_val("id", default=new_id())),
            account_id=account_id,
            type=txn_type,
            amount=amount,
            category=str(get_val("category", "cat", "category_name", default="Other")).strip(),
            description=str(get_val("description", "desc", "details", "memo", default="")).strip(),
            method_name=str(get_val("method_name", "method", "payment_method", default="")).strip(),
            tags=str(get_val("tags", "tag", default="")).strip(),
            date=txn_date,
            notes=str(get_val("notes", "note", default="")).strip(),
        )
    except Exception:
        return None


