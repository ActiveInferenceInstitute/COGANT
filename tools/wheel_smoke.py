from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INNER = ROOT / "cogant"


def main() -> None:
    output = ROOT / "output"
    output.mkdir(exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix="wheel-smoke-", dir=output))
    wheels = workspace / "wheels"
    subprocess.run(["uv", "build", "--wheel", "--out-dir", str(wheels)], cwd=INNER, check=True)
    (wheel,) = wheels.glob("cogant-*.whl")
    environment = workspace / "venv"
    subprocess.run(["uv", "venv", "--python", sys.executable, str(environment)], check=True)
    python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    subprocess.run(["uv", "pip", "install", "--python", str(python), str(wheel)], check=True)
    subprocess.run(
        [
            str(python),
            "-I",
            "-c",
            "import importlib; "
            "[importlib.import_module(n) for n in ('cogant','cogant.api','cogant.cli',"
            "'cogant.config','cogant.gnn','cogant.parsers','cogant.reverse','cogant.server')]; "
            "from cogant.parsers import get_parser, parser_capabilities; "
            "[get_parser(lang) for lang in sorted(parser_capabilities())]",
        ],
        cwd=workspace,
        check=True,
    )
    dist = INNER / "dist"
    dist.mkdir(exist_ok=True)
    (dist / wheel.name).write_bytes(wheel.read_bytes())
    print(f"Installed wheel smoke passed: {wheel}")


if __name__ == "__main__":
    main()
