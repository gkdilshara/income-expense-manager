"""
database/__init__.py - Database backend factory with sync support
"""

import os
import sys
import threading
import time
from typing import Union

from config import DB_BACKEND, AUTO_SYNC, SYNC_INTERVAL_MINUTES


_json_backend = None
_mysql_backend = None
_active_backend = None
_sync_thread = None
_sync_running = False


def get_backend(force: str = None):
    """Get the currently active backend instance."""
    global _json_backend, _mysql_backend, _active_backend

    backend_type = force or DB_BACKEND

    if backend_type == "mysql":
        if _mysql_backend is None:
            try:
                from database.mysql_backend import MySQLBackend
                _mysql_backend = MySQLBackend()
            except Exception as e:
                print(f"[WARNING] MySQL unavailable: {e}. Falling back to JSON.")
                return get_backend("json")
        _active_backend = _mysql_backend
    else:
        if _json_backend is None:
            from database.json_backend import JSONBackend
            _json_backend = JSONBackend()
        _active_backend = _json_backend

    return _active_backend


def get_json_backend():
    global _json_backend
    if _json_backend is None:
        from database.json_backend import JSONBackend
        _json_backend = JSONBackend()
    return _json_backend


def get_mysql_backend():
    global _mysql_backend
    if _mysql_backend is None:
        try:
            from database.mysql_backend import MySQLBackend
            _mysql_backend = MySQLBackend()
        except Exception as e:
            raise RuntimeError(f"Cannot connect to MySQL: {e}")
    return _mysql_backend


def switch_backend(new_backend: str):
    """Switch between json and mysql backends."""
    global _active_backend
    _active_backend = get_backend(new_backend)

    # Update .env
    _update_env("DB_BACKEND", new_backend)
    return _active_backend


def _update_env(key: str, value: str):
    """Update a key in the .env file."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith(f"{key}="):
                    lines.append(f"{key}={value}\n")
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f"{key}={value}\n")
    with open(env_path, "w") as f:
        f.writelines(lines)


def sync_json_to_mysql():
    """Sync all data from JSON to MySQL."""
    try:
        json_db = get_json_backend()
        mysql_db = get_mysql_backend()
        data = json_db.export_all()

        for acc_data in data["accounts"]:
            from models import Account
            mysql_db.save_account(Account.from_dict(acc_data))
        for m_data in data["income_methods"]:
            from models import IncomeMethod
            mysql_db.save_income_method(IncomeMethod.from_dict(m_data))
        for m_data in data["expense_methods"]:
            from models import ExpenseMethod
            mysql_db.save_expense_method(ExpenseMethod.from_dict(m_data))
        for t_data in data["transactions"]:
            from models import Transaction
            mysql_db.save_transaction(Transaction.from_dict(t_data))
        for b_data in data["budgets"]:
            from models import Budget
            mysql_db.save_budget(Budget.from_dict(b_data))
        return True, "JSON → MySQL sync complete."
    except Exception as e:
        return False, f"Sync failed: {e}"


def sync_mysql_to_json():
    """Sync all data from MySQL to JSON."""
    try:
        json_db = get_json_backend()
        mysql_db = get_mysql_backend()
        data = mysql_db.export_all()

        for acc_data in data["accounts"]:
            from models import Account
            json_db.save_account(Account.from_dict(acc_data))
        for m_data in data["income_methods"]:
            from models import IncomeMethod
            json_db.save_income_method(IncomeMethod.from_dict(m_data))
        for m_data in data["expense_methods"]:
            from models import ExpenseMethod
            json_db.save_expense_method(ExpenseMethod.from_dict(m_data))
        for t_data in data["transactions"]:
            from models import Transaction
            json_db.save_transaction(Transaction.from_dict(t_data))
        for b_data in data["budgets"]:
            from models import Budget
            json_db.save_budget(Budget.from_dict(b_data))
        return True, "MySQL → JSON sync complete."
    except Exception as e:
        return False, f"Sync failed: {e}"


def start_auto_sync():
    """Start background auto-sync thread."""
    global _sync_thread, _sync_running
    if not AUTO_SYNC:
        return
    _sync_running = True

    def _sync_loop():
        while _sync_running:
            time.sleep(SYNC_INTERVAL_MINUTES * 60)
            if _sync_running:
                try:
                    sync_json_to_mysql()
                except Exception:
                    pass

    _sync_thread = threading.Thread(target=_sync_loop, daemon=True)
    _sync_thread.start()


def stop_auto_sync():
    global _sync_running
    _sync_running = False
