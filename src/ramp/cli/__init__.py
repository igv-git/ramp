"""cli — input and rendering only (typer, rich). Commands are registered in one dispatch table."""

from collections.abc import Callable
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ramp import paths
from ramp.cli import wiring
from ramp.config import ConfigError, write_default
from ramp.loop import init_flow
from ramp.matrix import LawError
from ramp.providers.port import ProviderError
from ramp.runner.git_helper import init_repo

app = typer.Typer(help="ramp — onboard onto a new stack through daily micro-projects.", no_args_is_help=True)
console = Console()


def _fail(message: str) -> typer.Exit:
    typer.echo(message, err=True)
    return typer.Exit(1)


def _context(ctx: typer.Context, home: Path):
    try:
        return wiring.context_from(ctx, home)
    except ConfigError as e:
        raise _fail(str(e)) from None


def init_cmd(
    ctx: typer.Context,
    skill: str = typer.Option(..., "--skill", help="Skill to learn, e.g. python"),
    to: int = typer.Option(..., "--to", help="Target level"),
    hours: float | None = typer.Option(None, "--hours", help="Honest hours per day"),
    days: int | None = typer.Option(None, "--days", help="Number of days"),
    deadline: str | None = typer.Option(None, "--deadline", help="Optional deadline"),
    law_dir: Path | None = typer.Option(None, "--law-dir", help="Folder with descriptors.yaml and claims.yaml"),
) -> None:
    """Plan once: check eligibility, then generate the curriculum."""
    home = paths.home()
    try:
        init_repo(home)
    except (OSError, RuntimeError) as e:
        raise _fail(f"cannot set up {home} as a git repository (is git installed?): {e}") from None
    write_default(home)
    context = _context(ctx, home)
    goals: list[str] = []
    try:
        interactive = hours is None or days is None
        if hours is None:
            hours = typer.prompt("Honest hours per day you can spend", type=float)
        if days is None:
            days = typer.prompt("Number of days", type=int, default=14)
        if interactive:
            deadline = deadline or typer.prompt("Deadline (optional)", default="", show_default=False) or None
            raw = typer.prompt("Work goals, comma-separated (optional)", default="", show_default=False)
            goals = [g.strip() for g in raw.split(",") if g.strip()]
        plan = init_flow.run_init(context, law_dir=law_dir or home, skill=skill, target_level=to,
                                  hours_per_day=hours, days=days, deadline=deadline, goals=goals)
    except (LawError, init_flow.InitRefused, init_flow.SliceGenerationError, ProviderError) as e:
        raise _fail(f"init failed: {e}") from None
    except ConfigError as e:
        raise _fail(f"{e}\nEdit {home / 'config.toml'} and run `ramp init` again.") from None
    finally:
        context.store.close()
    table = Table(title=f"{plan.skill} → level {plan.target_level}")
    for col in ("Slice", "Title", "Concepts", "Minutes"):
        table.add_column(col)
    for s in plan.slices:
        table.add_row(s.id, s.title, ", ".join(s.concepts), str(s.est_minutes))
    console.print(table)
    total, budget = sum(s.est_minutes for s in plan.slices), plan.hours_per_day * 60 * plan.days
    console.print(f"Total {total} min of {budget:.0f} min available. Run `ramp today` to start.")


def _not_yet(name: str) -> Callable:
    def command(ctx: typer.Context) -> None:
        """Placeholder until this command's run lands."""
        _context(ctx, paths.home()).store.close()
        raise _fail(f"`ramp {name}` is not available yet in this build.")

    return command


def today_cmd(ctx: typer.Context) -> None:
    """Show due cards, then the current slice brief."""
    _not_yet("today")(ctx)


def submit_cmd(ctx: typer.Context) -> None:
    """Run the acceptance checks and get a review."""
    _not_yet("submit")(ctx)


def export_cmd(ctx: typer.Context) -> None:
    """Write the plain-text snapshot and commit it."""
    _not_yet("export")(ctx)


def flag_bridge_cmd(
    ctx: typer.Context,
    slice_id: str = typer.Argument(..., metavar="SLICE"),
    bridge_no: int = typer.Argument(..., metavar="BRIDGE#"),
    note: str | None = typer.Option(None, "--note"),
) -> None:
    """Mark a bridge (comparison) that misled you."""
    _not_yet("flag-bridge")(ctx)


# One dispatch table: parked features (chat, stats) register here later without touching the commands above.
COMMANDS: dict[str, Callable] = {
    "init": init_cmd,
    "today": today_cmd,
    "submit": submit_cmd,
    "export": export_cmd,
    "flag-bridge": flag_bridge_cmd,
}

for _name, _fn in COMMANDS.items():
    app.command(_name)(_fn)
