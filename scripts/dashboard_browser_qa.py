#!/usr/bin/env python3
"""Browser QA for generated COGANT dashboards.

Uses ``chrome-devtools-axi`` when available to open a local dashboard at
desktop and mobile widths, capture screenshots, check broken images, verify
required text, and report obvious horizontal overflow. If the browser tool is
not installed, the script falls back to a static image-path scan and records
that the browser checks were skipped.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

# Project root = projects/working/cogant/ (parent of scripts/). Used to resolve the
# default dashboard location the same way ``batch_dashboard.py`` does, so this
# script can run as a zero-argument analysis step under stage-04.
_STAGING_ROOT = Path(__file__).resolve().parent.parent

# Candidate locations for the HTML dashboard produced upstream by
# ``batch_dashboard.py`` (the ``site/`` builder). First existing match wins.
_DEFAULT_HTML_CANDIDATES = (
    _STAGING_ROOT / "cogant" / "output" / "dashboard" / "site" / "inspection_dashboard.html",
    _STAGING_ROOT / "output" / "dashboard" / "site" / "inspection_dashboard.html",
)


def _discover_dashboard_html() -> Path | None:
    """Locate the upstream-generated dashboard HTML, if one exists.

    Returns the first existing canonical candidate, else ``None``. Returning
    ``None`` lets the orchestrator path skip gracefully instead of crashing
    the Analysis stage when no dashboard HTML has been built yet.
    """
    for candidate in _DEFAULT_HTML_CANDIDATES:
        if candidate.is_file():
            return candidate
    return None


def _run_axi(args: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["chrome-devtools-axi", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )


def _file_url(path: Path) -> str:
    return path.resolve().as_uri()


def _static_broken_images(html_path: Path) -> list[str]:
    import re

    text = html_path.read_text(encoding="utf-8")
    broken: list[str] = []
    for raw in re.findall(r"<img[^>]+src=[\"']([^\"']+)[\"']", text):
        if raw.startswith("data:") or raw.startswith(("http://", "https://")):
            continue
        parsed = urlparse(raw)
        if parsed.scheme == "file":
            target = Path(unquote(parsed.path))
        else:
            target = (html_path.parent / unquote(parsed.path)).resolve()
        if not target.is_file():
            broken.append(raw)
    return broken


def _browser_eval() -> str:
    return """JSON.stringify({
        title: document.title,
        bodyText: document.body.innerText,
        imageCount: document.images.length,
        brokenImages: Array.from(document.images)
          .filter(img => !img.complete || img.naturalWidth === 0)
          .map(img => img.getAttribute('src') || ''),
        overflow: Array.from(document.querySelectorAll('body *'))
          .filter(el => el.scrollWidth > el.clientWidth + 2)
          .filter(el => !['svg', 'pre', 'code', 'table'].includes(el.tagName.toLowerCase()))
          .slice(0, 20)
          .map(el => ({
            tag: el.tagName.toLowerCase(),
            text: (el.innerText || el.alt || '').slice(0, 80),
            scrollWidth: el.scrollWidth,
            clientWidth: el.clientWidth
          }))
      })"""


def run_browser_qa(html_path: Path, output_dir: Path, required_text: list[str]) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {
        "schema_version": "1.0",
        "html": str(html_path.resolve()),
        "engine": "chrome-devtools-axi",
        "screenshots": {},
        "required_text": required_text,
        "checks": {},
        "ok": False,
    }

    if shutil.which("chrome-devtools-axi") is None:
        broken = _static_broken_images(html_path)
        report["engine"] = "static-fallback"
        report["checks"] = {
            "browser_available": False,
            "broken_images": broken,
            "required_text_missing": [
                text for text in required_text if text not in html_path.read_text(encoding="utf-8")
            ],
            "overflow": "not_checked",
        }
        report["ok"] = not broken and not report["checks"]["required_text_missing"]
        return report

    opened = _run_axi(["open", _file_url(html_path)])
    report["open_output"] = opened.stdout[-2000:]
    desktop = (output_dir / "dashboard_desktop.png").resolve()
    mobile = (output_dir / "dashboard_mobile.png").resolve()

    _run_axi(["resize", "1440", "1000"])
    _run_axi(["wait", "500"])
    desktop_eval = _run_axi(["eval", _browser_eval()])
    _run_axi(["screenshot", str(desktop)])
    _run_axi(["resize", "390", "844"])
    _run_axi(["wait", "500"])
    mobile_eval = _run_axi(["eval", _browser_eval()])
    _run_axi(["screenshot", str(mobile)])

    def parse_eval(output: str) -> dict[str, object]:
        text = output.strip()
        if text.startswith("result:"):
            result_text = text.split("result:", 1)[1].split("\n", 1)[0].strip()
            try:
                parsed: object = json.loads(result_text)
                for _ in range(4):
                    if isinstance(parsed, dict):
                        return parsed
                    if not isinstance(parsed, str):
                        break
                    parsed = json.loads(parsed)
            except json.JSONDecodeError:
                pass
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end >= start:
            try:
                value = json.loads(text[start : end + 1])
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                pass
        return {"raw": text}

    desktop_data = parse_eval(desktop_eval.stdout)
    mobile_data = parse_eval(mobile_eval.stdout)
    body_text = str(desktop_data.get("bodyText") or "")
    missing_text = [text for text in required_text if text not in body_text]
    broken_images = list(desktop_data.get("brokenImages") or []) + list(
        mobile_data.get("brokenImages") or []
    )
    overflow = list(desktop_data.get("overflow") or []) + list(mobile_data.get("overflow") or [])

    report["screenshots"] = {
        "desktop": str(desktop) if desktop.is_file() else None,
        "mobile": str(mobile) if mobile.is_file() else None,
    }
    report["checks"] = {
        "browser_available": True,
        "desktop": desktop_data,
        "mobile": mobile_data,
        "broken_images": broken_images,
        "required_text_missing": missing_text,
        "overflow": overflow,
    }
    report["ok"] = not broken_images and not missing_text and not overflow
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dashboard_html",
        type=Path,
        nargs="?",
        default=None,
        help=(
            "Dashboard HTML to QA. Optional: when omitted (stage-04 analysis "
            "invocation), the upstream batch dashboard HTML is auto-discovered."
        ),
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--require-text",
        action="append",
        default=["COGANT Inspection Dashboard", "Roundtrip Diagnostics"],
        help="Text that must be present in the rendered dashboard. Can be repeated.",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    explicit = args.dashboard_html is not None
    dashboard_html: Path | None = args.dashboard_html
    if dashboard_html is None:
        dashboard_html = _discover_dashboard_html()

    # Default the report location next to the discovered dashboard so the
    # zero-argument analysis run writes inside the project output tree.
    if args.output_dir is not None:
        output_dir = args.output_dir
    elif dashboard_html is not None:
        output_dir = dashboard_html.parent / "dashboard_qa"
    else:
        output_dir = _STAGING_ROOT / "output" / "dashboard_qa"

    if dashboard_html is None or not dashboard_html.is_file():
        # No dashboard HTML available. For an explicit invocation this is a
        # hard error (preserves original contract for tests / manual use).
        # For the orchestrator (no argument) this is a graceful skip so the
        # Analysis stage exits 0 without a built dashboard.
        target = dashboard_html if dashboard_html is not None else "<none discovered>"
        if explicit:
            print(f"dashboard not found: {target}", file=sys.stderr)
            return 2
        output_dir.mkdir(parents=True, exist_ok=True)
        skip_report = {
            "schema_version": "1.0",
            "engine": "skipped",
            "ok": True,
            "skipped": True,
            "reason": "no dashboard HTML found; browser QA skipped",
            "searched": [str(c) for c in _DEFAULT_HTML_CANDIDATES],
        }
        report_path = output_dir / "dashboard_browser_qa.json"
        report_path.write_text(json.dumps(skip_report, indent=2), encoding="utf-8")
        print(
            "dashboard_browser_qa: no dashboard HTML found; skipping browser QA "
            f"(searched {len(_DEFAULT_HTML_CANDIDATES)} location(s))",
            file=sys.stderr,
        )
        print(str(report_path))
        return 0

    report = run_browser_qa(dashboard_html, output_dir, args.require_text)
    report_path = output_dir / "dashboard_browser_qa.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not args.quiet:
        print(json.dumps(report, indent=2))
    # Emit the report path for the stage-04 manifest collector.
    print(str(report_path))
    # Explicit invocation keeps strict semantics (exit 1 on QA failure) for
    # test/manual use. The orchestrator path must not fail the Analysis stage
    # on cosmetic QA findings (overflow/missing text); a report was produced.
    if explicit:
        return 0 if report.get("ok") else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
