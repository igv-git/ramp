"""cli — input/render only (typer, rich). Commands arrive via spec-kit tasks."""

import typer

app = typer.Typer(help="ramp — onboard onto a new stack through daily micro-projects.", no_args_is_help=True)


@app.callback()
def main() -> None:
    """Command group; real commands (init, today, submit, export, flag-bridge) are added by tasks."""
