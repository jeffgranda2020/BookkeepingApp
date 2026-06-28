import database as db

# Keyword rules: (keywords_in_description, category_type, category_name)
# Checked in order — first match wins
RULES = [
    # Income indicators
    (["deposit", "direct dep", "transfer from", "payment received", "zelle from",
      "venmo from", "cashapp from", "ach credit", "wire credit"], "Income", "Flooring Job Revenue"),

    # Materials / Supplies
    (["home depot", "lowes", "lowe's", "menards", "floor & decor", "floor and decor",
      "lumber liquidators", "ll flooring", "build.com", "fastenal", "grainger"],
     "COGS", "Materials"),

    # Gas & Fuel
    (["shell", "exxon", "mobil", "chevron", "sunoco", "bp ", "citgo", "wawa",
      "speedway", "cumberland", "gas", "fuel", "valero", "marathon", "costco gas"],
     "Expense", "Gas & Fuel"),

    # Tools & Equipment
    (["harbor freight", "milwaukee tool", "dewalt", "makita", "ridgid",
      "tool", "northern tool", "acme tools"], "Expense", "Tools & Equipment"),

    # Vehicle
    (["autozone", "advance auto", "o'reilly", "napa ", "jiffy lube", "oil change",
      "tire", "midas", "maaco", "car wash"], "Expense", "Car & Truck Expenses"),

    # Insurance
    (["insurance", "geico", "progressive", "state farm", "allstate", "liberty mutual",
      "nationwide", "hartford"], "Expense", "Insurance"),

    # Phone & Communication
    (["verizon", "t-mobile", "tmobile", "at&t", "att ", "sprint", "mint mobile",
      "visible", "cricket", "phone"], "Expense", "Phone & Communication"),

    # Meals
    (["mcdonald", "burger", "wendy", "subway", "dunkin", "starbucks", "chick-fil",
      "taco bell", "chipotle", "panera", "restaurant", "pizza", "diner", "grubhub",
      "doordash", "uber eats"], "Expense", "Meals (50% Deductible)"),

    # Office / Supplies
    (["office depot", "staples", "amazon", "walmart", "target", "best buy"],
     "Expense", "Supplies"),

    # Utilities
    (["electric", "eversource", "ui ", "united illuminating", "gas bill",
      "water bill", "sewer", "utility", "utilities"], "Expense", "Utilities"),

    # Rent
    (["rent", "lease payment", "storage"], "Expense", "Rent - Other Business Property"),

    # Bank fees
    (["bank fee", "service charge", "monthly fee", "overdraft", "nsf fee",
      "atm fee", "wire fee", "merchant fee"], "Expense", "Bank & Merchant Fees"),

    # Permits & Inspections
    (["permit", "inspection", "license", "registration", "town of", "city of",
      "state of ct", "dcp ", "hic "], "Expense", "Permits & Inspections"),

    # Dump / Disposal
    (["dump", "disposal", "waste", "transfer station", "hauling"],
     "Expense", "Dump Fees & Disposal"),

    # Subcontractor payments
    (["zelle to", "venmo to", "cashapp to", "ach debit"], "COGS", "Subcontractor Labor"),

    # Advertising
    (["facebook", "google ads", "yelp", "angi", "angieslist", "thumbtack",
      "advertising", "marketing", "promotion"], "Expense", "Advertising"),

    # Legal & Professional
    (["attorney", "lawyer", "accountant", "cpa ", "bookkeep", "legal",
      "tax prep"], "Expense", "Legal & Professional Services"),

    # Contract Labor
    (["contractor", "labor", "day labor"], "Expense", "Contract Labor"),
]


def guess_category(description, amount):
    desc_lower = description.lower()

    # Check keyword rules
    for keywords, cat_type, cat_name in RULES:
        for kw in keywords:
            if kw in desc_lower:
                return cat_type, cat_name

    # Fallback: positive amounts are likely income, negative are expenses
    if amount > 0:
        return "Income", "Flooring Job Revenue"
    elif amount < 0:
        return "Expense", "Other Expenses"

    return None, None


def get_category_id(cat_type, cat_name):
    categories = db.get_categories()
    for cid, ctype, cname in categories:
        if ctype == cat_type and cname == cat_name:
            return cid
    return None


def auto_categorize_transaction(description, amount):
    cat_type, cat_name = guess_category(description, amount)
    if cat_type and cat_name:
        return get_category_id(cat_type, cat_name)
    return None
