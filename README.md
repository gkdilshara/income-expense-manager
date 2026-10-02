# 💰 Income & Expenses Manager CLI

```text
 ___                            ___  ___                             
|_ _|_ _  __ ___ _ __  ___     | __|/ __|_ __  ___ _ _  ___ ___ ___ 
 | || ' \/ _/ _ \ '  \/ -_)    | _|| (__| '_ \/ -_) ' \(_-</ -_|_-<
|___|_||_\__\___/_|_|_\___|    |___|\___| .__/\___|_||_/__/\___/__/
                                         |_|    M A N A G E R  C L I
```

[![Python Version](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Database](https://img.shields.io/badge/Storage-JSON%20%7C%20MySQL-orange.svg)]()
[![UI Framework](https://img.shields.io/badge/UI-Rich%20%2B%20Questionary-cyan.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()

> An advanced, terminal-based financial management system built in Python. Features butter-smooth arrow navigation, ASCII & Unicode charts, multi-account tracking, smart insights, customizable date/time stamps, and seamless JSON/MySQL synchronization.

**Author**: Sasindu Dilshara  
**Version**: 1.0.0 (Initial Release)

---

## ✨ Features

- ⌨️ **Arrow-Key Navigation**: Interactive, flicker-free terminal interface powered by `Questionary` & `Rich` with `ESC` to go back.
- 🕒 **Custom Date & Time**: Apply recommended current timestamps or enter custom historical dates & times.
- 📊 **Visual CLI Analytics**:
  - Summary stat cards (*Income, Expenses, Net Balance, Savings Rate*)
  - Horizontal category bar charts
  - Circular ASCII pie charts
  - Donut segment breakdown bars
  - 30-day activity sparklines
  - Budget vs. Actual progress bars
- 🗄️ **Dual-Engine Storage**:
  - **JSON Backend**: Zero-setup local storage in `data/`.
  - **MySQL Backend**: High-performance database with connection pooling.
  - **Live Switcher & Auto-Sync**: Switch engines dynamically or synchronize data bidirectionally.
- 👤 **Multi-Account Management**: Isolated accounts (*Personal, Business, Savings*) with distinct currencies and color badges.
- 💳 **Reusable Methods**: Customizable income sources and payment methods with emoji icons.
- 🎯 **Budget Goals**: Monthly spending limits per category with visual alerts for threshold warnings.
- 🔮 **Smart Insights & Forecasting**:
  - 6-month rolling next-month financial projections
  - Spending streak detection
  - Anomaly detection for high-spend categories
- 📤 **Multi-Format Import & Export**:
  - Export: `CSV`, `JSON`, `XLSX (Excel with styling)`, `PDF Reports`, `TXT Summary`
  - Import: `CSV`, `JSON`, `XLSX`
  - Full system snapshot backup and restore

---

## 🚀 Quick Start

### 1. Setup & Installation (One-Click)

On Windows:
```cmd
setup.bat
```

Or manually:
```bash
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
```

### 2. Run Application

```cmd
run.bat
```

Or via terminal:
```bash
.\venv\Scripts\python main.py
```

---

## ⌨️ Controls

| Key | Action |
|---|---|
| `↑` / `↓` | Navigate menu items |
| `Enter` | Select / Confirm |
| `ESC` | Go Back to previous menu / Cancel |

---

## ⚙️ Configuration (`.env`)

```env
# Storage backend: "json" or "mysql"
DB_BACKEND=json

# MySQL Configuration (if using MySQL backend)
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=yourpassword
MYSQL_DATABASE=income_expenses_manager

# Auto-sync settings
AUTO_SYNC=true
SYNC_INTERVAL_MINUTES=5

# Currency & Formats
DEFAULT_CURRENCY=USD
DATE_FORMAT=%Y-%m-%d
```

---

## 📁 Project Structure

```text
Income & Expenses Manager CLI/
├── main.py                   # Main CLI application & controllers
├── ui_components.py          # Questionary & Rich UI engine with ESC navigation
├── charts.py                 # Visual ASCII & Unicode charts engine
├── config.py                 # App configuration & UTF-8 stream setup
├── models.py                 # Dataclass entities (Account, Transaction, Budget, etc.)
├── analytics.py              # Stats, forecasting, and insights engine
├── io_manager.py             # Multi-format Import/Export manager
├── database/
│   ├── __init__.py           # Backend factory & sync engine
│   ├── json_backend.py       # JSON file storage
│   └── mysql_backend.py      # MySQL storage with pooling
├── data/                     # Local JSON database files
├── exports/                  # Exported reports (CSV, JSON, XLSX, PDF, TXT)
├── backups/                  # Full database backup snapshots
├── requirements.txt          # Python dependencies
├── setup.bat                 # One-click setup script
└── run.bat                   # Quick launch script
```

---

## 📄 License

Distributed under the MIT License. Created by **Sasindu Dilshara**.
