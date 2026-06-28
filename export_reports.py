import os
import csv
import re
from datetime import datetime, timedelta

import xlsxwriter
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

import database as db

APP_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(APP_DIR, "logo.png")


def _format_phone(phone):
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return phone or ""


def _get_company_header():
    info = db.load_company_info()
    return {
        "name": info.get("Company Name", "").upper(),
        "phone": _format_phone(info.get("Phone Number", "")),
        "email": info.get("Email", ""),
        "hic": info.get("HIC Number", ""),
    }


def _has_logo():
    return os.path.exists(LOGO_PATH)


def _prior_period(date_from, date_to):
    d1 = datetime.strptime(date_from, "%Y-%m-%d")
    d2 = datetime.strptime(date_to, "%Y-%m-%d")
    duration = (d2 - d1).days + 1
    prior_end = d1 - timedelta(days=1)
    prior_start = prior_end - timedelta(days=duration - 1)
    return prior_start.strftime("%Y-%m-%d"), prior_end.strftime("%Y-%m-%d")


def _format_date_display(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")
    except (ValueError, TypeError):
        return date_str or ""


# ─── PDF Export ───

def _build_pdf_header(elements, styles, title, date_from=None, date_to=None):
    company = _get_company_header()

    header_style = ParagraphStyle("CompanyHeader", parent=styles["Heading1"], fontSize=16, spaceAfter=4, fontName="Helvetica-Bold")
    sub_style = ParagraphStyle("CompanySub", parent=styles["Normal"], fontSize=10, spaceAfter=2, fontName="Helvetica-Bold")

    info_parts = []
    if company["phone"]:
        info_parts.append(company["phone"])
    if company["email"]:
        info_parts.append(company["email"])
    if company["hic"]:
        info_parts.append(f"HIC# {company['hic']}")

    if _has_logo():
        logo = Image(LOGO_PATH, width=0.9 * inch, height=0.9 * inch)
        header_content = []
        if company["name"]:
            header_content.append(Paragraph(company["name"], header_style))
        if info_parts:
            header_content.append(Paragraph("  |  ".join(info_parts), sub_style))
        header_table_data = [[logo, header_content]]
        header_table = Table(header_table_data, colWidths=[1.1 * inch, 5.3 * inch])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        elements.append(header_table)
    else:
        if company["name"]:
            elements.append(Paragraph(company["name"], header_style))
        if info_parts:
            elements.append(Paragraph("  |  ".join(info_parts), sub_style))

    elements.append(Spacer(1, 14))

    title_style = ParagraphStyle("ReportTitle", parent=styles["Heading2"], fontSize=14, spaceAfter=4)
    elements.append(Paragraph(title, title_style))

    period_style = ParagraphStyle("Period", parent=styles["Normal"], fontSize=10, spaceAfter=2)
    if date_from and date_to:
        period = f"{_format_date_display(date_from)} – {_format_date_display(date_to)}"
        elements.append(Paragraph(period, period_style))

    gen_style = ParagraphStyle("Gen", parent=styles["Normal"], fontSize=8, spaceAfter=2, textColor=colors.gray)
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%m/%d/%Y')}", gen_style))
    elements.append(Spacer(1, 15))


def export_pl_pdf(filepath, date_from=None, date_to=None, compare=False):
    transactions = db.get_transactions(date_from, date_to)
    income, cogs, expenses = _compute_pl(transactions)

    total_income = sum(income.values())
    total_cogs = sum(cogs.values())
    gross_profit = total_income - total_cogs
    total_expenses = sum(expenses.values())
    net_income = gross_profit - total_expenses
    margin = (net_income / total_income * 100) if total_income != 0 else 0

    prior_income_t = prior_cogs_t = prior_expenses_t = prior_gross = prior_net = 0
    prior_income = {}
    prior_cogs = {}
    prior_expenses = {}
    prior_from = prior_to = None

    if compare and date_from and date_to:
        prior_from, prior_to = _prior_period(date_from, date_to)
        prior_txns = db.get_transactions(prior_from, prior_to)
        prior_income, prior_cogs, prior_expenses = _compute_pl(prior_txns)
        prior_income_t = sum(prior_income.values())
        prior_cogs_t = sum(prior_cogs.values())
        prior_gross = prior_income_t - prior_cogs_t
        prior_expenses_t = sum(prior_expenses.values())
        prior_net = prior_gross - prior_expenses_t

    doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    elements = []

    _build_pdf_header(elements, styles, "Profit & Loss Statement", date_from, date_to)

    if compare and prior_from:
        col_headers = ["Category", "Current Period", "Prior Period", "Change"]
        col_widths = [3 * inch, 1.3 * inch, 1.3 * inch, 1 * inch]
    else:
        col_headers = ["Category", "Amount"]
        col_widths = [4 * inch, 2 * inch]

    data = [col_headers]

    def add_row(label, current, prior=0):
        row = [label, f"${current:,.2f}"]
        if compare and prior_from:
            row.append(f"${prior:,.2f}")
            change = current - prior
            row.append(f"${change:+,.2f}")
        data.append(row)

    data.append(["INCOME"] + [""] * (len(col_headers) - 1))
    all_income_cats = sorted(set(list(income.keys()) + list(prior_income.keys())))
    for name in all_income_cats:
        add_row(f"  {name}", income.get(name, 0), prior_income.get(name, 0))
    add_row("Total Income", total_income, prior_income_t)
    data.append([""] * len(col_headers))

    data.append(["COST OF GOODS SOLD"] + [""] * (len(col_headers) - 1))
    all_cogs_cats = sorted(set(list(cogs.keys()) + list(prior_cogs.keys())))
    for name in all_cogs_cats:
        add_row(f"  {name}", cogs.get(name, 0), prior_cogs.get(name, 0))
    add_row("Total COGS", total_cogs, prior_cogs_t)
    data.append([""] * len(col_headers))

    add_row("GROSS PROFIT", gross_profit, prior_gross)
    data.append([""] * len(col_headers))

    data.append(["EXPENSES"] + [""] * (len(col_headers) - 1))
    all_exp_cats = sorted(set(list(expenses.keys()) + list(prior_expenses.keys())))
    for name in all_exp_cats:
        add_row(f"  {name}", expenses.get(name, 0), prior_expenses.get(name, 0))
    add_row("Total Expenses", total_expenses, prior_expenses_t)
    data.append([""] * len(col_headers))

    add_row("NET INCOME", net_income, prior_net)

    margin_row = [f"Net Profit Margin: {margin:.1f}%"] + [""] * (len(col_headers) - 1)
    data.append(margin_row)

    table = Table(data, colWidths=col_widths)
    style_cmds = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
        ("LINEABOVE", (0, -2), (-1, -2), 1, colors.black),
        ("FONTNAME", (0, -2), (-1, -2), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (0, -1), 9),
        ("TEXTCOLOR", (0, -1), (0, -1), colors.HexColor("#444444")),
    ]
    table.setStyle(TableStyle(style_cmds))
    elements.append(table)
    doc.build(elements)


def export_bs_pdf(filepath):
    transactions = db.get_transactions()
    assets, liabilities, equity = _compute_bs(transactions)

    total_assets = sum(assets.values())
    total_liabilities = sum(liabilities.values())
    total_equity = sum(equity.values())

    doc = SimpleDocTemplate(filepath, pagesize=letter, topMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    elements = []

    _build_pdf_header(elements, styles, "Balance Sheet")

    data = [["Category", "Amount"]]
    data.append(["ASSETS", ""])
    for name, val in sorted(assets.items()):
        data.append([f"  {name}", f"${val:,.2f}"])
    data.append(["Total Assets", f"${total_assets:,.2f}"])
    data.append(["", ""])
    data.append(["LIABILITIES", ""])
    for name, val in sorted(liabilities.items()):
        data.append([f"  {name}", f"${val:,.2f}"])
    data.append(["Total Liabilities", f"${total_liabilities:,.2f}"])
    data.append(["", ""])
    data.append(["EQUITY", ""])
    for name, val in sorted(equity.items()):
        data.append([f"  {name}", f"${val:,.2f}"])
    data.append(["Total Equity", f"${total_equity:,.2f}"])
    data.append(["", ""])
    data.append(["LIABILITIES + EQUITY", f"${total_liabilities + total_equity:,.2f}"])

    table = Table(data, colWidths=[4 * inch, 2 * inch])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    elements.append(table)
    doc.build(elements)


# ─── CSV Export ───

def export_pl_csv(filepath, date_from=None, date_to=None, compare=False):
    transactions = db.get_transactions(date_from, date_to)
    income, cogs, expenses = _compute_pl(transactions)

    total_income = sum(income.values())
    total_cogs = sum(cogs.values())
    gross_profit = total_income - total_cogs
    total_expenses = sum(expenses.values())
    net_income = gross_profit - total_expenses
    margin = (net_income / total_income * 100) if total_income != 0 else 0

    prior_income = {}
    prior_cogs = {}
    prior_expenses = {}
    prior_from = prior_to = None

    if compare and date_from and date_to:
        prior_from, prior_to = _prior_period(date_from, date_to)
        prior_txns = db.get_transactions(prior_from, prior_to)
        prior_income, prior_cogs, prior_expenses = _compute_pl(prior_txns)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        company = _get_company_header()
        writer.writerow([company["name"]])
        info_parts = []
        if company["phone"]:
            info_parts.append(company["phone"])
        if company["email"]:
            info_parts.append(company["email"])
        if company["hic"]:
            info_parts.append(f"HIC# {company['hic']}")
        writer.writerow(["  |  ".join(info_parts)])
        writer.writerow([])
        writer.writerow(["Profit & Loss Statement"])
        if date_from and date_to:
            writer.writerow([f"{_format_date_display(date_from)} - {_format_date_display(date_to)}"])
        writer.writerow([f"Generated: {datetime.now().strftime('%m/%d/%Y')}"])
        writer.writerow([])

        if compare and prior_from:
            writer.writerow(["Category", "Current Period", "Prior Period", "Change"])
        else:
            writer.writerow(["Category", "Amount"])

        def write_row(label, current, prior=0):
            row = [label, f"{current:.2f}"]
            if compare and prior_from:
                row.append(f"{prior:.2f}")
                row.append(f"{current - prior:+.2f}")
            writer.writerow(row)

        writer.writerow(["INCOME"])
        all_income_cats = sorted(set(list(income.keys()) + list(prior_income.keys())))
        for name in all_income_cats:
            write_row(f"  {name}", income.get(name, 0), prior_income.get(name, 0))
        write_row("Total Income", total_income, sum(prior_income.values()))
        writer.writerow([])

        writer.writerow(["COST OF GOODS SOLD"])
        all_cogs_cats = sorted(set(list(cogs.keys()) + list(prior_cogs.keys())))
        for name in all_cogs_cats:
            write_row(f"  {name}", cogs.get(name, 0), prior_cogs.get(name, 0))
        write_row("Total COGS", total_cogs, sum(prior_cogs.values()))
        writer.writerow([])

        write_row("GROSS PROFIT", gross_profit, sum(prior_income.values()) - sum(prior_cogs.values()))
        writer.writerow([])

        writer.writerow(["EXPENSES"])
        all_exp_cats = sorted(set(list(expenses.keys()) + list(prior_expenses.keys())))
        for name in all_exp_cats:
            write_row(f"  {name}", expenses.get(name, 0), prior_expenses.get(name, 0))
        write_row("Total Expenses", total_expenses, sum(prior_expenses.values()))
        writer.writerow([])

        prior_net = (sum(prior_income.values()) - sum(prior_cogs.values())) - sum(prior_expenses.values())
        write_row("NET INCOME", net_income, prior_net)
        writer.writerow([f"Net Profit Margin: {margin:.1f}%"])


def export_bs_csv(filepath):
    transactions = db.get_transactions()
    assets, liabilities, equity = _compute_bs(transactions)

    total_assets = sum(assets.values())
    total_liabilities = sum(liabilities.values())
    total_equity = sum(equity.values())

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        company = _get_company_header()
        writer.writerow([company["name"]])
        info_parts = []
        if company["phone"]:
            info_parts.append(company["phone"])
        if company["email"]:
            info_parts.append(company["email"])
        if company["hic"]:
            info_parts.append(f"HIC# {company['hic']}")
        writer.writerow(["  |  ".join(info_parts)])
        writer.writerow([])
        writer.writerow(["Balance Sheet"])
        writer.writerow([f"Generated: {datetime.now().strftime('%m/%d/%Y')}"])
        writer.writerow([])
        writer.writerow(["Category", "Amount"])
        writer.writerow(["ASSETS", ""])
        for name, val in sorted(assets.items()):
            writer.writerow([f"  {name}", f"{val:.2f}"])
        writer.writerow(["Total Assets", f"{total_assets:.2f}"])
        writer.writerow([])
        writer.writerow(["LIABILITIES", ""])
        for name, val in sorted(liabilities.items()):
            writer.writerow([f"  {name}", f"{val:.2f}"])
        writer.writerow(["Total Liabilities", f"{total_liabilities:.2f}"])
        writer.writerow([])
        writer.writerow(["EQUITY", ""])
        for name, val in sorted(equity.items()):
            writer.writerow([f"  {name}", f"{val:.2f}"])
        writer.writerow(["Total Equity", f"{total_equity:.2f}"])
        writer.writerow([])
        writer.writerow(["LIABILITIES + EQUITY", f"{total_liabilities + total_equity:.2f}"])


# ─── Helpers ───

def _compute_pl(transactions):
    income = {}
    cogs = {}
    expenses = {}
    for txn in transactions:
        _, _, _, amount, cat_type, cat_name, _ = txn
        if not cat_type:
            continue
        if cat_type == "Income":
            income[cat_name] = income.get(cat_name, 0) + amount
        elif cat_type == "COGS":
            cogs[cat_name] = cogs.get(cat_name, 0) + abs(amount)
        elif cat_type == "Expense":
            expenses[cat_name] = expenses.get(cat_name, 0) + abs(amount)
    return income, cogs, expenses


def _compute_bs(transactions):
    assets = {}
    liabilities = {}
    equity = {}
    for txn in transactions:
        _, _, _, amount, cat_type, cat_name, _ = txn
        if not cat_type:
            continue
        if cat_type == "Asset":
            assets[cat_name] = assets.get(cat_name, 0) + amount
        elif cat_type == "Liability":
            liabilities[cat_name] = liabilities.get(cat_name, 0) + abs(amount)
        elif cat_type == "Equity":
            equity[cat_name] = equity.get(cat_name, 0) + amount
    return assets, liabilities, equity
