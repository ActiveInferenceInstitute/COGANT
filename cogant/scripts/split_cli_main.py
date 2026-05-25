#!/usr/bin/env python3
"""Mechanical split of cli/main.py into _app.py + commands/*.py."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "py/cogant/cli/main.py"
CMD_DIR = ROOT / "py/cogant/cli/commands"

lines = MAIN.read_text(encoding="utf-8").splitlines(keepends=True)

APP_HEADER = '''"""Shared Typer app, console, and CLI helper utilities."""

import functools
import logging
import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from cogant.api.pipeline import PipelineConfig, PipelineRunner
from cogant.api.bundle import Bundle

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

console = Console()

app = typer.Typer(
    name="cogant",
    help=(
        "Codebase-to-GNN Translation Engine.\\n\\n"
        "Translate a repository into an Active Inference Generalized "
        "Notation Notation (GNN) state-space model. Run "
        "[bold]cogant doctor[/bold] first to verify your environment, "
        "then [bold]cogant init <repo>[/bold] for a guided first run."
    ),
    no_args_is_help=True,
    rich_markup_mode="rich",
)


'''

CMD_IMPORT = '''"""CLI command registrations."""

import functools
from pathlib import Path
from typing import Any

import typer
from rich.panel import Panel
from rich.table import Table

from cogant.api.analysis_commands import (
    run_graph_analysis,
    run_multi_export,
    run_static_analysis,
    run_visualize,
)
from cogant.api.bundle import Bundle
from cogant.api.pipeline import PipelineConfig, PipelineRunner
from cogant.api.session import Session
from cogant.cli.doctor import doctor_command, render_report, run_doctor
from cogant.ingest.repo_sniff import count_source_files as _count_source_files
from cogant.ingest.repo_sniff import estimate_pipeline_seconds as _estimate_pipeline_seconds
from cogant.ingest.repo_sniff import format_duration as _format_duration
from cogant.reverse.cli import reverse_command, roundtrip_command
from cogant.cli._app import (
    app,
    console,
    friendly_pipeline_error as _friendly_pipeline_error,
    parse_step_csv as _parse_step_csv,
    apply_upstream_pipeline_flags as _apply_upstream_pipeline_flags,
    render_upstream_pipeline_table as _render_upstream_pipeline_table,
    run_pipeline_with_progress as _run_pipeline_with_progress,
)

'''

SECTIONS: list[tuple[str, int, int, str]] = [
    ("_app.py", 78, 200, APP_HEADER),
    ("_app.py", 374, 426, ""),  # append progress helper
    ("setup.py", 202, 372, CMD_IMPORT),
    ("ingest.py", 428, 592, CMD_IMPORT),
    ("translate_cmd.py", 593, 854, CMD_IMPORT),
    ("analyze.py", 855, 1328, CMD_IMPORT),
    ("export_validate.py", 1329, 1715, CMD_IMPORT),
    ("tools.py", 1716, 2045, CMD_IMPORT),
]

# Rename helpers in _app chunk
RENAME_IN_APP = {
    "def _parse_step_csv": "def parse_step_csv",
    "def _apply_upstream_pipeline_flags": "def apply_upstream_pipeline_flags",
    "def _render_upstream_pipeline_table": "def render_upstream_pipeline_table",
    "def _friendly_pipeline_error": "def friendly_pipeline_error",
    "def _run_pipeline_with_progress": "def run_pipeline_with_progress",
}


def transform_app_chunk(chunk: str) -> str:
    for old, new in RENAME_IN_APP.items():
        chunk = chunk.replace(old, new)
    # Fix internal calls within app helpers
    chunk = chunk.replace("_parse_step_csv(", "parse_step_csv(")
    return chunk


app_content = APP_HEADER
for filename, start, end, header in SECTIONS:
    chunk = "".join(lines[start - 1 : end])
    if filename == "_app.py":
        chunk = transform_app_chunk(chunk)
        app_content += chunk

(ROOT / "py/cogant/cli/_app.py").write_text(app_content, encoding="utf-8")

CMD_DIR.mkdir(exist_ok=True)
(CMD_DIR / "__init__.py").write_text(
    '"""Register all CLI command modules (import side effects)."""\n\n'
    "from cogant.cli.commands import analyze as _analyze\n"
    "from cogant.cli.commands import export_validate as _export_validate\n"
    "from cogant.cli.commands import ingest as _ingest\n"
    "from cogant.cli.commands import setup as _setup\n"
    "from cogant.cli.commands import tools as _tools\n"
    "from cogant.cli.commands import translate_cmd as _translate_cmd\n\n"
    "__all__: list[str] = []\n",
    encoding="utf-8",
)

for filename, start, end, header in SECTIONS:
    if filename == "_app.py":
        continue
    chunk = "".join(lines[start - 1 : end])
    (CMD_DIR / filename).write_text(header + chunk, encoding="utf-8")

MAIN_NEW = '''"""Main CLI application with all subcommands.

Typer wiring lives in :mod:`cogant.cli._app`; command bodies register via
:mod:`cogant.cli.commands` import side effects.
"""

from cogant.cli._app import app
from cogant.cli.migrate import migrate_app
from cogant.cli.plugin import plugin_app
import cogant.cli.commands  # noqa: F401 — register @app.command handlers

app.add_typer(plugin_app, name="plugin")
app.add_typer(migrate_app, name="migrate")


if __name__ == "__main__":
    app()
'''
MAIN.write_text(MAIN_NEW, encoding="utf-8")
print("cli split:", (ROOT / "py/cogant/cli/main.py").read_text().count("\n"), "main lines")
for p in sorted(CMD_DIR.glob("*.py")):
    print(p.name, sum(1 for _ in p.open()))
