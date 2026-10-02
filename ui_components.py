"""
ui_components.py - Clean, flicker-free terminal UI components and interactive prompts.
Built with Rich and Questionary for rock-solid cross-platform arrow navigation.
"""

import os
import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.table import Table
from rich import box
import questionary
from prompt_toolkit.styles import Style

import config

# Initialize Rich console with UTF-8 support
console = Console(highlight=False)

# Custom Questionary styling matching the app theme
QUESTIONARY_STYLE = Style([
    ('qmark', 'fg:#00d7ff bold'),          # Token for question mark (?)
    ('question', 'fg:#ffffff bold'),        # Question text
    ('answer', 'fg:#00ff87 bold'),          # Submitted answer
    ('pointer', 'fg:#00d7ff bold'),         # Pointer symbol (❯)
    ('highlighted', 'fg:#00d7ff bold bg:#1c2833'), # Highlighted choice
    ('selected', 'fg:#00ff87'),             # Selected choice
    ('separator', 'fg:#6c7a89'),            # Separator line
    ('instruction', 'fg:#7f8c8d italic'),   # Instruction text
    ('text', 'fg:#ecf0f1'),                 # General text
    ('disabled', 'fg:#7f8c8d italic'),      # Disabled choice
])


# ─── Clean Header & Logo ──────────────────────────────────────────────────────

ASCII_BANNER = r"""
 ___                            ___  ___                             
|_ _|_ _  __ ___ _ __  ___     | __|/ __|_ __  ___ _ _  ___ ___ ___ 
 | || ' \/ _/ _ \ '  \/ -_)    | _|| (__| '_ \/ -_) ' \(_-</ -_|_-<
|___|_||_\__\___/_|_|_\___|    |___|\___| .__/\___|_||_/__/\___/__/
                                         |_|    M A N A G E R  C L I
"""

def clear_screen():
    """Clear terminal cleanly without leftover artifacts or scrollback jitter."""
    if os.name == 'nt':
        _ = os.system('cls')
    else:
        _ = os.system('clear')


def print_banner(account_name: str = "", currency: str = "", backend: str = "JSON"):
    """Render clean, centered banner with status bar."""
    clear_screen()
    
    # Title art
    banner_text = Text(ASCII_BANNER.strip("\n"), style="bold cyan")
    console.print(Align.center(banner_text))
    console.print()
    
    # Author & Tagline line
    author_text = Text.assemble(
        ("Created by ", "dim white"),
        (f"{config.AUTHOR}", "bold magenta"),
        ("  •  Version ", "dim white"),
        (f"{config.APP_VERSION}", "bold green"),
    )
    console.print(Align.center(author_text))
    
    # Context status bar
    if account_name:
        status_table = Table(box=box.HORIZONTALS, show_header=False, expand=True, border_style="dim cyan")
        status_table.add_column(justify="left", ratio=1)
        status_table.add_column(justify="center", ratio=1)
        status_table.add_column(justify="right", ratio=1)
        
        db_badge = f"[bold green]DB: {backend.upper()}[/bold green]" if backend.lower() == "mysql" else f"[bold cyan]DB: {backend.upper()}[/bold cyan]"
        acc_badge = f"[bold white]Account:[/bold white] [bold yellow]{account_name}[/bold yellow] ([dim]{currency}[/dim])"
        date_badge = f"[dim]{time.strftime('%Y-%m-%d %H:%M')}[/dim]"
        
        status_table.add_row(acc_badge, db_badge, date_badge)
        console.print(status_table)
    else:
        console.print(Align.center(Text("─" * 70, style="dim cyan")))
    console.print()


def print_section(title: str, subtitle: str = ""):
    """Print clean section header panel."""
    content = f"[bold white]{title}[/bold white]"
    if subtitle:
        content += f"\n[dim]{subtitle}[/dim]"
    console.print(Panel(content, border_style="cyan", padding=(0, 2)))
    console.print()


def show_success(msg: str):
    """Display success message banner."""
    console.print(f"  [bold green]✔[/bold green] [green]{msg}[/green]\n")


def show_error(msg: str):
    """Display error message banner."""
    console.print(f"  [bold red]✖[/bold red] [red]{msg}[/red]\n")


def show_info(msg: str):
    """Display info message banner."""
    console.print(f"  [bold cyan]ℹ[/bold cyan] [cyan]{msg}[/cyan]\n")


def show_warning(msg: str):
    """Display warning message banner."""
    console.print(f"  [bold yellow]⚠[/bold yellow] [yellow]{msg}[/yellow]\n")


def pause(prompt: str = "Press Enter or ESC to go back..."):
    """Clean pause prompt supporting Enter, Space, and ESC."""
    console.print(f"\n  [dim]{prompt}[/dim]", end="")
    sys.stdout.flush()
    try:
        if os.name == 'nt':
            import msvcrt
            ch = msvcrt.getwch()
            if ch in ('\xe0', '\x00'):
                msvcrt.getwch()
        else:
            input()
    except (KeyboardInterrupt, EOFError):
        pass
    console.print()


# ─── Interactive Questionary Prompts ──────────────────────────────────────────

def prompt_menu(title: str, choices: list, default: str = None) -> str:
    """
    Render a butter-smooth arrow-key select menu using Questionary.
    Supports Up/Down arrows, Enter to select, and ESC to go Back / Cancel.
    """
    console.print(f"  [bold yellow]{title}[/bold yellow]")
    try:
        q = questionary.select(
            "",
            choices=choices,
            default=default,
            style=QUESTIONARY_STYLE,
            qmark="❯",
            instruction="(Use ↑/↓ arrows, Enter to select, ESC to Go Back)"
        )

        if hasattr(q, "application") and hasattr(q.application, "key_bindings"):
            kb = q.application.key_bindings
            if kb is not None:
                @kb.add("escape", eager=True)
                def _handle_esc(event):
                    event.app.exit(result="BACK")

        selection = q.ask()
        return selection if selection is not None else "BACK"
    except (KeyboardInterrupt, EOFError):
        return "BACK"


def prompt_text(label: str, default: str = "", validate=None) -> str:
    """Prompt for text input with optional validator."""
    try:
        res = questionary.text(
            f"{label}:",
            default=default,
            validate=validate,
            style=QUESTIONARY_STYLE,
            qmark="?"
        ).ask()
        return res.strip() if res is not None else ""
    except (KeyboardInterrupt, EOFError):
        return ""


def prompt_confirm(label: str, default: bool = True) -> bool:
    """Prompt for yes/no confirmation."""
    try:
        res = questionary.confirm(
            label,
            default=default,
            style=QUESTIONARY_STYLE,
            qmark="?"
        ).ask()
        return res if res is not None else False
    except (KeyboardInterrupt, EOFError):
        return False


def prompt_amount(label: str = "Enter Amount") -> float:
    """Prompt and validate a positive floating point amount."""
    while True:
        val_str = prompt_text(label)
        if not val_str:
            return 0.0
        val_str = val_str.replace(",", "").replace("$", "").replace("+", "").replace("-", "").strip()
        try:
            val = float(val_str)
            if val <= 0:
                show_error("Amount must be greater than 0.")
                continue
            return val
        except ValueError:
            show_error("Please enter a valid numeric amount.")
