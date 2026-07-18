"""Module execution entry point for ``python -m cogant.cli``."""

from cogant.cli.main import app


def main() -> None:
    """Run the installed COGANT Typer application."""
    app()


if __name__ == "__main__":
    main()
