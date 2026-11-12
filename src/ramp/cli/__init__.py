"""cli — input and rendering only (typer, rich). Commands are registered in one dispatch table."""

from collections.abc import Callable
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ramp import paths
from ramp.cli import wiring
from ramp.config import ConfigError, write_default
from ramp.loop import init_flow, submit_flow, today_flow
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
    """Show today's slice brief (due review cards come first once cards exist)."""
    context = _context(ctx, paths.home())
    try:
        view = today_flow.run_today(context)
    except today_flow.NoCurriculum as e:
        raise _fail(str(e)) from None
    finally:
        context.store.close()
    if view.finished:
        console.print(Text(view.message))
        return
    body = Text(view.brief)
    if view.bridges:
        body.append("\n\nBridges to what you know:\n", style="bold")
        for i, bridge in enumerate(view.bridges, start=1):
            body.append(f"  {i}. {bridge}\n")
    console.print(Panel(body, title=f"{view.slice_id} — {view.title}", title_align="left"))
    console.print(Text(f"Workspace: {view.workspace}\nWrite your code in src/, then run `ramp submit`."))


def submit_cmd(ctx: typer.Context) -> None:
    """Run the acceptance checks and get a review."""
    context = _context(ctx, paths.home())
    try:
        out = submit_flow.run_submit(context)
    except (submit_flow.NothingToSubmit, today_flow.NoCurriculum) as e:
        raise _fail(str(e)) from None
    finally:
        context.store.close()
    for argv, code in out.commands:
        state = "ok" if code == 0 else "timed out / not started" if code is None else f"exit {code}"
        console.print(Text(f"  {' '.join(argv)}  ->  {state}"))
    if out.fingerprint_changed:
        console.print(Text("Note: the test or fixture files differ from the shipped ones (logged, not blocked)."))
    if out.status == "blocked":
        typer.echo(f"Blocked: {out.blocked_cause}\nThis is not counted against you. Fix the cause and run "
                   "`ramp submit` again.", err=True)
        raise typer.Exit(1)
    if out.passed:
        console.print(Text("Passed.", style="bold green"))
        if out.unlocked:
            console.print(Text(f"Next slice {out.unlocked} unlocked. Run `ramp today`."))
        else:
            console.print(Text("That was the last slice."))
        return
    console.print(Text("Not passed yet (verdict: needs work).", style="bold"))
    for reason in out.reasons:
        console.print(Text(f"  - {reason}"))
    for issue in out.issues:
        console.print(Text(f"\n{issue.location}\n  {issue.symptom}\n  Hint: {issue.hint}"))
    if out.understanding_check:
        console.print(Text(f"\nThink about: {out.understanding_check}"))


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
