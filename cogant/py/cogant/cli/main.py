"""Main CLI application with all subcommands.

Typer wiring lives in :mod:`cogant.cli._app`; command bodies register via
:mod:`cogant.cli.commands` import side effects.
"""

import cogant.cli.commands  # noqa: F401 — register @app.command handlers
from cogant.cli._app import (
    app,
    console,
)
from cogant.cli._app import (
    apply_upstream_pipeline_flags as _apply_upstream_pipeline_flags,
)
from cogant.cli._app import (
    friendly_pipeline_error as _friendly_pipeline_error,
)
from cogant.cli._app import (
    parse_step_csv as _parse_step_csv,
)
from cogant.cli._app import (
    render_upstream_pipeline_table as _render_upstream_pipeline_table,
)
from cogant.cli._app import (
    run_pipeline_with_progress as _run_pipeline_with_progress,
)
from cogant.cli.migrate import migrate_app
from cogant.cli.plugin import plugin_app

app.add_typer(plugin_app, name="plugin")
app.add_typer(migrate_app, name="migrate")

__all__ = [
    "_apply_upstream_pipeline_flags",
    "_friendly_pipeline_error",
    "_parse_step_csv",
    "_render_upstream_pipeline_table",
    "_run_pipeline_with_progress",
    "app",
    "console",
]


if __name__ == "__main__":
    app()
