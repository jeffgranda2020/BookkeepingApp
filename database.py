import sqlite3
import sys
import os
import hashlib
import secrets
from datetime import datetime


def _app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


DB_PATH = os.path.join(_app_dir(), "bookkeeping.db")
DB_BACKUP_PATH = os.path.join(_app_dir(), "bookkeeping_backup.db")


def backup_database():
    if os.path.exists(DB_PATH):
        import shutil
        shutil.copy2(DB_PATH, DB_BACKUP_PATH)

DEFAULT_CATEGORIES = [
    # Income
    ("Income", "Flooring Job Revenue"),
    ("Income", "Materials Markup"),
    ("Income", "Other Income"),
    # Cost of Goods Sold
    ("COGS", "Materials"),
    ("COGS", "Subcontractor Labor"),
    ("COGS", "Direct Labor"),
    # Expenses (IRS Schedule C aligned for CT Construction)
    ("Expense", "Advertising"),
    ("Expense", "Car & Truck Expenses"),
    ("Expense", "Commissions & Fees"),
    ("Expense", "Contract Labor"),
    ("Expense", "Depreciation"),
    ("Expense", "Insurance"),
    ("Expense", "Interest - Mortgage"),
    ("Expense", "Interest - Other"),
    ("Expense", "Legal & Professional Services"),
    ("Expense", "Office Expense"),
    ("Expense", "Rent - Vehicles & Equipment"),
    ("Expense", "Rent - Other Business Property"),
    ("Expense", "Repairs & Maintenance"),
    ("Expense", "Supplies"),
    ("Expense", "Taxes & Licenses"),
    ("Expense", "Travel"),
    ("Expense", "Meals (50% Deductible)"),
    ("Expense", "Utilities"),
    ("Expense", "Wages"),
    ("Expense", "Tools & Equipment"),
    ("Expense", "Gas & Fuel"),
    ("Expense", "Phone & Communication"),
    ("Expense", "Uniforms & Work Clothes"),
    ("Expense", "Continuing Education"),
    ("Expense", "Bank & Merchant Fees"),
    ("Expense", "Permits & Inspections"),
    ("Expense", "Dump Fees & Disposal"),
    ("Expense", "Other Expenses"),
    # Assets / Liabilities (for Balance Sheet)
    ("Asset", "Cash & Bank Accounts"),
    ("Asset", "Accounts Receivable"),
    ("Asset", "Equipment"),
    ("Asset", "Vehicles"),
    ("Asset", "Inventory - Materials"),
    ("Liability", "Accounts Payable"),
    ("Liability", "Credit Cards"),
    ("Liability", "Loans Payable"),
    ("Liability", "Taxes Payable"),
    ("Equity", "Owner's Equity"),
    ("Equity", "Owner's Draw"),
    ("Equity", "Retained Earnings"),
]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate_add_user_id(cursor):
    tables_needing_user_id = [
        "company_info", "categories", "transactions", "contractors",
        "clients", "services", "invoices", "invoice_jobs", "invoice_lines", "sub_payments"
    ]
    for table in tables_needing_user_id:
        try:
            cursor.execute(f"SELECT user_id FROM {table} LIMIT 1")
        except sqlite3.OperationalError:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER")
            except sqlite3.OperationalError:
                pass


def has_legacy_data():
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT COUNT(*) FROM transactions WHERE user_id IS NULL")
        txn_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM contractors WHERE user_id IS NULL")
        con_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM clients WHERE user_id IS NULL")
        cli_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM invoices WHERE user_id IS NULL")
        inv_count = c.fetchone()[0]
        conn.close()
        return (txn_count + con_count + cli_count + inv_count) > 0
    except sqlite3.OperationalError:
        conn.close()
        return False


def adopt_legacy_data(user_id):
    conn = get_connection()
    c = conn.cursor()
    tables = [
        "company_info", "categories", "transactions", "contractors",
        "clients", "services", "invoices", "invoice_jobs", "invoice_lines", "sub_payments"
    ]
    for table in tables:
        c.execute(f"UPDATE {table} SET user_id = ? WHERE user_id IS NULL", (user_id,))
    conn.commit()
    conn.close()


def _hash_password(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()


def create_user(username, password):
    salt = secrets.token_hex(16)
    password_hash = _hash_password(password, salt)
    created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO users (username, password_hash, salt, created_date) VALUES (?, ?, ?, ?)",
            (username, password_hash, salt, created),
        )
        conn.commit()
        user_id = c.lastrowid
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None


def verify_user(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, password_hash, salt FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    user_id, stored_hash, salt = row
    if _hash_password(password, salt) == stored_hash:
        return user_id
    return None


def get_user_count():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count


def save_security_questions(user_id, qa_pairs):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM security_questions WHERE user_id = ?", (user_id,))
    for question, answer in qa_pairs:
        salt = secrets.token_hex(16)
        answer_hash = _hash_password(answer.strip().lower(), salt)
        c.execute(
            "INSERT INTO security_questions (user_id, question, answer_hash, salt) VALUES (?, ?, ?, ?)",
            (user_id, question, answer_hash, salt),
        )
    conn.commit()
    conn.close()


def get_security_questions(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    user_id = row[0]
    c.execute("SELECT question, answer_hash, salt FROM security_questions WHERE user_id = ?", (user_id,))
    questions = c.fetchall()
    conn.close()
    if not questions:
        return None
    return user_id, questions


def verify_security_answers(user_id, answers):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT answer_hash, salt FROM security_questions WHERE user_id = ? ORDER BY id", (user_id,))
    rows = c.fetchall()
    conn.close()
    if len(answers) != len(rows):
        return False
    for answer, (stored_hash, salt) in zip(answers, rows):
        if _hash_password(answer.strip().lower(), salt) != stored_hash:
            return False
    return True


def reset_password(user_id, new_password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT password_hash, salt FROM users WHERE id = ?", (user_id,))
    old_hash, old_salt = c.fetchone()
    if _hash_password(new_password, old_salt) == old_hash:
        conn.close()
        return False
    new_salt = secrets.token_hex(16)
    new_hash = _hash_password(new_password, new_salt)
    c.execute("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?", (new_hash, new_salt, user_id))
    conn.commit()
    conn.close()
    return True


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_date TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS security_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Add user_id column to existing tables if not present
    _migrate_add_user_id(c)

    c.execute("""
        CREATE TABLE IF NOT EXISTS company_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            value TEXT,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(key, user_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_type TEXT NOT NULL,
            name TEXT NOT NULL,
            user_id INTEGER,
            UNIQUE(category_type, name, user_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            description TEXT,
            amount REAL NOT NULL,
            category_id INTEGER,
            source TEXT,
            user_id INTEGER,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS contractors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contractor_type TEXT NOT NULL,
            code_id TEXT NOT NULL,
            name TEXT NOT NULL,
            street TEXT,
            city TEXT,
            state TEXT,
            zipcode TEXT,
            phone TEXT,
            email TEXT,
            ein TEXT,
            ssn_tin TEXT,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code_id TEXT NOT NULL,
            name TEXT NOT NULL,
            street TEXT,
            city TEXT,
            state TEXT,
            zipcode TEXT,
            phone TEXT,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT NOT NULL,
            invoice_type TEXT NOT NULL,
            recipient_type TEXT NOT NULL,
            recipient_id INTEGER NOT NULL,
            week_number INTEGER,
            date_from TEXT,
            date_to TEXT,
            created_date TEXT NOT NULL,
            status TEXT DEFAULT 'Unpaid',
            payment_method TEXT,
            payment_notes TEXT,
            total REAL DEFAULT 0,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS invoice_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            date TEXT,
            customer_name TEXT,
            mobile_number TEXT,
            job_total REAL DEFAULT 0,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS invoice_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            service TEXT,
            price REAL DEFAULT 0,
            FOREIGN KEY (job_id) REFERENCES invoice_jobs(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS sub_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contractor_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_date TEXT NOT NULL,
            payment_type TEXT NOT NULL,
            period_from TEXT,
            period_to TEXT,
            notes TEXT,
            user_id INTEGER,
            FOREIGN KEY (contractor_id) REFERENCES contractors(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


def seed_defaults_for_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    for cat_type, name in DEFAULT_CATEGORIES:
        c.execute(
            "INSERT OR IGNORE INTO categories (category_type, name, user_id) VALUES (?, ?, ?)",
            (cat_type, name, user_id),
        )

    default_services = [
        "Install Laminate", "Install Vinyl", "Install Hardwood",
        "Install Click Lock Vinyl", "Install Click Lock Hardwood",
        "Install Nail Down Hardwood", "Install 1/4 Round", "Install Baseboard",
        "Leveling Subfloor", "Back Screw Subfloor",
        "Take Up Carpet", "Take Up Ceramic", "Take Up Floating Floor",
        "Remove Existing", "Remove Glue Down Vinyl",
        "Remove & Reset Baseboard", "Remove & Reset Toilet", "Remove & Replace Toilet",
        "Undercut Casing", "Move Appliance", "Move Furniture",
        "Cut Away From Cabinets", "Scribe Seal Fireplace",
        "Custom Work", "Trip Charge", "Tread",
    ]
    for svc in default_services:
        c.execute(
            "INSERT OR IGNORE INTO services (name, user_id) VALUES (?, ?)",
            (svc, user_id),
        )

    conn.commit()
    conn.close()


def save_company_info(data: dict, user_id=None):
    conn = get_connection()
    c = conn.cursor()
    for key, value in data.items():
        c.execute("DELETE FROM company_info WHERE key = ? AND user_id = ?", (key, user_id))
        c.execute(
            "INSERT INTO company_info (key, value, user_id) VALUES (?, ?, ?)",
            (key, value, user_id),
        )
    conn.commit()
    conn.close()


def load_company_info(user_id=None) -> dict:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT key, value FROM company_info WHERE user_id = ?", (user_id,))
    data = dict(c.fetchall())
    conn.close()
    return data


def get_categories(category_type=None, user_id=None):
    conn = get_connection()
    c = conn.cursor()
    if category_type:
        c.execute("SELECT id, category_type, name FROM categories WHERE category_type = ? AND user_id = ? ORDER BY name", (category_type, user_id))
    else:
        c.execute("SELECT id, category_type, name FROM categories WHERE user_id = ? ORDER BY category_type, name", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def add_transaction(date, description, amount, category_id, source="Manual", user_id=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO transactions (date, description, amount, category_id, source, user_id) VALUES (?, ?, ?, ?, ?, ?)",
        (date, description, amount, category_id, source, user_id),
    )
    conn.commit()
    conn.close()


def add_transactions_bulk(rows, user_id=None):
    conn = get_connection()
    c = conn.cursor()
    rows_with_user = [(r[0], r[1], r[2], r[3], r[4], user_id) for r in rows]
    c.executemany(
        "INSERT INTO transactions (date, description, amount, category_id, source, user_id) VALUES (?, ?, ?, ?, ?, ?)",
        rows_with_user,
    )
    conn.commit()
    conn.close()


def get_transactions(start_date=None, end_date=None, user_id=None):
    conn = get_connection()
    c = conn.cursor()
    query = """
        SELECT t.id, t.date, t.description, t.amount, c.category_type, c.name, t.source
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
    """
    params = []
    conditions = ["t.user_id = ?"]
    params.append(user_id)
    if start_date:
        conditions.append("t.date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("t.date <= ?")
        params.append(end_date)
    query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY t.date DESC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows


def update_transaction_category(transaction_id, category_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE transactions SET category_id = ? WHERE id = ?", (category_id, transaction_id))
    conn.commit()
    conn.close()


def delete_transactions(transaction_ids):
    conn = get_connection()
    c = conn.cursor()
    for tid in transaction_ids:
        c.execute("DELETE FROM transactions WHERE id = ?", (tid,))
    conn.commit()
    conn.close()


def add_category(category_type, name, user_id=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO categories (category_type, name, user_id) VALUES (?, ?, ?)",
        (category_type, name, user_id),
    )
    conn.commit()
    inserted = c.rowcount > 0
    conn.close()
    return inserted


# ─── Contractors ───

def _generate_code_id(name):
    words = name.strip().split()
    if len(words) >= 2:
        code = "".join(w[0].upper() for w in words if w)
    elif len(words) == 1:
        code = words[0][:3].upper()
    else:
        code = "X"
    return code


def _ensure_unique_code(code, user_id=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT code_id FROM contractors WHERE code_id LIKE ? AND user_id = ?", (code + "%", user_id))
    existing = [r[0] for r in c.fetchall()]
    conn.close()

    if code not in existing:
        return code

    i = 2
    while f"{code}{i}" in existing:
        i += 1
    return f"{code}{i}"


def add_contractor(contractor_type, name, street="", city="", state="", zipcode="", phone="", email="", ein="", ssn_tin="", user_id=None):
    code = _generate_code_id(name)
    code = _ensure_unique_code(code, user_id)

    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO contractors (contractor_type, code_id, name, street, city, state, zipcode, phone, email, ein, ssn_tin, user_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (contractor_type, code, name, street, city, state, zipcode, phone, email, ein, ssn_tin, user_id),
    )
    conn.commit()
    conn.close()
    return code


def get_contractors(contractor_type=None, user_id=None):
    conn = get_connection()
    c = conn.cursor()
    if contractor_type:
        c.execute("SELECT id, code_id, name, street, city, state, zipcode, phone, email, ein, ssn_tin FROM contractors WHERE contractor_type = ? AND user_id = ? ORDER BY name", (contractor_type, user_id))
    else:
        c.execute("SELECT id, contractor_type, code_id, name, street, city, state, zipcode, phone, email, ein, ssn_tin FROM contractors WHERE user_id = ? ORDER BY contractor_type, name", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def delete_contractor(contractor_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM contractors WHERE id = ?", (contractor_id,))
    conn.commit()
    conn.close()


# ─── Clients (Individual) ───

def _ensure_unique_client_code(code, user_id=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT code_id FROM clients WHERE code_id LIKE ? AND user_id = ?", (code + "%", user_id))
    existing = [r[0] for r in c.fetchall()]
    conn.close()
    if code not in existing:
        return code
    i = 2
    while f"{code}{i}" in existing:
        i += 1
    return f"{code}{i}"


def add_client(name, street="", city="", state="", zipcode="", phone="", user_id=None):
    code = _generate_code_id(name)
    code = _ensure_unique_client_code(code, user_id)
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO clients (code_id, name, street, city, state, zipcode, phone, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (code, name, street, city, state, zipcode, phone, user_id),
    )
    conn.commit()
    conn.close()
    return code


def get_clients(user_id=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, code_id, name, street, city, state, zipcode, phone FROM clients WHERE user_id = ? ORDER BY name", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def delete_client(client_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    conn.commit()
    conn.close()


# ─── Invoices ───

def _next_invoice_number(prefix="INV", user_id=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT invoice_number FROM invoices WHERE invoice_number LIKE ? AND user_id = ? ORDER BY id DESC LIMIT 1", (prefix + "-%", user_id))
    row = c.fetchone()
    conn.close()
    if row:
        try:
            last_num = int(row[0].split("-")[1])
            return f"{prefix}-{last_num + 1:04d}"
        except (IndexError, ValueError):
            pass
    return f"{prefix}-0001"


def create_invoice(invoice_type, recipient_type, recipient_id, week_number=None, date_from=None, date_to=None, user_id=None):
    prefix = "WB" if invoice_type == "Primary" else "INV"
    inv_num = _next_invoice_number(prefix, user_id)
    created = datetime.now().strftime("%Y-%m-%d")

    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO invoices (invoice_number, invoice_type, recipient_type, recipient_id, week_number, date_from, date_to, created_date, status, total, user_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Unpaid', 0, ?)""",
        (inv_num, invoice_type, recipient_type, recipient_id, week_number, date_from, date_to, created, user_id),
    )
    invoice_id = c.lastrowid
    conn.commit()
    conn.close()
    return invoice_id, inv_num


# ─── Services ───

def get_services(user_id=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name FROM services WHERE user_id = ? ORDER BY name", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def add_service(name, user_id=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO services (name, user_id) VALUES (?, ?)", (name, user_id))
    conn.commit()
    inserted = c.rowcount > 0
    conn.close()
    return inserted


def update_service(service_id, new_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE services SET name = ? WHERE id = ?", (new_name, service_id))
    conn.commit()
    conn.close()


def delete_service(service_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM services WHERE id = ?", (service_id,))
    conn.commit()
    conn.close()


# ─── Invoice Jobs & Lines ───

def add_invoice_job(invoice_id, date="", customer_name="", mobile_number=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO invoice_jobs (invoice_id, date, customer_name, mobile_number, job_total) VALUES (?, ?, ?, ?, 0)",
        (invoice_id, date, customer_name, mobile_number),
    )
    job_id = c.lastrowid
    conn.commit()
    conn.close()
    return job_id


def add_invoice_line(job_id, service, price):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO invoice_lines (job_id, service, price) VALUES (?, ?, ?)", (job_id, service, price))
    conn.commit()
    conn.close()


def update_job_total(job_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COALESCE(SUM(price), 0) FROM invoice_lines WHERE job_id = ?", (job_id,))
    total = c.fetchone()[0]
    c.execute("UPDATE invoice_jobs SET job_total = ? WHERE id = ?", (total, job_id))
    conn.commit()
    conn.close()
    return total


def update_invoice_total(invoice_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COALESCE(SUM(job_total), 0) FROM invoice_jobs WHERE invoice_id = ?", (invoice_id,))
    total = c.fetchone()[0]
    c.execute("UPDATE invoices SET total = ? WHERE id = ?", (total, invoice_id))
    conn.commit()
    conn.close()
    return total


def update_invoice_status(invoice_id, status, payment_method=None, payment_notes=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE invoices SET status = ?, payment_method = ?, payment_notes = ? WHERE id = ?",
              (status, payment_method, payment_notes, invoice_id))
    conn.commit()
    conn.close()


def get_invoice(invoice_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, invoice_number, invoice_type, recipient_type, recipient_id, week_number, date_from, date_to, created_date, status, payment_method, payment_notes, total FROM invoices WHERE id = ?", (invoice_id,))
    row = c.fetchone()
    conn.close()
    return row


def get_invoices(invoice_type=None, user_id=None):
    conn = get_connection()
    c = conn.cursor()
    if invoice_type:
        c.execute("SELECT id, invoice_number, invoice_type, recipient_type, recipient_id, week_number, date_from, date_to, created_date, status, total FROM invoices WHERE invoice_type = ? AND user_id = ? ORDER BY id DESC", (invoice_type, user_id))
    else:
        c.execute("SELECT id, invoice_number, invoice_type, recipient_type, recipient_id, week_number, date_from, date_to, created_date, status, total FROM invoices WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def get_invoice_jobs(invoice_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, date, customer_name, mobile_number, job_total FROM invoice_jobs WHERE invoice_id = ? ORDER BY id", (invoice_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def get_job_lines(job_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, service, price FROM invoice_lines WHERE job_id = ? ORDER BY id", (job_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def delete_invoice(invoice_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM invoice_jobs WHERE invoice_id = ?", (invoice_id,))
    job_ids = [r[0] for r in c.fetchall()]
    for jid in job_ids:
        c.execute("DELETE FROM invoice_lines WHERE job_id = ?", (jid,))
    c.execute("DELETE FROM invoice_jobs WHERE invoice_id = ?", (invoice_id,))
    c.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
    conn.commit()
    conn.close()


def get_recipient_name(recipient_type, recipient_id):
    conn = get_connection()
    c = conn.cursor()
    if recipient_type == "Primary":
        c.execute("SELECT name FROM contractors WHERE id = ?", (recipient_id,))
    else:
        c.execute("SELECT name FROM clients WHERE id = ?", (recipient_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else "Unknown"


# ─── Sub Payments ───

def add_sub_payment(contractor_id, amount, payment_date, payment_type, period_from=None, period_to=None, notes="", user_id=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO sub_payments (contractor_id, amount, payment_date, payment_type, period_from, period_to, notes, user_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (contractor_id, amount, payment_date, payment_type, period_from, period_to, notes, user_id),
    )
    conn.commit()
    conn.close()


def get_sub_payments(start_date=None, end_date=None, contractor_id=None, user_id=None):
    conn = get_connection()
    c = conn.cursor()
    query = """
        SELECT sp.id, c.name, sp.amount, sp.payment_date, sp.payment_type, sp.period_from, sp.period_to, sp.notes
        FROM sub_payments sp
        JOIN contractors c ON sp.contractor_id = c.id
    """
    conditions = ["sp.user_id = ?"]
    params = [user_id]
    if start_date:
        conditions.append("sp.payment_date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("sp.payment_date <= ?")
        params.append(end_date)
    if contractor_id:
        conditions.append("sp.contractor_id = ?")
        params.append(contractor_id)
    query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY sp.payment_date DESC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows


def delete_sub_payment(payment_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM sub_payments WHERE id = ?", (payment_id,))
    conn.commit()
    conn.close()


def get_sub_payment_summary(start_date=None, end_date=None, user_id=None):
    conn = get_connection()
    c = conn.cursor()
    query = """
        SELECT c.name, SUM(sp.amount) as total, COUNT(sp.id) as count
        FROM sub_payments sp
        JOIN contractors c ON sp.contractor_id = c.id
    """
    conditions = ["sp.user_id = ?"]
    params = [user_id]
    if start_date:
        conditions.append("sp.payment_date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("sp.payment_date <= ?")
        params.append(end_date)
    query += " WHERE " + " AND ".join(conditions)
    query += " GROUP BY c.name ORDER BY total DESC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows
