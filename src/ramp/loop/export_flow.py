"""Export sequencer: write the JSONL files, then commit them through the fixed-argv git helper."""

from collections.abc import Callable
from datetime import UTC, datetime

from ramp.runner.git_helper import commit_export
from ramp.store import export


class ExportFailed(Exception):
    pass


def run_export(ctx, clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> export.Counts:
    try:
        export.export_all(ctx.store, ctx.home)
        commit_export(ctx.home, clock)
        return export.counts(ctx.home)
    except (export.ExportError, RuntimeError, OSError) as e:
        raise ExportFailed(str(e)) from None


def auto_export(ctx, clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> str | None:
    """End-of-command export. Returns the failure text (to print), never raises: it must not change the exit status."""
    try:
        run_export(ctx, clock)
    except ExportFailed as e:
        return str(e)
    return None
