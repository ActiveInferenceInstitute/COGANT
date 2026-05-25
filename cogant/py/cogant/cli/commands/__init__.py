"""Register all CLI command modules (import side effects)."""

from cogant.cli.commands import analyze as _analyze
from cogant.cli.commands import export_validate as _export_validate
from cogant.cli.commands import ingest as _ingest
from cogant.cli.commands import setup as _setup
from cogant.cli.commands import tools as _tools
from cogant.cli.commands import translate_cmd as _translate_cmd

__all__: list[str] = []
