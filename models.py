"""
models.py - Data models for Income & Expenses Manager
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import uuid


def new_id() -> str:
    return str(uuid.uuid4())


def now_str() -> str:
    return datetime.now().isoformat()


@dataclass
class Account:
    name: str
    currency: str = "USD"
    description: str = ""
    color: str = "cyan"
    id: str = field(default_factory=new_id)
    created_at: str = field(default_factory=now_str)
    balance: float = 0.0
    is_active: bool = True

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class IncomeMethod:
    name: str
    description: str = ""
    icon: str = "💰"
    id: str = field(default_factory=new_id)
    created_at: str = field(default_factory=now_str)
    is_active: bool = True

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ExpenseMethod:
    name: str
    description: str = ""
    icon: str = "💳"
    id: str = field(default_factory=new_id)
    created_at: str = field(default_factory=now_str)
    is_active: bool = True

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Transaction:
    account_id: str
    type: str             # "income" or "expense"
    amount: float
    category: str
    description: str = ""
    method_id: str = ""   # IncomeMethod or ExpenseMethod id
    method_name: str = "" # denormalized for display
    tags: str = ""        # comma-separated
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    id: str = field(default_factory=new_id)
    created_at: str = field(default_factory=now_str)
    updated_at: str = field(default_factory=now_str)
    is_recurring: bool = False
    recurrence: str = ""  # daily, weekly, monthly, yearly
    notes: str = ""

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**known)


@dataclass
class Budget:
    account_id: str
    category: str
    amount: float
    period: str = "monthly"  # monthly, weekly, yearly
    id: str = field(default_factory=new_id)
    created_at: str = field(default_factory=now_str)
    is_active: bool = True

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class AppSettings:
    db_backend: str = "json"
    default_currency: str = "USD"
    date_format: str = "%Y-%m-%d"
    auto_sync: bool = True
    sync_interval: int = 5
    theme: str = "default"
    show_animations: bool = True
    default_account_id: str = ""
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "income_expenses_manager"

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
