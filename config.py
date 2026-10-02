"""
Income & Expenses Manager CLI
Core configuration and constants.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure UTF-8 output encoding for Windows terminals
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).parent

# ─── Database Backend ──────────────────────────────────────────────────────────
DB_BACKEND = os.getenv("DB_BACKEND", "json").lower()

# ─── MySQL Configuration ───────────────────────────────────────────────────────
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "income_expenses_manager"),
}

# ─── JSON Configuration ────────────────────────────────────────────────────────
JSON_DATA_DIR = BASE_DIR / os.getenv("JSON_DATA_DIR", "data")
JSON_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ─── Sync Settings ─────────────────────────────────────────────────────────────
AUTO_SYNC = os.getenv("AUTO_SYNC", "true").lower() == "true"
SYNC_INTERVAL_MINUTES = int(os.getenv("SYNC_INTERVAL_MINUTES", 5))

# ─── App Settings ──────────────────────────────────────────────────────────────
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "USD")
DATE_FORMAT = os.getenv("DATE_FORMAT", "%Y-%m-%d")

# ─── UI Constants ──────────────────────────────────────────────────────────────
APP_NAME = "Income & Expenses Manager"
APP_VERSION = "1.0.0"
AUTHOR = "Sasindu Dilshara"
GITHUB = "github.com/sasindudilshara"

# Color theme (Rich markup)
THEME = {
    "primary":   "bold cyan",
    "secondary": "bold blue",
    "success":   "bold green",
    "warning":   "bold yellow",
    "error":     "bold red",
    "muted":     "dim white",
    "income":    "bold green",
    "expense":   "bold red",
    "header":    "bold white on blue",
    "title":     "bold magenta",
    "accent":    "bold cyan",
    "border":    "cyan",
}

# Supported export formats
EXPORT_FORMATS = ["csv", "json", "xlsx", "pdf", "txt"]

# Supported import formats
IMPORT_FORMATS = ["csv", "json", "xlsx"]

# Default income methods
DEFAULT_INCOME_METHODS = [
    "Salary", "Freelance", "Business", "Investment",
    "Rental", "Dividends", "Gift", "Bonus", "Other"
]

# Default expense methods
DEFAULT_EXPENSE_METHODS = [
    "Cash", "Credit Card", "Debit Card", "Bank Transfer",
    "Mobile Payment", "Cheque", "Cryptocurrency", "Other"
]

# Default expense categories
DEFAULT_EXPENSE_CATEGORIES = [
    "Food & Dining", "Transportation", "Housing", "Utilities",
    "Healthcare", "Entertainment", "Shopping", "Education",
    "Travel", "Insurance", "Savings", "Investment", "Other"
]

# Default income categories
DEFAULT_INCOME_CATEGORIES = [
    "Primary Income", "Secondary Income", "Passive Income",
    "Investment Returns", "Gifts & Awards", "Other"
]

CURRENCY_SYMBOLS = {
    "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥",
    "INR": "₹", "LKR": "Rs", "AUD": "A$", "CAD": "C$",
}
