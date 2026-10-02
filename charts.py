"""
charts.py - Clean CLI data visualizations and reports.
Generates flicker-free ASCII/Unicode bar charts, pie charts, sparklines, line trends, and progress bars.
"""

import math
from typing import Dict, List, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console(highlight=False)

PALETTE = [
    "cyan", "bright_green", "yellow", "bright_magenta",
    "bright_cyan", "green", "magenta", "blue", "white"
]

SLICE_SYMBOLS = ["●", "■", "▲", "◆", "★", "○", "□", "△", "◇"]


# ─── Summary Stat Cards ───────────────────────────────────────────────────────

def render_summary_cards(stats: Dict, currency_symbol: str = "$"):
    """Render 4 responsive summary cards."""
    income = stats.get("total_income", 0.0)
    expenses = stats.get("total_expenses", 0.0)
    net = stats.get("net_balance", 0.0)
    savings = stats.get("savings_rate", 0.0)

    net_color = "bold green" if net >= 0 else "bold red"
    net_sign = "+" if net >= 0 else ""
    savings_color = "bold green" if savings >= 20 else ("bold yellow" if savings >= 0 else "bold red")

    cards_table = Table(box=box.ROUNDED, expand=True, border_style="cyan", show_header=False)
    cards_table.add_column(justify="center", ratio=1)
    cards_table.add_column(justify="center", ratio=1)
    cards_table.add_column(justify="center", ratio=1)
    cards_table.add_column(justify="center", ratio=1)

    cards_table.add_row(
        f"[bold green]TOTAL INCOME[/bold green]\n[white]{currency_symbol}{income:,.2f}[/white]",
        f"[bold red]TOTAL EXPENSES[/bold red]\n[white]{currency_symbol}{expenses:,.2f}[/white]",
        f"[{net_color}]NET BALANCE[/{net_color}]\n[{net_color}]{net_sign}{currency_symbol}{net:,.2f}[/{net_color}]",
        f"[{savings_color}]SAVINGS RATE[/{savings_color}]\n[{savings_color}]{savings:.1f}%[/{savings_color}]"
    )

    console.print(cards_table)
    console.print()


# ─── Bar Chart ────────────────────────────────────────────────────────────────

def render_bar_chart(data: Dict[str, float], title: str = "", currency_symbol: str = "$", max_bars: int = 8, bar_width: int = 35):
    """Render a clean horizontal bar chart with percentage breakdown."""
    if not data:
        console.print("  [dim]No data available to display.[/dim]")
        return

    items = [(k, v) for k, v in data.items() if v > 0][:max_bars]
    if not items:
        console.print("  [dim]No non-zero data available.[/dim]")
        return

    total = sum(v for _, v in items)
    max_val = max(v for _, v in items) if items else 1.0
    max_label_len = min(22, max(len(k) for k, _ in items))

    if title:
        console.print(f"  [bold cyan]── {title} ──────────────────────────────────────[/bold cyan]"[:60])

    for i, (label, val) in enumerate(items):
        color = PALETTE[i % len(PALETTE)]
        ratio = val / max_val if max_val > 0 else 0
        filled = max(1, int(ratio * bar_width)) if val > 0 else 0
        pct = (val / total * 100) if total > 0 else 0
        
        bar_str = "█" * filled
        pad_label = label[:max_label_len].ljust(max_label_len)
        console.print(
            f"  [{color}]{pad_label}[/{color}] "
            f"[{color}]{bar_str}[/{color}] "
            f"[white]{currency_symbol}{val:,.2f}[/white] [dim]({pct:.1f}%)[/dim]"
        )
    console.print()


# ─── Donut / Category Bar ─────────────────────────────────────────────────────

def render_donut_bar(data: Dict[str, float], title: str = "", currency_symbol: str = "$", total_width: int = 48):
    """Render a horizontal segment breakdown bar with color legend."""
    if not data:
        console.print("  [dim]No category data.[/dim]")
        return

    items = [(k, v) for k, v in data.items() if v > 0][:6]
    total = sum(v for _, v in items)
    if total <= 0:
        return

    if title:
        console.print(f"  [bold cyan]── {title} ──────────────────────────────────────[/bold cyan]"[:60])

    bar_segments = ""
    for i, (label, val) in enumerate(items):
        color = PALETTE[i % len(PALETTE)]
        seg_len = max(1, int((val / total) * total_width))
        bar_segments += f"[{color}]{'█' * seg_len}[/{color}]"

    console.print(f"  [{bar_segments}]")
    console.print()

    # Legend table
    leg_table = Table(box=None, show_header=False, padding=(0, 2))
    leg_table.add_column()
    leg_table.add_column()
    
    legend_items = []
    for i, (label, val) in enumerate(items):
        color = PALETTE[i % len(PALETTE)]
        pct = (val / total) * 100
        sym = SLICE_SYMBOLS[i % len(SLICE_SYMBOLS)]
        item_str = f"[{color}]{sym} {label[:18]:<18}[/{color}] [white]{currency_symbol}{val:,.2f}[/white] [dim]({pct:.1f}%)[/dim]"
        legend_items.append(item_str)

    # 2 items per row in legend
    for i in range(0, len(legend_items), 2):
        row = [legend_items[i]]
        if i + 1 < len(legend_items):
            row.append(legend_items[i + 1])
        else:
            row.append("")
        leg_table.add_row(*row)

    console.print(leg_table)
    console.print()


# ─── Pie Chart (ASCII Matrix) ─────────────────────────────────────────────────

def render_pie_chart(data: Dict[str, float], title: str = "", currency_symbol: str = "$", radius: int = 6):
    """Render circular ASCII pie chart with side legend."""
    if not data:
        console.print("  [dim]No data to display.[/dim]")
        return

    items = [(k, v) for k, v in data.items() if v > 0][:8]
    total = sum(v for _, v in items)
    if total <= 0:
        return

    height = radius * 2 + 1
    width = radius * 4 + 1
    grid = [[(" ", -1) for _ in range(width)] for _ in range(height)]

    # Compute angle bounds
    angles = []
    cum = 0.0
    for i, (label, val) in enumerate(items):
        s_angle = cum * 2 * math.pi
        cum += val / total
        e_angle = cum * 2 * math.pi
        angles.append((s_angle, e_angle, i))

    for r in range(height):
        for c in range(width):
            x = (c - width / 2) / (radius * 2)
            y = (r - height / 2) / radius
            dist = math.sqrt(x * x + y * y)
            if dist <= 0.5:
                if dist < 0.12:
                    grid[r][c] = ("◉", -2)
                else:
                    angle = math.atan2(y, x)
                    if angle < 0:
                        angle += 2 * math.pi
                    for s_a, e_a, idx in angles:
                        if s_a <= angle <= e_a:
                            grid[r][c] = (SLICE_SYMBOLS[idx % len(SLICE_SYMBOLS)], idx)
                            break

    if title:
        console.print(f"  [bold cyan]── {title} ──────────────────────────────────────[/bold cyan]"[:60])

    legend_lines = []
    for i, (label, val) in enumerate(items):
        pct = (val / total) * 100
        color = PALETTE[i % len(PALETTE)]
        sym = SLICE_SYMBOLS[i % len(SLICE_SYMBOLS)]
        legend_lines.append(
            f"[{color}]{sym} {label[:16]:<16}[/{color}] [white]{currency_symbol}{val:,.2f}[/white] [dim]({pct:.1f}%)[/dim]"
        )

    pie_lines = []
    for r in grid:
        line = ""
        for ch, s_idx in r:
            if s_idx >= 0:
                color = PALETTE[s_idx % len(PALETTE)]
                line += f"[{color}]{ch}[/{color}]"
            elif s_idx == -2:
                line += "[dim cyan]◉[/dim cyan]"
            else:
                line += " "
        pie_lines.append(line)

    max_rows = max(len(pie_lines), len(legend_lines))
    for i in range(max_rows):
        p_part = pie_lines[i] if i < len(pie_lines) else " " * width
        l_part = legend_lines[i] if i < len(legend_lines) else ""
        console.print(f"  {p_part}   {l_part}")
    console.print()


# ─── Sparklines & Progress Bars ───────────────────────────────────────────────

def sparkline_str(values: List[float], color: str = "cyan") -> str:
    """Generate compact UTF-8 sparkline string."""
    if not values:
        return "─"
    chars = [" ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    min_v = min(values)
    max_v = max(values)
    rng = max_v - min_v or 1.0
    res = ""
    for v in values:
        idx = min(len(chars) - 1, max(0, int((v - min_v) / rng * (len(chars) - 1))))
        res += chars[idx]
    return f"[{color}]{res}[/{color}]"


def render_budget_progress(budget_data: List[Dict], currency_symbol: str = "$"):
    """Render budget vs actual progress bars."""
    if not budget_data:
        console.print("  [dim]No budget goals set for this account.[/dim]")
        return

    console.print(f"  [bold cyan]── Budget vs Actual ───────────────────────────────────[/bold cyan]"[:60])
    bar_w = 26

    for b in budget_data:
        spent = b["spent"]
        budget = b["budget"]
        pct = b["pct"]
        status = b["status"]

        color = "red" if status == "over" else ("yellow" if status == "warning" else "green")
        fill_count = min(bar_w, max(0, int((spent / budget * bar_w) if budget > 0 else 0)))
        empty_count = max(0, bar_w - fill_count)
        
        bar_render = f"[{color}]{'█' * fill_count}[/{color}][dim]{'░' * empty_count}[/dim]"
        status_icon = "✖ OVER" if status == "over" else ("▲ WARN" if status == "warning" else "✔ OK")
        
        console.print(
            f"  [{color}]{status_icon:<6}[/{color}] [white]{b['category'][:14]:<14}[/white] "
            f"│{bar_render}│ "
            f"[dim]{currency_symbol}{spent:,.2f} / {currency_symbol}{budget:,.2f}[/dim] [{color}]({pct:.0f}%)[/{color}]"
        )
    console.print()
