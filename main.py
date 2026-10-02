"""
main.py - Income & Expenses Manager CLI
Clean, flicker-free command-line financial management system.

Created by Sasindu Dilshara
"""

import sys
import os
import time
from datetime import datetime, date, timedelta
from typing import Optional, List

# Core modules
import config
from models import Account, Transaction, IncomeMethod, ExpenseMethod, Budget, AppSettings, new_id
import database as db
from analytics import Analytics
import charts
from io_manager import export_transactions, import_transactions
import ui_components as ui
from rich.table import Table
from rich import box


class Application:
    """Core application controller."""

    def __init__(self):
        self.db = None
        self.current_account: Optional[Account] = None
        self.current_account_id: str = ""

    def init(self):
        """Initialize database backend and active account."""
        self.db = db.get_backend()
        accounts = self.db.get_accounts()
        if accounts:
            settings = self.db.get_settings()
            if settings.default_account_id:
                acc = self.db.get_account(settings.default_account_id)
                if acc:
                    self.current_account = acc
                    self.current_account_id = acc.id
            if not self.current_account_id:
                self.current_account = accounts[0]
                self.current_account_id = accounts[0].id

        db.start_auto_sync()

    def get_currency_symbol(self) -> str:
        """Get currency symbol for the current active account."""
        curr = self.current_account.currency if self.current_account else config.DEFAULT_CURRENCY
        return config.CURRENCY_SYMBOLS.get(curr, curr + " ")

    def refresh_banner(self, subtitle: str = ""):
        """Print clean header banner."""
        acc_name = self.current_account.name if self.current_account else "No Account"
        acc_curr = self.current_account.currency if self.current_account else config.DEFAULT_CURRENCY
        backend = self.db.get_settings().db_backend if hasattr(self.db, "get_settings") else config.DB_BACKEND
        ui.print_banner(account_name=acc_name, currency=acc_curr, backend=backend)
        if subtitle:
            ui.print_section(subtitle)

    # ─── Main Menu Loop ───────────────────────────────────────────────────────

    def run(self):
        """Main application execution loop."""
        self.init()

        while True:
            self.refresh_banner("Main Navigation")
            
            choices = [
                "1. 📊  Dashboard & Overview",
                "2. 💰  Add Income",
                "3. 💸  Add Expense",
                "4. 📋  View & Search Transactions",
                "5. 📈  Advanced Analytics & Forecast",
                "6. 💳  Manage Payment & Income Methods",
                "7. 🎯  Budget Goals & Tracking",
                "8. 👤  Account Management",
                "9. 📁  Import / Export / Sync",
                "10. ⚙️  Settings & Database",
                "11. ℹ️  About & Credits",
                "12. 🚪  Exit Application"
            ]

            choice = ui.prompt_menu("Select an Option:", choices)

            if choice.startswith("1."):
                self.show_dashboard()
            elif choice.startswith("2."):
                self.add_transaction("income")
            elif choice.startswith("3."):
                self.add_transaction("expense")
            elif choice.startswith("4."):
                self.view_transactions()
            elif choice.startswith("5."):
                self.show_analytics_menu()
            elif choice.startswith("6."):
                self.show_methods_menu()
            elif choice.startswith("7."):
                self.show_budget_menu()
            elif choice.startswith("8."):
                self.show_account_menu()
            elif choice.startswith("9."):
                self.show_io_menu()
            elif choice.startswith("10."):
                self.show_settings_menu()
            elif choice.startswith("11."):
                self.show_about()
            elif choice.startswith("12.") or choice == "BACK":
                self.exit_app()
                break

    # ─── 1. Dashboard ─────────────────────────────────────────────────────────

    def show_dashboard(self):
        """Render high-level financial overview dashboard."""
        self.refresh_banner("Financial Overview Dashboard")
        txns = self.db.get_transactions(account_id=self.current_account_id)
        sym = self.get_currency_symbol()
        a = Analytics(txns)

        # 1. Summary Cards
        stats = a.summary()
        charts.render_summary_cards(stats, currency_symbol=sym)

        # 2. 30-Day Activity Sparklines
        daily = a.by_day(30)
        if daily:
            inc_series = [v["income"] for v in daily.values()]
            exp_series = [v["expense"] for v in daily.values()]
            ui.console.print("  [bold white]30-Day Income Trend :[/bold white] " + charts.sparkline_str(inc_series, color="green"))
            ui.console.print("  [bold white]30-Day Expense Trend:[/bold white] " + charts.sparkline_str(exp_series, color="red"))
            ui.console.print()

        # 3. Category Donut / Breakdown
        top_exp = dict(list(a.by_category("expense").items())[:6])
        if top_exp:
            charts.render_donut_bar(top_exp, title="Top Expense Categories", currency_symbol=sym)

        # 4. Budget Progress
        budgets = self.db.get_budgets(account_id=self.current_account_id)
        if budgets:
            b_data = a.budget_analysis(budgets)
            charts.render_budget_progress(b_data[:4], currency_symbol=sym)

        ui.pause()

    # ─── 2 & 3. Add Transaction ───────────────────────────────────────────────

    def add_transaction(self, txn_type: str = "expense"):
        """Interactive transaction entry workflow."""
        type_title = "Add Income" if txn_type == "income" else "Add Expense"
        self.refresh_banner(type_title)

        sym = self.get_currency_symbol()
        ui.console.print(f"  [bold cyan]Recording new {txn_type.upper()} for account: {self.current_account.name}[/bold cyan]\n")

        # Amount
        amount = ui.prompt_amount(f"Enter {txn_type.capitalize()} Amount ({sym})")
        if amount <= 0:
            ui.show_warning("Operation cancelled: amount was 0.")
            ui.pause()
            return

        # Category
        default_cats = config.DEFAULT_INCOME_CATEGORIES if txn_type == "income" else config.DEFAULT_EXPENSE_CATEGORIES
        cat_choices = default_cats + ["+ Enter Custom Category", "Cancel"]
        cat_pick = ui.prompt_menu("Select Category:", cat_choices)
        
        if cat_pick == "Cancel" or cat_pick == "BACK":
            return
        elif cat_pick.startswith("+"):
            category = ui.prompt_text("Enter Custom Category Name")
            if not category:
                category = "Other"
        else:
            category = cat_pick

        # Description
        desc = ui.prompt_text("Description / Note (Optional)", default="")

        # Method
        if txn_type == "income":
            methods = self.db.get_income_methods()
        else:
            methods = self.db.get_expense_methods()

        method_name = ""
        method_id = ""
        if methods:
            m_choices = [f"{m.icon} {m.name}" for m in methods] + ["None / Skip"]
            m_pick = ui.prompt_menu("Select Payment/Income Method:", m_choices)
            if m_pick not in ("None / Skip", "BACK"):
                for m in methods:
                    if f"{m.icon} {m.name}" == m_pick:
                        method_name = m.name
                        method_id = m.id
                        break

        # Date & Time Selection
        selected_date, selected_time = self.prompt_datetime_selection()
        if not selected_date:
            ui.show_warning("Transaction creation cancelled.")
            ui.pause()
            return

        # Tags
        tags = ui.prompt_text("Tags (comma-separated, optional)", default="")

        # Save
        full_timestamp = f"{selected_date} {selected_time}".strip()
        txn = Transaction(
            account_id=self.current_account_id,
            type=txn_type,
            amount=amount,
            category=category,
            description=desc,
            method_id=method_id,
            method_name=method_name,
            tags=tags,
            date=selected_date,
            created_at=datetime.now().isoformat()
        )
        self.db.save_transaction(txn)

        ui.console.print()
        sign = "+" if txn_type == "income" else "-"
        color = "green" if txn_type == "income" else "red"
        ui.show_success(f"Successfully recorded: [{color}]{sign}{sym}{amount:,.2f}[/{color}] in '{category}' on {full_timestamp}")
        ui.pause()

    def prompt_datetime_selection(self):
        """Prompt user to choose current timestamp or enter custom date & time."""
        now = datetime.now()
        now_date = now.strftime("%Y-%m-%d")
        now_time = now.strftime("%H:%M:%S")
        yesterday_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")

        dt_choices = [
            f"1. 🕒 Current Date & Time ({now_date} {now.strftime('%H:%M')}) [Recommended]",
            f"2. 📅 Today's Date ({now_date})",
            f"3. 🗓️ Yesterday ({yesterday_date})",
            "4. ✍️ Enter Custom Date & Time",
            "Cancel"
        ]

        pick = ui.prompt_menu("Select Date & Time for this Transaction:", dt_choices)

        if pick == "Cancel" or pick == "BACK":
            return None, None
        elif pick.startswith("1."):
            return now_date, now_time
        elif pick.startswith("2."):
            return now_date, now_time
        elif pick.startswith("3."):
            return yesterday_date, now_time
        else:
            # Custom input
            custom_input = ui.prompt_text(
                "Enter Date/Time (e.g. YYYY-MM-DD or YYYY-MM-DD HH:MM)",
                default=f"{now_date} {now.strftime('%H:%M')}"
            )
            if not custom_input:
                return now_date, now_time

            custom_input = custom_input.strip()
            parsed_date = now_date
            parsed_time = now_time

            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d",
                "%d-%m-%Y %H:%M",
                "%d-%m-%Y",
                "%Y/%m/%d %H:%M",
                "%Y/%m/%d",
                "%d/%m/%Y"
            ):
                try:
                    dt = datetime.strptime(custom_input, fmt)
                    parsed_date = dt.strftime("%Y-%m-%d")
                    if "H" in fmt or " " in custom_input or ":" in custom_input:
                        parsed_time = dt.strftime("%H:%M:%S")
                    break
                except ValueError:
                    continue

            return parsed_date, parsed_time

    # ─── 4. View & Search Transactions ────────────────────────────────────────

    def view_transactions(self):
        """List and search transactions with formatted table."""
        while True:
            self.refresh_banner("Transactions Explorer")
            sub_choices = [
                "1. 📋  Show Recent Transactions (Last 25)",
                "2. 🔍  Search by Keyword / Note",
                "3. 📅  Filter by Date Range",
                "4. 🏷️  Filter by Category",
                "5. 🗑️  Delete a Transaction",
                "6. ↩  Back to Main Menu"
            ]
            choice = ui.prompt_menu("Transactions Menu:", sub_choices)

            if choice.startswith("1."):
                self._display_txn_table(self.db.get_transactions(account_id=self.current_account_id)[:25])
            elif choice.startswith("2."):
                kw = ui.prompt_text("Enter search keyword")
                if kw:
                    txns = self.db.get_transactions(account_id=self.current_account_id, search=kw)
                    self._display_txn_table(txns, subtitle=f"Search results for '{kw}'")
            elif choice.startswith("3."):
                d_from = ui.prompt_text("From Date (YYYY-MM-DD)", default=(date.today() - timedelta(days=30)).isoformat())
                d_to = ui.prompt_text("To Date (YYYY-MM-DD)", default=date.today().isoformat())
                txns = self.db.get_transactions(account_id=self.current_account_id, date_from=d_from[:10], date_to=d_to[:10])
                self._display_txn_table(txns, subtitle=f"Date Range: {d_from} to {d_to}")
            elif choice.startswith("4."):
                cats = config.DEFAULT_EXPENSE_CATEGORIES + config.DEFAULT_INCOME_CATEGORIES
                cat_pick = ui.prompt_menu("Select Category to Filter:", cats + ["Back"])
                if cat_pick != "Back" and cat_pick != "BACK":
                    txns = self.db.get_transactions(account_id=self.current_account_id, category=cat_pick)
                    self._display_txn_table(txns, subtitle=f"Category: {cat_pick}")
            elif choice.startswith("5."):
                self._delete_transaction_flow()
            else:
                break

    def _display_txn_table(self, txns: List[Transaction], subtitle: str = ""):
        """Render clean, responsive table of transactions."""
        self.refresh_banner("Transaction Records")
        if subtitle:
            ui.console.print(f"  [bold cyan]Filtering:[/bold cyan] [dim]{subtitle}[/dim]\n")

        if not txns:
            ui.show_warning("No transactions found matching the criteria.")
            ui.pause()
            return

        sym = self.get_currency_symbol()
        table = Table(box=box.ROUNDED, expand=True, border_style="cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Date", width=12)
        table.add_column("Type", width=10, justify="center")
        table.add_column("Category", width=18)
        table.add_column("Description", ratio=1)
        table.add_column("Method", width=14)
        table.add_column("Amount", justify="right", width=14)

        for i, t in enumerate(txns, 1):
            is_inc = t.type == "income"
            t_color = "bold green" if is_inc else "bold red"
            t_sign = "+" if is_inc else "-"
            table.add_row(
                str(i),
                t.date[:10],
                f"[{t_color}]{t.type.upper()}[/{t_color}]",
                t.category[:16],
                (t.description or "—")[:35],
                (t.method_name or "—")[:12],
                f"[{t_color}]{t_sign}{sym}{t.amount:,.2f}[/{t_color}]"
            )

        ui.console.print(table)
        
        # Summary footer
        inc_total = sum(t.amount for t in txns if t.type == "income")
        exp_total = sum(t.amount for t in txns if t.type == "expense")
        net = inc_total - exp_total
        net_col = "green" if net >= 0 else "red"
        ui.console.print(
            f"\n  [dim]Found {len(txns)} records[/dim]  |  "
            f"[green]Income: {sym}{inc_total:,.2f}[/green]  |  "
            f"[red]Expenses: {sym}{exp_total:,.2f}[/red]  |  "
            f"[{net_col}]Net: {sym}{net:+,.2f}[/{net_col}]\n"
        )
        ui.pause()

    def _delete_transaction_flow(self):
        """Interactive transaction deletion."""
        txns = self.db.get_transactions(account_id=self.current_account_id)[:15]
        if not txns:
            ui.show_warning("No transactions to delete.")
            ui.pause()
            return

        sym = self.get_currency_symbol()
        choices = []
        for t in txns:
            sign = "+" if t.type == "income" else "-"
            choices.append(f"{t.date[:10]} | {sign}{sym}{t.amount:,.2f} | {t.category} ({t.description[:20]}) [ID:{t.id[:8]}]")
        choices.append("Cancel")

        pick = ui.prompt_menu("Select transaction to permanently delete:", choices)
        if pick == "Cancel" or pick == "BACK":
            return

        # Find matching txn
        matched = None
        for t in txns:
            if t.id[:8] in pick:
                matched = t
                break

        if matched and ui.prompt_confirm(f"Are you sure you want to delete this {matched.type} transaction of {sym}{matched.amount:,.2f}?"):
            self.db.delete_transaction(matched.id)
            ui.show_success("Transaction deleted successfully.")
            ui.pause()

    # ─── 5. Advanced Analytics & Forecast ─────────────────────────────────────

    def show_analytics_menu(self):
        """Advanced visual analytics menu."""
        while True:
            self.refresh_banner("Advanced Financial Analytics")
            choices = [
                "1. 📊  Expense Category Distribution",
                "2. 💰  Income Source Breakdown",
                "3. 🗓️  Monthly Income vs Expense Trend",
                "4. 🔮  6-Month Rolling Forecast",
                "5. 💡  Smart Habits & Insights",
                "6. ↩  Back to Main Menu"
            ]
            choice = ui.prompt_menu("Analytics Options:", choices)
            sym = self.get_currency_symbol()
            txns = self.db.get_transactions(account_id=self.current_account_id)
            a = Analytics(txns)

            if choice.startswith("1."):
                self.refresh_banner("Expense Distribution")
                by_cat = a.by_category("expense")
                charts.render_bar_chart(by_cat, title="Expenses by Category", currency_symbol=sym)
                charts.render_pie_chart(by_cat, title="Expense Category Share", currency_symbol=sym)
                ui.pause()
            elif choice.startswith("2."):
                self.refresh_banner("Income Sources")
                by_inc = a.by_category("income")
                charts.render_bar_chart(by_inc, title="Income Sources", currency_symbol=sym)
                charts.render_pie_chart(by_inc, title="Income Share", currency_symbol=sym)
                ui.pause()
            elif choice.startswith("3."):
                self.refresh_banner("Monthly Trends")
                by_m = a.by_month()
                if not by_m:
                    ui.show_warning("Not enough transaction history for monthly trends.")
                else:
                    table = Table(box=box.ROUNDED, expand=True, border_style="cyan")
                    table.add_column("Month", width=12)
                    table.add_column("Income", justify="right", style="green")
                    table.add_column("Expenses", justify="right", style="red")
                    table.add_column("Net Balance", justify="right")
                    table.add_column("Trend Indicator", justify="center", width=18)

                    for m, data in list(by_m.items())[-12:]:
                        net = data["net"]
                        net_col = "bold green" if net >= 0 else "bold red"
                        spark = charts.sparkline_str([data["income"], data["expense"]])
                        table.add_row(
                            m,
                            f"{sym}{data['income']:,.2f}",
                            f"{sym}{data['expense']:,.2f}",
                            f"[{net_col}]{sym}{net:+,.2f}[/{net_col}]",
                            spark
                        )
                    ui.console.print(table)
                ui.pause()
            elif choice.startswith("4."):
                self.refresh_banner("Next-Month Forecast")
                fc = a.forecast_next_month()
                if not fc:
                    ui.show_warning("Need at least 2 months of history to project next month.")
                else:
                    fc_net = fc["forecast_net"]
                    net_c = "bold green" if fc_net >= 0 else "bold red"
                    ui.console.print(f"  [bold cyan]Projected Forecast for Month:[/bold cyan] [bold yellow]{fc['month']}[/bold yellow]\n")
                    ui.console.print(f"  [white]Expected Income   :[/white] [green]{sym}{fc['forecast_income']:,.2f}[/green]")
                    ui.console.print(f"  [white]Expected Expenses :[/white] [red]{sym}{fc['forecast_expense']:,.2f}[/red]")
                    ui.console.print(f"  [white]Projected Savings :[/white] [{net_c}]{sym}{fc_net:+,.2f}[/{net_c}]\n")
                    ui.console.print("  [dim]* Calculation uses a 6-month weighted moving average.[/dim]\n")
                ui.pause()
            elif choice.startswith("5."):
                self.refresh_banner("Smart Financial Insights")
                summary = a.summary()
                streak = a.spending_streak()
                insights = summary.get("insights", [])

                sav_rate = summary["savings_rate"]
                sav_c = "green" if sav_rate >= 20 else ("yellow" if sav_rate >= 0 else "red")
                ui.console.print(f"  [bold white]Overall Savings Rate:[/bold white] [{sav_c}]{sav_rate:.1f}%[/{sav_c}]")
                ui.console.print(f"  [bold white]Active Expense Streak:[/bold white] {streak['streak']} consecutive day(s)\n")

                if insights:
                    ui.console.print("  [bold yellow]Automated Spending Alerts:[/bold yellow]")
                    for ins in insights:
                        ui.console.print(f"  [yellow]• {ins['message']}[/yellow]")
                else:
                    ui.show_success("Spending habits look well-balanced! No category exceeds 40% of total expenses.")
                ui.pause()
            else:
                break

    # ─── 6. Methods Management ────────────────────────────────────────────────

    def show_methods_menu(self):
        """Manage reusable income and expense payment methods."""
        while True:
            self.refresh_banner("Reusable Methods Management")
            choices = [
                "1. 📋  List All Methods",
                "2. ➕  Add New Income Method",
                "3. ➕  Add New Expense Method",
                "4. 🗑️  Delete a Method",
                "5. ↩  Back to Main Menu"
            ]
            choice = ui.prompt_menu("Methods Options:", choices)

            if choice.startswith("1."):
                self.refresh_banner("Configured Methods")
                inc_m = self.db.get_income_methods()
                exp_m = self.db.get_expense_methods()

                table = Table(box=box.ROUNDED, expand=True, border_style="cyan")
                table.add_column("Type", width=12)
                table.add_column("Icon", justify="center", width=8)
                table.add_column("Method Name", style="bold white", ratio=1)
                table.add_column("Status", justify="center", width=10)

                for m in inc_m:
                    table.add_row("[green]INCOME[/green]", m.icon, m.name, "✔ ACTIVE")
                for m in exp_m:
                    table.add_row("[red]EXPENSE[/red]", m.icon, m.name, "✔ ACTIVE")

                ui.console.print(table)
                ui.pause()
            elif choice.startswith("2.") or choice.startswith("3."):
                m_type = "income" if choice.startswith("2.") else "expense"
                self.refresh_banner(f"Add {m_type.capitalize()} Method")
                name = ui.prompt_text(f"Enter {m_type.capitalize()} Method Name")
                if name:
                    icon = ui.prompt_text("Emoji Icon (e.g. 💰, 💳, 🏦)", default="💰" if m_type == "income" else "💳")
                    if m_type == "income":
                        self.db.save_income_method(IncomeMethod(name=name, icon=icon))
                    else:
                        self.db.save_expense_method(ExpenseMethod(name=name, icon=icon))
                    ui.show_success(f"{m_type.capitalize()} method '{name}' added successfully.")
                    ui.pause()
            elif choice.startswith("4."):
                self.refresh_banner("Delete Method")
                inc_m = self.db.get_income_methods()
                exp_m = self.db.get_expense_methods()
                del_choices = [f"[INCOME] {m.icon} {m.name} (ID:{m.id[:8]})" for m in inc_m] + \
                              [f"[EXPENSE] {m.icon} {m.name} (ID:{m.id[:8]})" for m in exp_m] + ["Cancel"]
                pick = ui.prompt_menu("Select method to remove:", del_choices)
                if pick != "Cancel" and pick != "BACK":
                    for m in inc_m:
                        if m.id[:8] in pick:
                            self.db.delete_income_method(m.id)
                            ui.show_success(f"Deleted income method '{m.name}'")
                            break
                    for m in exp_m:
                        if m.id[:8] in pick:
                            self.db.delete_expense_method(m.id)
                            ui.show_success(f"Deleted expense method '{m.name}'")
                            break
                    ui.pause()
            else:
                break

    # ─── 7. Budget Goals ──────────────────────────────────────────────────────

    def show_budget_menu(self):
        """Budget goal setting and tracking."""
        while True:
            self.refresh_banner("Budget Goals & Progress")
            choices = [
                "1. 📊  View Budget Progress",
                "2. ➕  Set Category Budget",
                "3. 🗑️  Remove a Budget",
                "4. ↩  Back to Main Menu"
            ]
            choice = ui.prompt_menu("Budget Options:", choices)
            sym = self.get_currency_symbol()
            txns = self.db.get_transactions(account_id=self.current_account_id)
            a = Analytics(txns)

            if choice.startswith("1."):
                self.refresh_banner("Budget Status")
                budgets = self.db.get_budgets(account_id=self.current_account_id)
                b_data = a.budget_analysis(budgets)
                charts.render_budget_progress(b_data, currency_symbol=sym)
                ui.pause()
            elif choice.startswith("2."):
                self.refresh_banner("Set Category Budget")
                cats = config.DEFAULT_EXPENSE_CATEGORIES + ["Cancel"]
                cat_pick = ui.prompt_menu("Select Category for Budget:", cats)
                if cat_pick != "Cancel" and cat_pick != "BACK":
                    amt = ui.prompt_amount(f"Monthly Budget Limit ({sym})")
                    if amt > 0:
                        b = Budget(account_id=self.current_account_id, category=cat_pick, amount=amt, period="monthly")
                        self.db.save_budget(b)
                        ui.show_success(f"Budget of {sym}{amt:,.2f}/month saved for '{cat_pick}'.")
                        ui.pause()
            elif choice.startswith("3."):
                self.refresh_banner("Remove Budget")
                budgets = self.db.get_budgets(account_id=self.current_account_id)
                if not budgets:
                    ui.show_warning("No active budgets.")
                    ui.pause()
                else:
                    b_choices = [f"{b.category}: {sym}{b.amount:,.2f}/{b.period} (ID:{b.id[:8]})" for b in budgets] + ["Cancel"]
                    pick = ui.prompt_menu("Select budget to remove:", b_choices)
                    if pick != "Cancel" and pick != "BACK":
                        for b in budgets:
                            if b.id[:8] in pick:
                                self.db.delete_budget(b.id)
                                ui.show_success(f"Removed budget for '{b.category}'")
                                break
                        ui.pause()
            else:
                break

    # ─── 8. Account Management ────────────────────────────────────────────────

    def show_account_menu(self):
        """Multi-account switcher and creator."""
        while True:
            self.refresh_banner("Account Management")
            choices = [
                "1. 🔄  Switch Active Account",
                "2. ➕  Create New Account",
                "3. 📋  List All Accounts",
                "4. 🗑️  Delete an Account",
                "5. ↩  Back to Main Menu"
            ]
            choice = ui.prompt_menu("Account Options:", choices)

            if choice.startswith("1."):
                accounts = self.db.get_accounts()
                acc_choices = [f"{'✔ ' if a.id == self.current_account_id else '  '}{a.name} ({a.currency})" for a in accounts] + ["Cancel"]
                pick = ui.prompt_menu("Select Account to Activate:", acc_choices)
                if pick != "Cancel" and pick != "BACK":
                    for a in accounts:
                        if a.name in pick:
                            self.current_account = a
                            self.current_account_id = a.id
                            ui.show_success(f"Switched to account: '{a.name}'")
                            break
                    ui.pause()
            elif choice.startswith("2."):
                self.refresh_banner("Create New Account")
                name = ui.prompt_text("Account Name (e.g. Business, Savings)")
                if name:
                    curr = ui.prompt_text("Currency Code (e.g. USD, EUR, GBP, LKR)", default="USD").upper()
                    desc = ui.prompt_text("Description (Optional)", default="")
                    acc = Account(name=name, currency=curr, description=desc)
                    self.db.save_account(acc)
                    if ui.prompt_confirm("Switch to this new account now?"):
                        self.current_account = acc
                        self.current_account_id = acc.id
                    ui.show_success(f"Account '{name}' created.")
                    ui.pause()
            elif choice.startswith("3."):
                self.refresh_banner("Accounts Directory")
                accounts = self.db.get_accounts()
                table = Table(box=box.ROUNDED, expand=True, border_style="cyan")
                table.add_column("Active", justify="center", width=8)
                table.add_column("Account Name", style="bold white", ratio=1)
                table.add_column("Currency", justify="center", width=10)
                table.add_column("Net Balance", justify="right", width=18)

                for a in accounts:
                    is_act = a.id == self.current_account_id
                    txns = self.db.get_transactions(account_id=a.id)
                    net = sum(t.amount if t.type == "income" else -t.amount for t in txns)
                    net_c = "green" if net >= 0 else "red"
                    sym = config.CURRENCY_SYMBOLS.get(a.currency, a.currency + " ")
                    table.add_row(
                        "✔ ACTIVE" if is_act else "—",
                        a.name,
                        a.currency,
                        f"[{net_c}]{sym}{net:+,.2f}[/{net_c}]"
                    )
                ui.console.print(table)
                ui.pause()
            elif choice.startswith("4."):
                accounts = self.db.get_accounts()
                if len(accounts) <= 1:
                    ui.show_warning("Cannot delete the only remaining account.")
                    ui.pause()
                else:
                    del_choices = [a.name for a in accounts if a.id != self.current_account_id] + ["Cancel"]
                    pick = ui.prompt_menu("Select Account to Delete (All its transactions will be deleted!):", del_choices)
                    if pick != "Cancel" and pick != "BACK":
                        for a in accounts:
                            if a.name == pick and ui.prompt_confirm(f"Permanently delete '{a.name}' and all its data?"):
                                self.db.delete_account(a.id)
                                ui.show_success(f"Account '{a.name}' deleted.")
                                break
                        ui.pause()
            else:
                break

    # ─── 9. Import / Export / Sync ────────────────────────────────────────────

    def show_io_menu(self):
        """Multi-format data export and backup management."""
        while True:
            self.refresh_banner("Data Import, Export & Sync")
            choices = [
                "1. 📤  Export Transactions (CSV / JSON / Excel / PDF / TXT)",
                "2. 📥  Import Transactions from File",
                "3. 💾  Full Database Backup (JSON)",
                "4. 🔄  Sync Data (JSON ↔ MySQL)",
                "5. ↩  Back to Main Menu"
            ]
            choice = ui.prompt_menu("I/O Options:", choices)

            if choice.startswith("1."):
                self.refresh_banner("Export Financial Records")
                fmt = ui.prompt_menu("Choose Export Format:", ["CSV", "JSON", "XLSX (Excel)", "PDF Report", "TXT Summary", "Cancel"])
                if fmt != "Cancel" and fmt != "BACK":
                    fmt_key = fmt.split()[0].lower()
                    default_file = f"exports/transactions_{self.current_account.name}_{date.today().isoformat()}.{fmt_key}"
                    dest = ui.prompt_text("Destination File Path", default=default_file)
                    txns = self.db.get_transactions(account_id=self.current_account_id)
                    ok, msg = export_transactions(txns, dest, fmt_key, account_name=self.current_account.name)
                    if ok:
                        ui.show_success(msg)
                    else:
                        ui.show_error(msg)
                    ui.pause()
            elif choice.startswith("2."):
                self.refresh_banner("Import Transactions")
                fpath = ui.prompt_text("Enter file path to import (CSV / JSON / XLSX)")
                if fpath and os.path.exists(fpath):
                    ok, msg, txns = import_transactions(fpath, self.current_account_id)
                    if ok and txns:
                        if ui.prompt_confirm(f"Import {len(txns)} records into '{self.current_account.name}'?"):
                            self.db.bulk_import_transactions(txns)
                            ui.show_success(f"Successfully imported {len(txns)} transactions.")
                    else:
                        ui.show_error(msg)
                else:
                    ui.show_error("File not found.")
                ui.pause()
            elif choice.startswith("3."):
                self.refresh_banner("Database Backup")
                b_path = f"backups/backup_all_{time.strftime('%Y%m%d_%H%M%S')}.json"
                os.makedirs("backups", exist_ok=True)
                data = self.db.export_all()
                import json
                with open(b_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, default=str)
                ui.show_success(f"Full system snapshot backup created: {b_path}")
                ui.pause()
            elif choice.startswith("4."):
                self.refresh_banner("Bidirectional Database Sync")
                sync_pick = ui.prompt_menu("Select Sync Direction:", ["1. JSON → MySQL", "2. MySQL → JSON", "Cancel"])
                if sync_pick.startswith("1."):
                    ok, msg = db.sync_json_to_mysql()
                    if ok: ui.show_success(msg)
                    else: ui.show_error(msg)
                elif sync_pick.startswith("2."):
                    ok, msg = db.sync_mysql_to_json()
                    if ok: ui.show_success(msg)
                    else: ui.show_error(msg)
                ui.pause()
            else:
                break

    # ─── 10. Settings & Database ──────────────────────────────────────────────

    def show_settings_menu(self):
        """System configuration and database backend settings."""
        while True:
            settings = self.db.get_settings()
            self.refresh_banner("Application Settings")
            choices = [
                f"1. 🗄️  Switch Backend Engine (Active: {settings.db_backend.upper()})",
                "2. 🔧  Configure MySQL Credentials",
                f"3. 💱  Set Default Currency (Current: {settings.default_currency})",
                f"4. 🔄  Auto-Sync Toggle (Current: {'ON' if settings.auto_sync else 'OFF'})",
                "5. ↩  Back to Main Menu"
            ]
            choice = ui.prompt_menu("Settings Options:", choices)

            if choice.startswith("1."):
                target = "mysql" if settings.db_backend == "json" else "json"
                if target == "mysql":
                    ui.console.print("  [dim]Testing MySQL connection...[/dim]")
                    try:
                        _ = db.get_mysql_backend()
                        ui.show_success("MySQL connection established!")
                    except Exception as e:
                        ui.show_error(f"Cannot connect to MySQL: {e}")
                        ui.pause()
                        continue
                settings.db_backend = target
                self.db.save_settings(settings)
                self.db = db.switch_backend(target)
                ui.show_success(f"Switched storage backend to: {target.upper()}")
                ui.pause()
            elif choice.startswith("2."):
                self.refresh_banner("MySQL Server Configuration")
                settings.mysql_host = ui.prompt_text("MySQL Host", default=settings.mysql_host)
                port_str = ui.prompt_text("MySQL Port", default=str(settings.mysql_port))
                settings.mysql_port = int(port_str) if port_str.isdigit() else 3306
                settings.mysql_user = ui.prompt_text("MySQL User", default=settings.mysql_user)
                settings.mysql_password = ui.prompt_text("MySQL Password", default=settings.mysql_password)
                settings.mysql_database = ui.prompt_text("MySQL Database", default=settings.mysql_database)
                self.db.save_settings(settings)
                ui.show_success("MySQL credentials saved.")
                ui.pause()
            elif choice.startswith("3."):
                new_curr = ui.prompt_text("Enter Default Currency Code (e.g. USD, EUR, GBP, LKR)", default=settings.default_currency).upper()
                if new_curr:
                    settings.default_currency = new_curr
                    self.db.save_settings(settings)
                    ui.show_success(f"Default currency set to: {new_curr}")
                    ui.pause()
            elif choice.startswith("4."):
                settings.auto_sync = not settings.auto_sync
                self.db.save_settings(settings)
                ui.show_success(f"Auto-Sync is now: {'ENABLED' if settings.auto_sync else 'DISABLED'}")
                ui.pause()
            else:
                break

    # ─── 11. About & Credits ──────────────────────────────────────────────────

    def show_about(self):
        """Display software credits and version info."""
        self.refresh_banner("About Application")
        about_table = Table(box=box.ROUNDED, expand=True, border_style="cyan")
        about_table.add_column("Property", style="bold cyan", width=22)
        about_table.add_column("Details", style="bold white")

        about_table.add_row("Application Name", config.APP_NAME)
        about_table.add_row("Version", f"v{config.APP_VERSION}")
        about_table.add_row("Author / Creator", config.AUTHOR)
        about_table.add_row("GitHub Repository", "github.com/gkdilshara/income-expense-manager")
        about_table.add_row("Storage Architecture", "Dual-Engine (JSON & MySQL with Live Sync)")
        about_table.add_row("UI Framework", "Rich + Questionary (Butter-Smooth Arrow Navigation)")

        ui.console.print(about_table)
        ui.pause()

    # ─── 12. Exit ─────────────────────────────────────────────────────────────

    def exit_app(self):
        """Clean shutdown handler."""
        db.stop_auto_sync()
        ui.clear_screen()
        ui.console.print()
        ui.console.print(Panel(
            "[bold white]Thank you for using Income & Expenses Manager CLI![/bold white]\n"
            f"[dim]Created by {config.AUTHOR} • Version {config.APP_VERSION}[/dim]\n"
            "[bold green]Have a great day! 👋[/bold green]",
            border_style="cyan",
            padding=(1, 4)
        ))
        ui.console.print()


if __name__ == "__main__":
    try:
        app = Application()
        app.run()
    except (KeyboardInterrupt, EOFError):
        ui.clear_screen()
        print("\nSession exited. Goodbye!")
        sys.exit(0)
