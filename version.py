APP_NAME = "5StarBookKeeping"
APP_VERSION = "1.0.4"
APP_AUTHOR = "Jeff Granda-Arias"

# GitHub repo for update checks (owner/repo)
GITHUB_REPO = "jeffgranda2020/BookkeepingApp"

CHANGELOG = {
    "1.0.4": [
        "Added user login system — each account has its own isolated data",
        "Strong password requirements (10+ chars, uppercase, lowercase, number, special character)",
        "Blocks common passwords, keyboard patterns, and username-based passwords",
        "Security questions during signup for password recovery",
        "Forgot Password flow — answer security questions to reset password",
        "New password cannot match old password on reset",
        "Legacy data migration offered only to the first account created",
    ],
    "1.0.3": [
        "Company Info Save button now positioned directly under the form fields",
        "All table columns centered and stretch to fill fullscreen width",
        "Fixed updater to properly wait for app to close before replacing .exe",
        "Bundled VC++ runtime DLLs for compatibility on machines without Visual C++ installed",
    ],
    "1.0.2": [
        "App now starts fullscreen (maximized)",
        "All dialog windows open centered on screen",
        "Fixed Add Transaction and Add Category dialog alignment",
        "Added Select All / Deselect All buttons for transaction multi-select",
        "Fixed Add Individual Client dialog — Save button no longer cut off",
        "Added Edit Service functionality in Invoicing > Services",
        "Contractors require all fields before saving",
    ],
    "1.0.1": [
        "Fixed data loss on restart — database now saves next to the .exe instead of temp folder",
    ],
    "1.0.0": [
        "Initial release",
        "Company Information management with logo upload",
        "Accounting tab: import statements (CSV/Excel/PDF/OFX), auto-categorize, P&L, Balance Sheet",
        "Contractors tab: Primary contractors and Subcontractors with code IDs",
        "Invoicing: Primary weekly bills and Client invoices with preview and PDF export",
        "Sub Payments: track payments to subs, generate full and individual statements",
        "Editable import review before committing transactions",
        "Date range selection for P&L with prior period comparison",
        "Net Profit Margin on P&L reports",
        "Professional PDF exports with company branding",
    ],
}
