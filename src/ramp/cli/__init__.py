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
from ramp.loop import export_flow, flag_flow, init_flow, submit_flow, today_flow
from ramp.matrix import LawError
from ramp.providers.port import ProviderError
from ramp.runner.git_helper import init_repo
from ramp.store import export as export_store

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


def _print_drained(lines: list[str]) -> None:
    for line in lines:
        console.print(Text(line, style="yellow" if line.startswith(("Still", "Queued")) else ""))


def _auto_export(context) -> None:
    """End-of-command export: a failure is printed and never changes the command's exit status."""
    failure = export_flow.auto_export(context)
    if failure:
        typer.echo(f"export failed: {failure}", err=True)


def _auto_export_if_open(context) -> None:
    try:
        _auto_export(context)
    finally:
        context.store.close()


def _ask(label: str) -> str:
    return typer.prompt(label, default="", show_default=False).strip()


def _review_cards(context, view) -> None:
    """Serve each due card: question, written answer, grade, reschedule. A blank answer skips the card."""
    for card in view.cards:
        console.print(Panel(Text(card.question), title=f"Review: {card.concept}", title_align="left"))
        answer = _ask("Your answer (Enter to skip)")
        if not answer:
            console.print(Text("Skipped; it stays due."))
            continue
        try:
            res = today_flow.answer_card(context, card.card_id, answer)
        except ProviderError as e:
            console.print(Text(f"Could not grade this card now ({e}); it stays due. Run `ramp today` again later.",
                               style="yellow"))
            return
        console.print(Text(f"Grade {res.grade}/5: {res.rationale}"))


def today_cmd(ctx: typer.Context) -> None:
    """Review due cards first, then show today's slice brief."""
    context = _context(ctx, paths.home())
    try:
        view = today_flow.run_today(context)
        _print_drained(view.drained)
        _review_cards(context, view)
    except today_flow.NoCurriculum as e:
        raise _fail(str(e)) from None
    finally:
        _auto_export_if_open(context)
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


def _teach_back(context, out) -> None:
    console.print(Text("\n" + out.teachback_question))
    answer = ""
    try:
        while not answer:
            answer = _ask("Your teach-back")
    except typer.Abort:
        console.print(Text("Teach-back not recorded; the next slice stays locked. Run `ramp submit` again to "
                           "finish it (the review is reused, no model call).", style="yellow"))
        raise
    res = submit_flow.complete_teachback(context, out, answer)
    if res.grade is None:
        console.print(Text("Teach-back saved; it could not be graded now."))
    else:
        console.print(Text(f"Teach-back grade {res.grade}/5: {res.rationale}"))
    if res.cards_created:
        console.print(Text("Added review cards for: " + ", ".join(res.cards_created)))
    if res.unlocked:
        console.print(Text(f"Next slice {res.unlocked} unlocked. Run `ramp today`."))
    else:
        console.print(Text("That was the last slice."))


def submit_cmd(ctx: typer.Context) -> None:
    """Run the acceptance checks and get a review; on a pass, answer a teach-back to unlock the next slice."""
    context = _context(ctx, paths.home())
    try:
        try:
            out = submit_flow.run_submit(context)
        except (submit_flow.NothingToSubmit, today_flow.NoCurriculum) as e:
            raise _fail(str(e)) from None
        _print_drained(out.drained)
        _print_submit(out)
        if out.passed and out.needs_teachback:
            _teach_back(context, out)
    except KeyboardInterrupt:
        typer.echo("Interrupted. Your attempt is saved as blocked (interrupted) and is not counted against you. "
                   "Run `ramp submit` again when you are ready.", err=True)
        raise typer.Exit(1) from None
    finally:
        _auto_export_if_open(context)


def _print_submit(out) -> None:
    for argv, code in out.commands:
        state = "ok" if code == 0 else "timed out / not started" if code is None else f"exit {code}"
        console.print(Text(f"  {' '.join(argv)}  ->  {state}"))
    for note in out.layout_notes:
        console.print(Text(f"Layout: {note}", style="yellow"))
    if out.reused_review:
        console.print(Text("Same code and test output as an earlier submit: reusing that review (no model call)."))
    if out.fingerprint_changed:
        console.print(Text("Note: the test or fixture files differ from the shipped ones (logged, not blocked)."))
    if out.status == "queued":
        console.print(Text("The provider is unreachable, so your review is queued. The tests ran and your attempt "
                           "is saved; the slice stays where it is. The next `ramp today` or `ramp submit` reviews it "
                           "once the provider is back."))
        return
    if out.status == "blocked":
        cause = out.blocked_cause or ""
        advice = ("check your network, the API key and the spending caps in config.toml, then run `ramp submit` "
                  "again" if cause.startswith("provider") else "fix the cause, then run `ramp submit` again")
        typer.echo(f"Blocked: {cause}\nThis is not counted against you. What to try: {advice}.", err=True)
        raise typer.Exit(1)
    if out.passed:
        console.print(Text("Passed.", style="bold green"))
        return
    console.print(Text("Not passed yet (verdict: needs work).", style="bold"))
    for reason in out.reasons:
        console.print(Text(f"  - {reason}"))
    for issue in out.issues:
        console.print(Text(f"\n{issue.location}\n  {issue.symptom}\n  Hint: {issue.hint}"))
    if out.understanding_check:
        console.print(Text(f"\nThink about: {out.understanding_check}"))


def export_cmd(ctx: typer.Context) -> None:
    """Write the plain-text snapshot, commit it and print the counts."""
    context = _context(ctx, paths.home())
    try:
        counts = export_flow.run_export(context)
    except export_flow.ExportFailed as e:
        raise _fail(f"export failed: {e}") from None
    finally:
        context.store.close()
    console.print(Text(export_store.format_counts(counts)))


def flag_bridge_cmd(
    ctx: typer.Context,
    slice_id: str = typer.Argument(..., metavar="SLICE"),
    bridge_no: int = typer.Argument(..., metavar="BRIDGE#"),
    note: str | None = typer.Option(None, "--note"),
) -> None:
    """Mark a bridge (comparison) that misled you."""
    context = _context(ctx, paths.home())
    try:
        try:
            flag_flow.flag_bridge(context, slice_id.strip(), bridge_no, note)
        except flag_flow.FlagRefused as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(2) from None
        console.print(Text(f"Flagged bridge {bridge_no} of {slice_id.strip()}."))
        _auto_export(context)
    finally:
        context.store.close()


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
