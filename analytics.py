"""
analytics.py - Analytics engine for Income & Expenses Manager
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime, date, timedelta
from collections import defaultdict
import math


def _to_date(s: str) -> date:
    try:
        return datetime.fromisoformat(s).date() if 'T' in s else datetime.strptime(s[:10], "%Y-%m-%d").date()
    except Exception:
        return date.today()


class Analytics:
    """Compute all analytics from a list of transactions."""

    def __init__(self, transactions):
        self.txns = transactions

    # ─── Basic Stats ─────────────────────────────────────────────────────────

    def total_income(self) -> float:
        return sum(t.amount for t in self.txns if t.type == "income")

    def total_expenses(self) -> float:
        return sum(t.amount for t in self.txns if t.type == "expense")

    def net_balance(self) -> float:
        return self.total_income() - self.total_expenses()

    def savings_rate(self) -> float:
        income = self.total_income()
        if income == 0:
            return 0.0
        return (self.net_balance() / income) * 100

    def transaction_count(self) -> Dict:
        return {
            "income": sum(1 for t in self.txns if t.type == "income"),
            "expense": sum(1 for t in self.txns if t.type == "expense"),
            "total": len(self.txns),
        }

    def average_transaction(self) -> Dict:
        income_txns = [t.amount for t in self.txns if t.type == "income"]
        expense_txns = [t.amount for t in self.txns if t.type == "expense"]
        return {
            "income": sum(income_txns) / len(income_txns) if income_txns else 0,
            "expense": sum(expense_txns) / len(expense_txns) if expense_txns else 0,
        }

    # ─── Breakdown by Category ────────────────────────────────────────────────

    def by_category(self, txn_type: str = None) -> Dict[str, float]:
        result = defaultdict(float)
        for t in self.txns:
            if txn_type and t.type != txn_type:
                continue
            result[t.category or "Uncategorized"] += t.amount
        return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))

    def by_method(self, txn_type: str = None) -> Dict[str, float]:
        result = defaultdict(float)
        for t in self.txns:
            if txn_type and t.type != txn_type:
                continue
            result[t.method_name or "Unknown"] += t.amount
        return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))

    # ─── Time Series ─────────────────────────────────────────────────────────

    def by_month(self) -> Dict[str, Dict[str, float]]:
        """Returns {month_str: {income, expense, net}}"""
        result = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "net": 0.0})
        for t in self.txns:
            month = t.date[:7]  # "YYYY-MM"
            result[month][t.type] += t.amount
            result[month]["net"] = result[month]["income"] - result[month]["expense"]
        return dict(sorted(result.items()))

    def by_week(self) -> Dict[str, Dict[str, float]]:
        result = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "net": 0.0})
        for t in self.txns:
            d = _to_date(t.date)
            week = f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"
            result[week][t.type] += t.amount
            result[week]["net"] = result[week]["income"] - result[week]["expense"]
        return dict(sorted(result.items()))

    def by_day(self, days: int = 30) -> Dict[str, Dict[str, float]]:
        cutoff = date.today() - timedelta(days=days)
        result = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "net": 0.0})
        for t in self.txns:
            d = _to_date(t.date)
            if d >= cutoff:
                day = str(d)
                result[day][t.type] += t.amount
                result[day]["net"] = result[day]["income"] - result[day]["expense"]
        return dict(sorted(result.items()))

    # ─── Trends & Forecasting ────────────────────────────────────────────────

    def monthly_trends(self) -> Dict:
        by_m = self.by_month()
        months = list(by_m.keys())
        if len(months) < 2:
            return {}

        incomes  = [by_m[m]["income"]  for m in months]
        expenses = [by_m[m]["expense"] for m in months]
        nets     = [by_m[m]["net"]     for m in months]

        def growth(series):
            if len(series) < 2 or series[0] == 0:
                return 0.0
            return ((series[-1] - series[0]) / abs(series[0])) * 100

        return {
            "months":           months,
            "incomes":          incomes,
            "expenses":         expenses,
            "nets":             nets,
            "income_growth":    growth(incomes),
            "expense_growth":   growth(expenses),
            "avg_income":       sum(incomes) / len(incomes),
            "avg_expense":      sum(expenses) / len(expenses),
        }

    def forecast_next_month(self) -> Dict:
        by_m = self.by_month()
        if len(by_m) < 2:
            return {}
        vals = list(by_m.values())
        n = min(len(vals), 6)
        recent = vals[-n:]
        avg_income  = sum(v["income"]  for v in recent) / n
        avg_expense = sum(v["expense"] for v in recent) / n
        next_m = (date.today().replace(day=1) + timedelta(days=32)).replace(day=1)
        return {
            "month":            next_m.strftime("%Y-%m"),
            "forecast_income":  avg_income,
            "forecast_expense": avg_expense,
            "forecast_net":     avg_income - avg_expense,
        }

    # ─── Top Transactions ────────────────────────────────────────────────────

    def top_transactions(self, txn_type: str, limit: int = 5) -> List:
        txns = [t for t in self.txns if t.type == txn_type]
        return sorted(txns, key=lambda t: t.amount, reverse=True)[:limit]

    # ─── Budget Analysis ─────────────────────────────────────────────────────

    def budget_analysis(self, budgets, period_start: str = None, period_end: str = None) -> List[Dict]:
        if not period_start:
            today = date.today()
            period_start = today.replace(day=1).isoformat()
        if not period_end:
            period_end = date.today().isoformat()

        expense_by_cat = defaultdict(float)
        for t in self.txns:
            t_date = t.date[:10] if t.date else ""
            if t.type == "expense" and period_start <= t_date <= period_end:
                expense_by_cat[t.category] += t.amount

        result = []
        for b in budgets:
            if not b.is_active:
                continue
            spent = expense_by_cat.get(b.category, 0.0)
            pct = (spent / b.amount * 100) if b.amount > 0 else 0
            result.append({
                "category": b.category,
                "budget":   b.amount,
                "spent":    spent,
                "remaining": b.amount - spent,
                "pct":      pct,
                "status":   "over" if pct > 100 else "warning" if pct > 80 else "ok",
            })
        return sorted(result, key=lambda x: x["pct"], reverse=True)

    # ─── Streak & Insights ───────────────────────────────────────────────────

    def spending_streak(self) -> Dict:
        """Consecutive days with expenses."""
        expense_days = sorted(set(
            _to_date(t.date) for t in self.txns if t.type == "expense"
        ), reverse=True)
        if not expense_days:
            return {"streak": 0, "last_expense_day": None}
        streak = 1
        for i in range(1, len(expense_days)):
            if (expense_days[i-1] - expense_days[i]).days == 1:
                streak += 1
            else:
                break
        return {"streak": streak, "last_expense_day": str(expense_days[0])}

    def category_insights(self) -> List[Dict]:
        """Detect unusual spending patterns."""
        by_cat = self.by_category("expense")
        total_exp = self.total_expenses()
        insights = []
        for cat, amount in by_cat.items():
            pct = (amount / total_exp * 100) if total_exp > 0 else 0
            if pct > 40:
                insights.append({
                    "type": "high_spend",
                    "category": cat,
                    "amount": amount,
                    "pct": pct,
                    "message": f"{cat} accounts for {pct:.1f}% of total expenses"
                })
        return insights

    def summary(self) -> Dict:
        fc = self.forecast_next_month()
        return {
            "total_income":    self.total_income(),
            "total_expenses":  self.total_expenses(),
            "net_balance":     self.net_balance(),
            "savings_rate":    self.savings_rate(),
            "counts":          self.transaction_count(),
            "averages":        self.average_transaction(),
            "top_income_cats": dict(list(self.by_category("income").items())[:5]),
            "top_expense_cats":dict(list(self.by_category("expense").items())[:5]),
            "forecast":        fc,
            "trends":          self.monthly_trends(),
            "insights":        self.category_insights(),
        }
