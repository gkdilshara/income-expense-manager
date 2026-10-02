"""
database/mysql_backend.py - MySQL storage backend
"""

import threading
from typing import List, Optional, Dict, Any
from datetime import datetime

try:
    import mysql.connector
    from mysql.connector import pooling
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

from models import Account, Transaction, IncomeMethod, ExpenseMethod, Budget, AppSettings
from config import MYSQL_CONFIG


CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS accounts (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    description TEXT,
    color VARCHAR(50) DEFAULT 'cyan',
    balance DECIMAL(15,2) DEFAULT 0.00,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS income_methods (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    icon VARCHAR(10) DEFAULT '💰',
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS expense_methods (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    icon VARCHAR(10) DEFAULT '💳',
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id VARCHAR(36) PRIMARY KEY,
    account_id VARCHAR(36) NOT NULL,
    type ENUM('income','expense') NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    category VARCHAR(255),
    description TEXT,
    method_id VARCHAR(36),
    method_name VARCHAR(255),
    tags TEXT,
    date DATE NOT NULL,
    is_recurring BOOLEAN DEFAULT FALSE,
    recurrence VARCHAR(50),
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS budgets (
    id VARCHAR(36) PRIMARY KEY,
    account_id VARCHAR(36) NOT NULL,
    category VARCHAR(255) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    period VARCHAR(50) DEFAULT 'monthly',
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS settings (
    id INT PRIMARY KEY DEFAULT 1,
    db_backend VARCHAR(20) DEFAULT 'json',
    default_currency VARCHAR(10) DEFAULT 'USD',
    date_format VARCHAR(50) DEFAULT '%Y-%m-%d',
    auto_sync BOOLEAN DEFAULT TRUE,
    sync_interval INT DEFAULT 5,
    theme VARCHAR(50) DEFAULT 'default',
    show_animations BOOLEAN DEFAULT TRUE,
    default_account_id VARCHAR(36) DEFAULT '',
    mysql_host VARCHAR(255) DEFAULT 'localhost',
    mysql_port INT DEFAULT 3306,
    mysql_user VARCHAR(255) DEFAULT 'root',
    mysql_password VARCHAR(255) DEFAULT '',
    mysql_database VARCHAR(255) DEFAULT 'income_expenses_manager'
);
"""


class MySQLBackend:
    """MySQL storage backend with connection pooling."""

    def __init__(self, config: dict = None):
        if not MYSQL_AVAILABLE:
            raise RuntimeError("mysql-connector-python is not installed.")
        self._config = config or MYSQL_CONFIG
        self._lock = threading.RLock()
        self._pool = None
        self._connect()
        self._create_tables()
        self._initialize_defaults()

    def _connect(self):
        cfg = {**self._config}
        # Create DB if not exists
        db_name = cfg.pop("database", "income_expenses_manager")
        try:
            tmp = mysql.connector.connect(**cfg)
            cur = tmp.cursor()
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            tmp.commit()
            cur.close()
            tmp.close()
        except Exception:
            pass

        self._pool = pooling.MySQLConnectionPool(
            pool_name="ie_pool",
            pool_size=5,
            **self._config
        )

    def _get_conn(self):
        return self._pool.get_connection()

    def _create_tables(self):
        conn = self._get_conn()
        cur = conn.cursor()
        for stmt in CREATE_TABLES_SQL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                cur.execute(stmt)
        conn.commit()
        cur.close()
        conn.close()

    def _initialize_defaults(self):
        from config import DEFAULT_INCOME_METHODS, DEFAULT_EXPENSE_METHODS, DEFAULT_CURRENCY
        conn = self._get_conn()
        cur = conn.cursor(dictionary=True)
        try:
            # Settings row
            cur.execute("SELECT COUNT(*) as cnt FROM settings WHERE id=1")
            if cur.fetchone()["cnt"] == 0:
                cur.execute("INSERT INTO settings (id) VALUES (1)")
                conn.commit()

            # Default account
            cur.execute("SELECT COUNT(*) as cnt FROM accounts")
            if cur.fetchone()["cnt"] == 0:
                from models import Account
                acc = Account(name="Personal", currency=DEFAULT_CURRENCY)
                self._save_account_conn(cur, conn, acc)

            # Income methods
            cur.execute("SELECT COUNT(*) as cnt FROM income_methods")
            if cur.fetchone()["cnt"] == 0:
                from models import IncomeMethod
                for m in DEFAULT_INCOME_METHODS:
                    method = IncomeMethod(name=m)
                    self._save_income_method_conn(cur, conn, method)

            # Expense methods
            cur.execute("SELECT COUNT(*) as cnt FROM expense_methods")
            if cur.fetchone()["cnt"] == 0:
                from models import ExpenseMethod
                for m in DEFAULT_EXPENSE_METHODS:
                    method = ExpenseMethod(name=m)
                    self._save_expense_method_conn(cur, conn, method)
        finally:
            cur.close()
            conn.close()

    # ─── Internal save helpers ────────────────────────────────────────────────

    def _save_account_conn(self, cur, conn, account):
        cur.execute("""
            INSERT INTO accounts (id, name, currency, description, color, balance, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              name=%s, currency=%s, description=%s, color=%s, balance=%s, is_active=%s
        """, (account.id, account.name, account.currency, account.description,
              account.color, account.balance, account.is_active, account.created_at,
              account.name, account.currency, account.description,
              account.color, account.balance, account.is_active))
        conn.commit()

    def _save_income_method_conn(self, cur, conn, method):
        cur.execute("""
            INSERT INTO income_methods (id, name, description, icon, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE name=%s, description=%s, icon=%s, is_active=%s
        """, (method.id, method.name, method.description, method.icon,
              method.is_active, method.created_at,
              method.name, method.description, method.icon, method.is_active))
        conn.commit()

    def _save_expense_method_conn(self, cur, conn, method):
        cur.execute("""
            INSERT INTO expense_methods (id, name, description, icon, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE name=%s, description=%s, icon=%s, is_active=%s
        """, (method.id, method.name, method.description, method.icon,
              method.is_active, method.created_at,
              method.name, method.description, method.icon, method.is_active))
        conn.commit()

    # ─── Accounts ─────────────────────────────────────────────────────────────

    def get_accounts(self) -> List[Account]:
        conn = self._get_conn()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM accounts ORDER BY created_at")
            rows = cur.fetchall()
            return [Account.from_dict(self._convert_row(r)) for r in rows]
        finally:
            cur.close(); conn.close()

    def get_account(self, account_id: str) -> Optional[Account]:
        conn = self._get_conn()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM accounts WHERE id=%s", (account_id,))
            row = cur.fetchone()
            return Account.from_dict(self._convert_row(row)) if row else None
        finally:
            cur.close(); conn.close()

    def save_account(self, account: Account):
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            self._save_account_conn(cur, conn, account)
        finally:
            cur.close(); conn.close()

    def delete_account(self, account_id: str) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM accounts WHERE id=%s", (account_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close(); conn.close()

    # ─── Transactions ─────────────────────────────────────────────────────────

    def get_transactions(self, account_id=None, type_filter=None,
                         date_from=None, date_to=None,
                         category=None, search=None) -> List[Transaction]:
        conn = self._get_conn()
        cur = conn.cursor(dictionary=True)
        try:
            sql = "SELECT * FROM transactions WHERE 1=1"
            params = []
            if account_id:
                sql += " AND account_id=%s"; params.append(account_id)
            if type_filter:
                sql += " AND type=%s"; params.append(type_filter)
            if date_from:
                sql += " AND date>=%s"; params.append(date_from)
            if date_to:
                sql += " AND date<=%s"; params.append(date_to)
            if category:
                sql += " AND category=%s"; params.append(category)
            if search:
                sql += " AND (description LIKE %s OR category LIKE %s OR notes LIKE %s OR tags LIKE %s)"
                s = f"%{search}%"
                params.extend([s, s, s, s])
            sql += " ORDER BY date DESC, created_at DESC"
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [Transaction.from_dict(self._convert_row(r)) for r in rows]
        finally:
            cur.close(); conn.close()

    def get_transaction(self, txn_id: str) -> Optional[Transaction]:
        conn = self._get_conn()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM transactions WHERE id=%s", (txn_id,))
            row = cur.fetchone()
            return Transaction.from_dict(self._convert_row(row)) if row else None
        finally:
            cur.close(); conn.close()

    def save_transaction(self, txn: Transaction):
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            txn.updated_at = datetime.now().isoformat()
            cur.execute("""
                INSERT INTO transactions
                  (id, account_id, type, amount, category, description,
                   method_id, method_name, tags, date, is_recurring, recurrence,
                   notes, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                  amount=%s, category=%s, description=%s, method_id=%s,
                  method_name=%s, tags=%s, date=%s, is_recurring=%s,
                  recurrence=%s, notes=%s, updated_at=%s
            """, (txn.id, txn.account_id, txn.type, txn.amount, txn.category,
                  txn.description, txn.method_id, txn.method_name, txn.tags,
                  txn.date, txn.is_recurring, txn.recurrence, txn.notes,
                  txn.created_at, txn.updated_at,
                  txn.amount, txn.category, txn.description, txn.method_id,
                  txn.method_name, txn.tags, txn.date, txn.is_recurring,
                  txn.recurrence, txn.notes, txn.updated_at))
            conn.commit()
        finally:
            cur.close(); conn.close()

    def delete_transaction(self, txn_id: str) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM transactions WHERE id=%s", (txn_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close(); conn.close()

    def get_all_transactions_raw(self) -> List[Dict]:
        conn = self._get_conn()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM transactions ORDER BY date DESC")
            return [self._convert_row(r) for r in cur.fetchall()]
        finally:
            cur.close(); conn.close()

    def bulk_import_transactions(self, txns: List[Transaction]):
        for t in txns:
            self.save_transaction(t)

    # ─── Income Methods ───────────────────────────────────────────────────────

    def get_income_methods(self) -> List[IncomeMethod]:
        conn = self._get_conn()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM income_methods ORDER BY name")
            return [IncomeMethod.from_dict(self._convert_row(r)) for r in cur.fetchall()]
        finally:
            cur.close(); conn.close()

    def save_income_method(self, method: IncomeMethod):
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            self._save_income_method_conn(cur, conn, method)
        finally:
            cur.close(); conn.close()

    def delete_income_method(self, method_id: str) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM income_methods WHERE id=%s", (method_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close(); conn.close()

    # ─── Expense Methods ──────────────────────────────────────────────────────

    def get_expense_methods(self) -> List[ExpenseMethod]:
        conn = self._get_conn()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM expense_methods ORDER BY name")
            return [ExpenseMethod.from_dict(self._convert_row(r)) for r in cur.fetchall()]
        finally:
            cur.close(); conn.close()

    def save_expense_method(self, method: ExpenseMethod):
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            self._save_expense_method_conn(cur, conn, method)
        finally:
            cur.close(); conn.close()

    def delete_expense_method(self, method_id: str) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM expense_methods WHERE id=%s", (method_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close(); conn.close()

    # ─── Budgets ──────────────────────────────────────────────────────────────

    def get_budgets(self, account_id=None) -> List[Budget]:
        conn = self._get_conn()
        cur = conn.cursor(dictionary=True)
        try:
            sql = "SELECT * FROM budgets WHERE 1=1"
            params = []
            if account_id:
                sql += " AND account_id=%s"; params.append(account_id)
            cur.execute(sql, params)
            return [Budget.from_dict(self._convert_row(r)) for r in cur.fetchall()]
        finally:
            cur.close(); conn.close()

    def save_budget(self, budget: Budget):
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO budgets (id, account_id, category, amount, period, is_active, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                  category=%s, amount=%s, period=%s, is_active=%s
            """, (budget.id, budget.account_id, budget.category, budget.amount,
                  budget.period, budget.is_active, budget.created_at,
                  budget.category, budget.amount, budget.period, budget.is_active))
            conn.commit()
        finally:
            cur.close(); conn.close()

    def delete_budget(self, budget_id: str) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM budgets WHERE id=%s", (budget_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close(); conn.close()

    # ─── Settings ─────────────────────────────────────────────────────────────

    def get_settings(self) -> AppSettings:
        conn = self._get_conn()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM settings WHERE id=1")
            row = cur.fetchone()
            return AppSettings.from_dict(self._convert_row(row)) if row else AppSettings()
        finally:
            cur.close(); conn.close()

    def save_settings(self, settings: AppSettings):
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            d = settings.to_dict()
            cols = ", ".join(f"{k}=%s" for k in d)
            cur.execute(f"UPDATE settings SET {cols} WHERE id=1", list(d.values()))
            conn.commit()
        finally:
            cur.close(); conn.close()

    def wipe_transactions(self, account_id: str = None, txn_type: str = None) -> int:
        """Delete all transactions (or filtered by account / type)."""
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            sql = "DELETE FROM transactions WHERE 1=1"
            params = []
            if account_id:
                sql += " AND account_id=%s"
                params.append(account_id)
            if txn_type:
                sql += " AND type=%s"
                params.append(txn_type)
            cur.execute(sql, tuple(params))
            conn.commit()
            return cur.rowcount
        finally:
            cur.close(); conn.close()

    def factory_reset(self):
        """Reset MySQL database back to default state."""
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM transactions")
            cur.execute("DELETE FROM budgets")
            cur.execute("DELETE FROM accounts")
            cur.execute("DELETE FROM income_methods")
            cur.execute("DELETE FROM expense_methods")
            conn.commit()
            self._initialize_defaults()
        finally:
            cur.close(); conn.close()

    # ─── Export ───────────────────────────────────────────────────────────────

    def export_all(self) -> Dict:
        return {
            "accounts":        [a.to_dict() for a in self.get_accounts()],
            "transactions":    self.get_all_transactions_raw(),
            "income_methods":  [m.to_dict() for m in self.get_income_methods()],
            "expense_methods": [m.to_dict() for m in self.get_expense_methods()],
            "budgets":         [b.to_dict() for b in self.get_budgets()],
            "settings":        self.get_settings().to_dict(),
            "exported_at":     datetime.now().isoformat(),
        }

    def _convert_row(self, row: dict) -> dict:
        """Convert MySQL types to Python-friendly types."""
        if not row:
            return {}
        import decimal
        result = {}
        for k, v in row.items():
            if hasattr(v, 'isoformat'):
                result[k] = v.isoformat()
            elif isinstance(v, decimal.Decimal):
                result[k] = float(v)
            elif isinstance(v, (bytes, bytearray)):
                result[k] = v.decode()
            else:
                result[k] = v
        return result
