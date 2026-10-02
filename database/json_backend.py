"""
database/json_backend.py - JSON file-based storage backend
"""

import json
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from models import Account, Transaction, IncomeMethod, ExpenseMethod, Budget, AppSettings
from config import JSON_DATA_DIR


class JSONBackend:
    """Thread-safe JSON file storage backend."""

    def __init__(self):
        self._lock = threading.RLock()
        self._data_dir = JSON_DATA_DIR
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._files = {
            "accounts":        self._data_dir / "accounts.json",
            "transactions":    self._data_dir / "transactions.json",
            "income_methods":  self._data_dir / "income_methods.json",
            "expense_methods": self._data_dir / "expense_methods.json",
            "budgets":         self._data_dir / "budgets.json",
            "settings":        self._data_dir / "settings.json",
        }
        self._initialize_defaults()

    # ─── Internal helpers ─────────────────────────────────────────────────────

    def _read(self, key: str) -> Any:
        path = self._files[key]
        if not path.exists():
            return [] if key != "settings" else {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, key: str, data: Any):
        path = self._files[key]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def _initialize_defaults(self):
        from config import (
            DEFAULT_INCOME_METHODS, DEFAULT_EXPENSE_METHODS,
            DEFAULT_CURRENCY, AUTHOR
        )
        with self._lock:
            # Settings
            if not self._files["settings"].exists():
                settings = AppSettings()
                self._write("settings", settings.to_dict())

            # Default account
            if not self._files["accounts"].exists() or not self._read("accounts"):
                acc = Account(name="Personal", currency=DEFAULT_CURRENCY,
                              description="Default personal account", color="cyan")
                self._write("accounts", [acc.to_dict()])

            # Income methods
            if not self._files["income_methods"].exists() or not self._read("income_methods"):
                methods = [IncomeMethod(name=m).to_dict() for m in DEFAULT_INCOME_METHODS]
                self._write("income_methods", methods)

            # Expense methods
            if not self._files["expense_methods"].exists() or not self._read("expense_methods"):
                methods = [ExpenseMethod(name=m).to_dict() for m in DEFAULT_EXPENSE_METHODS]
                self._write("expense_methods", methods)

            # Empty transactions / budgets
            for key in ["transactions", "budgets"]:
                if not self._files[key].exists():
                    self._write(key, [])

    # ─── Accounts ─────────────────────────────────────────────────────────────

    def get_accounts(self) -> List[Account]:
        with self._lock:
            return [Account.from_dict(d) for d in self._read("accounts")]

    def get_account(self, account_id: str) -> Optional[Account]:
        for a in self.get_accounts():
            if a.id == account_id:
                return a
        return None

    def save_account(self, account: Account):
        with self._lock:
            accounts = self._read("accounts")
            for i, a in enumerate(accounts):
                if a["id"] == account.id:
                    accounts[i] = account.to_dict()
                    self._write("accounts", accounts)
                    return
            accounts.append(account.to_dict())
            self._write("accounts", accounts)

    def delete_account(self, account_id: str) -> bool:
        with self._lock:
            accounts = self._read("accounts")
            new = [a for a in accounts if a["id"] != account_id]
            if len(new) == len(accounts):
                return False
            self._write("accounts", new)
            return True

    # ─── Transactions ─────────────────────────────────────────────────────────

    def get_transactions(self, account_id: str = None,
                         type_filter: str = None,
                         date_from: str = None,
                         date_to: str = None,
                         category: str = None,
                         search: str = None) -> List[Transaction]:
        with self._lock:
            data = self._read("transactions")
            txns = [Transaction.from_dict(d) for d in data]

        if account_id:
            txns = [t for t in txns if t.account_id == account_id]
        if type_filter:
            txns = [t for t in txns if t.type == type_filter]
        if date_from:
            txns = [t for t in txns if t.date >= date_from]
        if date_to:
            txns = [t for t in txns if t.date <= date_to]
        if category:
            txns = [t for t in txns if t.category.lower() == category.lower()]
        if search:
            s = search.lower()
            txns = [t for t in txns if
                    s in t.description.lower() or
                    s in t.category.lower() or
                    s in t.notes.lower() or
                    s in t.tags.lower()]
        return sorted(txns, key=lambda t: (t.date, t.created_at), reverse=True)

    def get_transaction(self, txn_id: str) -> Optional[Transaction]:
        with self._lock:
            for d in self._read("transactions"):
                if d["id"] == txn_id:
                    return Transaction.from_dict(d)
        return None

    def save_transaction(self, txn: Transaction):
        with self._lock:
            txns = self._read("transactions")
            txn.updated_at = datetime.now().isoformat()
            for i, t in enumerate(txns):
                if t["id"] == txn.id:
                    txns[i] = txn.to_dict()
                    self._write("transactions", txns)
                    return
            txns.append(txn.to_dict())
            self._write("transactions", txns)

    def delete_transaction(self, txn_id: str) -> bool:
        with self._lock:
            txns = self._read("transactions")
            new = [t for t in txns if t["id"] != txn_id]
            if len(new) == len(txns):
                return False
            self._write("transactions", new)
            return True

    def get_all_transactions_raw(self) -> List[Dict]:
        with self._lock:
            return self._read("transactions")

    def bulk_import_transactions(self, txns: List[Transaction]):
        with self._lock:
            existing = self._read("transactions")
            ids = {t["id"] for t in existing}
            for t in txns:
                if t.id not in ids:
                    existing.append(t.to_dict())
            self._write("transactions", existing)

    # ─── Income Methods ───────────────────────────────────────────────────────

    def get_income_methods(self) -> List[IncomeMethod]:
        with self._lock:
            return [IncomeMethod.from_dict(d) for d in self._read("income_methods")]

    def save_income_method(self, method: IncomeMethod):
        with self._lock:
            methods = self._read("income_methods")
            for i, m in enumerate(methods):
                if m["id"] == method.id:
                    methods[i] = method.to_dict()
                    self._write("income_methods", methods)
                    return
            methods.append(method.to_dict())
            self._write("income_methods", methods)

    def delete_income_method(self, method_id: str) -> bool:
        with self._lock:
            methods = self._read("income_methods")
            new = [m for m in methods if m["id"] != method_id]
            if len(new) == len(methods):
                return False
            self._write("income_methods", new)
            return True

    # ─── Expense Methods ──────────────────────────────────────────────────────

    def get_expense_methods(self) -> List[ExpenseMethod]:
        with self._lock:
            return [ExpenseMethod.from_dict(d) for d in self._read("expense_methods")]

    def save_expense_method(self, method: ExpenseMethod):
        with self._lock:
            methods = self._read("expense_methods")
            for i, m in enumerate(methods):
                if m["id"] == method.id:
                    methods[i] = method.to_dict()
                    self._write("expense_methods", methods)
                    return
            methods.append(method.to_dict())
            self._write("expense_methods", methods)

    def delete_expense_method(self, method_id: str) -> bool:
        with self._lock:
            methods = self._read("expense_methods")
            new = [m for m in methods if m["id"] != method_id]
            if len(new) == len(methods):
                return False
            self._write("expense_methods", new)
            return True

    # ─── Budgets ──────────────────────────────────────────────────────────────

    def get_budgets(self, account_id: str = None) -> List[Budget]:
        with self._lock:
            budgets = [Budget.from_dict(d) for d in self._read("budgets")]
        if account_id:
            budgets = [b for b in budgets if b.account_id == account_id]
        return budgets

    def save_budget(self, budget: Budget):
        with self._lock:
            budgets = self._read("budgets")
            for i, b in enumerate(budgets):
                if b["id"] == budget.id:
                    budgets[i] = budget.to_dict()
                    self._write("budgets", budgets)
                    return
            budgets.append(budget.to_dict())
            self._write("budgets", budgets)

    def delete_budget(self, budget_id: str) -> bool:
        with self._lock:
            budgets = self._read("budgets")
            new = [b for b in budgets if b["id"] != budget_id]
            if len(new) == len(budgets):
                return False
            self._write("budgets", new)
            return True

    # ─── Settings ─────────────────────────────────────────────────────────────

    def get_settings(self) -> AppSettings:
        with self._lock:
            d = self._read("settings")
            return AppSettings.from_dict(d) if d else AppSettings()

    def save_settings(self, settings: AppSettings):
        with self._lock:
            self._write("settings", settings.to_dict())

    def wipe_transactions(self, account_id: str = None, txn_type: str = None) -> int:
        """Delete all transactions (or filtered by account / type)."""
        with self._lock:
            txns = self._read("transactions")
            new_txns = []
            removed = 0
            for t in txns:
                matches_acc = (account_id is None) or (t.get("account_id") == account_id)
                matches_type = (txn_type is None) or (t.get("type") == txn_type)
                if matches_acc and matches_type:
                    removed += 1
                else:
                    new_txns.append(t)
            self._write("transactions", new_txns)
            return removed

    def factory_reset(self):
        """Reset all data files back to fresh default state."""
        with self._lock:
            for key in ["accounts", "transactions", "income_methods", "expense_methods", "budgets", "settings"]:
                path = self._files[key]
                if path.exists():
                    try:
                        path.unlink()
                    except Exception:
                        pass
            self._initialize_defaults()

    # ─── Sync / Export ────────────────────────────────────────────────────────

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
