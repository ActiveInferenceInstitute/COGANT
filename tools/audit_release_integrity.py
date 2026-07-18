#!/usr/bin/env python3
"""Audit package provenance, API schema, dependency boundaries, and wheels.

This is a local, network-free release audit.  It checks the source metadata
that can be verified without trusting a package index, emits a small SBOM-like
report from the pinned project declarations, validates the generated FastAPI
OpenAPI contract, and (when a wheel is available) verifies every hash in its
``RECORD`` file.

The audit deliberately does not claim that a single wheel proves reproducible
builds.  ``--check-wheel-reproducibility`` performs two clean local builds and
compares their bytes; the release gate enables that stronger check.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import importlib.metadata as importlib_metadata
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
INNER = ROOT / "cogant"
INIT_PATH = INNER / "py" / "cogant" / "__init__.py"
INNER_PYPROJECT = INNER / "pyproject.toml"
ROOT_PYPROJECT = ROOT / "pyproject.toml"
LOCK_PATH = INNER / "uv.lock"
DEFAULT_WHEEL_DIR = Path("/tmp/cogant-wheelhouse")
REPORT_PATH = ROOT / "output" / "reports" / "release_integrity.json"


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _version_from_init() -> str | None:
    match = re.search(
        r'^__version__\s*=\s*["\']([^"\']+)["\']',
        INIT_PATH.read_text(),
        re.MULTILINE,
    )
    return match.group(1) if match else None


def _locked_version() -> str | None:
    data = _load_toml(LOCK_PATH)
    for package in data.get("package", []):
        if package.get("name") == "cogant":
            return str(package.get("version"))
    return None


def _dependency_names(specs: list[str]) -> set[str]:
    names: set[str] = set()
    for spec in specs:
        match = re.match(r"\s*([A-Za-z0-9_.-]+)", spec)
        if match:
            names.add(match.group(1).lower().replace("_", "-"))
    return names


def _normalise_name(name: str) -> str:
    return name.lower().replace("_", "-")


def _installed_licenses(name: str) -> list[str]:
    """Read license identifiers from local distribution metadata only."""
    try:
        metadata = importlib_metadata.metadata(name)
    except importlib_metadata.PackageNotFoundError:
        return ["UNKNOWN"]
    values = [str(value).strip() for value in metadata.get_all("License") or [] if str(value).strip()]
    for classifier in metadata.get_all("Classifier") or []:
        prefix = "License :: "
        if str(classifier).startswith(prefix):
            values.append(str(classifier)[len(prefix) :].replace(" :: ", "-"))
    deduplicated = sorted(set(values))
    return deduplicated or ["UNKNOWN"]


def _build_sbom(
    project: dict[str, Any], optional: dict[str, list[str]]
) -> tuple[dict[str, Any], list[str]]:
    """Build a network-free CycloneDX-shaped inventory from ``uv.lock``."""
    lock = _load_toml(LOCK_PATH)
    direct = {_normalise_name(name) for name in _dependency_names(project.get("dependencies", []))}
    optional_names = {
        _normalise_name(name)
        for specs in optional.values()
        for name in _dependency_names(specs)
    }
    components: list[dict[str, Any]] = []
    issues: list[str] = []
    for package in lock.get("package", []):
        if not isinstance(package, dict) or not package.get("name"):
            continue
        name = str(package["name"])
        version = str(package.get("version", ""))
        normalized = _normalise_name(name)
        source = package.get("source", {})
        source = source if isinstance(source, dict) else {}
        if "registry" in source:
            purl = f"pkg:pypi/{quote(normalized)}@{quote(version)}"
        elif "git" in source:
            purl = f"pkg:github/{quote(str(source['git']).split('/')[-2])}/{quote(str(source['git']).split('/')[-1])}@{quote(version)}"
        else:
            purl = f"pkg:pypi/{quote(normalized)}@{quote(version)}"
        hashes: list[dict[str, str]] = []
        for artifact_key in ("sdist", "wheels"):
            artifacts = package.get(artifact_key, [])
            if isinstance(artifacts, dict):
                artifacts = [artifacts]
            if isinstance(artifacts, list):
                for artifact in artifacts[:1]:
                    if isinstance(artifact, dict) and artifact.get("hash", "").startswith("sha256:"):
                        hashes.append({"alg": "SHA-256", "content": str(artifact["hash"])[7:]})
        component: dict[str, Any] = {
            "type": "library",
            "bom-ref": purl,
            "name": name,
            "version": version,
            "purl": purl,
            "scope": "required" if normalized in direct else "optional" if normalized in optional_names else "optional",
            "licenses": [{"license": {"name": license_name}} for license_name in _installed_licenses(name)],
            "properties": [
                {"name": "cogant.lock.source", "value": json.dumps(source, sort_keys=True)},
            ],
        }
        if hashes:
            component["hashes"] = hashes
        components.append(component)

    upstream_specs = optional.get("upstream", [])
    upstream_spec = next(
        (spec for spec in upstream_specs if "generalized-notation-notation" in spec.lower()),
        None,
    )
    upstream_pin = re.search(r"@([0-9a-f]{40})(?:$|[?#])", upstream_spec or "")
    upstream_lock = next(
        (
            package
            for package in lock.get("package", [])
            if isinstance(package, dict)
            and _normalise_name(str(package.get("name", ""))) == "generalized-notation-notation"
        ),
        None,
    )
    lock_source = (upstream_lock or {}).get("source", {}) if isinstance(upstream_lock, dict) else {}
    lock_pin = re.search(r"#([0-9a-f]{40})$", str(lock_source.get("git", ""))) if isinstance(lock_source, dict) else None
    if upstream_spec and not upstream_pin:
        issues.append("optional upstream dependency is not pinned to a full commit")
    if upstream_spec and upstream_pin and (not lock_pin or lock_pin.group(1) != upstream_pin.group(1)):
        issues.append("optional upstream lock source does not match the pyproject commit pin")

    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:cogant-{project.get('name', 'package')}-{project.get('version', 'unknown')}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": project.get("name"),
                "version": project.get("version"),
            },
            "properties": [
                {"name": "cogant.lockfile", "value": str(LOCK_PATH.relative_to(ROOT))},
                {"name": "cogant.network_free", "value": "true"},
            ],
        },
        "components": sorted(components, key=lambda item: (str(item["name"]), str(item["version"]))),
    }
    return sbom, issues


def _source_report() -> tuple[dict[str, Any], list[str], dict[str, Any]]:
    inner = _load_toml(INNER_PYPROJECT)
    root = _load_toml(ROOT_PYPROJECT)
    project = inner.get("project", {})
    root_project = root.get("project", {})
    versions = {
        "inner_pyproject": str(project.get("version", "")),
        "root_shell": str(root_project.get("version", "")),
        "package_init": _version_from_init() or "",
        "uv_lock": _locked_version() or "",
    }
    issues: list[str] = []
    if len(set(versions.values())) != 1 or not next(iter(versions.values()), ""):
        issues.append(f"version mismatch: {versions}")

    dependencies = [str(value) for value in project.get("dependencies", [])]
    optional = {
        str(extra): [str(value) for value in values]
        for extra, values in project.get("optional-dependencies", {}).items()
    }
    all_names = _dependency_names(optional.get("all", []))
    upstream_names = _dependency_names(optional.get("upstream", []))
    leaked_upstream = sorted(all_names & upstream_names)
    if leaked_upstream:
        issues.append("optional upstream dependency leaked into all extra: " + ", ".join(leaked_upstream))

    license_path = ROOT / "LICENSE"
    if not license_path.exists():
        issues.append(f"missing package license: {license_path}")

    sbom, sbom_issues = _build_sbom(project, optional)
    issues.extend(sbom_issues)
    report = {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "package": {
            "name": project.get("name"),
            "version": versions["inner_pyproject"],
            "license": project.get("license"),
            "license_file": str(license_path.relative_to(ROOT)),
            "versions": versions,
        },
        "runtime_dependencies": dependencies,
        "optional_dependencies": optional,
        "provenance": {
            "lockfile": str(LOCK_PATH.relative_to(ROOT)),
            "upstream_extra": "upstream",
            "upstream_isolated_from_all": not bool(leaked_upstream),
        },
        "sbom": {
            "format": sbom["bomFormat"],
            "spec_version": sbom["specVersion"],
            "component_count": len(sbom["components"]),
        },
    }
    return report, issues, sbom


def _openapi_report() -> tuple[dict[str, Any], list[str]]:
    issues: list[str] = []
    try:
        from cogant.server.app import create_app

        with tempfile.TemporaryDirectory(prefix="cogant-release-api-") as temp:
            app = create_app(workspace_root=temp)
            schema = app.openapi()
        paths = schema.get("paths", {})
        versioned = sorted(path for path in paths if path.startswith("/api/v1/"))
        if not versioned:
            issues.append("OpenAPI schema has no /api/v1/ routes")
        for path in versioned:
            for method, operation in paths[path].items():
                if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                    continue
                if not operation.get("responses"):
                    issues.append(f"OpenAPI operation has no responses: {method.upper()} {path}")
                if method.lower() == "post" and "requestBody" not in operation:
                    issues.append(f"POST operation has no request body schema: {path}")
        report = {
            "title": schema.get("info", {}).get("title"),
            "version": schema.get("info", {}).get("version"),
            "versioned_paths": versioned,
            "operation_count": sum(
                1
                for path in paths.values()
                for method in path
                if method.lower() in {"get", "post", "put", "patch", "delete"}
            ),
        }
        return report, issues
    except Exception as exc:  # pragma: no cover - exercised by minimal installs
        return {}, [f"OpenAPI contract unavailable: {type(exc).__name__}: {exc}"]


def _record_digest(data: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode("ascii").rstrip("=")
    return f"sha256={digest}"


def _verify_wheel(path: Path) -> tuple[dict[str, Any], list[str]]:
    issues: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        metadata_names = sorted(name for name in names if name.endswith(".dist-info/METADATA"))
        record_names = sorted(name for name in names if name.endswith(".dist-info/RECORD"))
        if len(metadata_names) != 1:
            issues.append(f"expected one wheel METADATA file, found {metadata_names}")
        if len(record_names) != 1:
            issues.append(f"expected one wheel RECORD file, found {record_names}")
        metadata = archive.read(metadata_names[0]).decode("utf-8", errors="replace") if metadata_names else ""
        version_match = re.search(r"^Version:\s*(.+)$", metadata, re.MULTILINE)
        source_version = _version_from_init() or ""
        if not version_match or version_match.group(1).strip() != source_version:
            issues.append("wheel metadata version does not match source package version")

        checked = 0
        for row in csv.reader(io.StringIO(archive.read(record_names[0]).decode("utf-8"))) if record_names else []:
            if len(row) != 3:
                issues.append(f"malformed RECORD row: {row!r}")
                continue
            name, digest, size = row
            if name.endswith(".dist-info/RECORD"):
                continue
            if name not in names:
                issues.append(f"RECORD names missing wheel member: {name}")
                continue
            payload = archive.read(name)
            if digest and digest != _record_digest(payload):
                issues.append(f"RECORD digest mismatch: {name}")
            if size and int(size) != len(payload):
                issues.append(f"RECORD size mismatch: {name}")
            checked += 1
        report = {
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "metadata_version": version_match.group(1).strip() if version_match else None,
            "record_entries_checked": checked,
            "members": len(names),
        }
    return report, issues


def _find_wheel(explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit).expanduser().resolve()
    candidates = sorted(DEFAULT_WHEEL_DIR.glob("cogant-*.whl"), key=lambda path: path.stat().st_mtime)
    return candidates[-1] if candidates else None


def _reproducibility_report() -> tuple[dict[str, Any], list[str]]:
    issues: list[str] = []
    build_environment = {**os.environ, "SOURCE_DATE_EPOCH": "0"}
    with tempfile.TemporaryDirectory(prefix="cogant-wheel-a-") as first, tempfile.TemporaryDirectory(
        prefix="cogant-wheel-b-"
    ) as second:
        for destination in (first, second):
            result = subprocess.run(
                ["uv", "build", "--wheel", "--out-dir", destination],
                cwd=INNER,
                capture_output=True,
                text=True,
                env=build_environment,
                check=False,
            )
            if result.returncode != 0:
                return {}, [f"reproducible wheel build failed: {result.stderr[-500:]}"]
        first_wheel = next(Path(first).glob("*.whl"), None)
        second_wheel = next(Path(second).glob("*.whl"), None)
        if first_wheel is None or second_wheel is None:
            return {}, ["reproducible wheel build did not emit a wheel"]
        first_hash = hashlib.sha256(first_wheel.read_bytes()).hexdigest()
        second_hash = hashlib.sha256(second_wheel.read_bytes()).hexdigest()
        if first_hash != second_hash:
            issues.append("two clean wheel builds differ byte-for-byte")
        return {"first_sha256": first_hash, "second_sha256": second_hash, "byte_identical": first_hash == second_hash}, issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", help="wheel to validate; defaults to the latest /tmp/cogant-wheelhouse wheel")
    parser.add_argument("--require-wheel", action="store_true", help="fail if no wheel is available")
    parser.add_argument("--check-wheel-reproducibility", action="store_true", help="build two wheels and compare bytes")
    parser.add_argument("--no-openapi", action="store_true", help="skip the optional FastAPI OpenAPI check")
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)

    report, issues, sbom = _source_report()
    if not args.no_openapi:
        report["openapi"], openapi_issues = _openapi_report()
        issues.extend(openapi_issues)

    wheel = _find_wheel(args.wheel)
    if wheel is None:
        report["wheel"] = None
        if args.require_wheel:
            issues.append("no wheel available for release integrity validation")
    elif not wheel.exists():
        report["wheel"] = None
        issues.append(f"wheel does not exist: {wheel}")
    else:
        report["wheel"], wheel_issues = _verify_wheel(wheel)
        issues.extend(wheel_issues)

    if args.check_wheel_reproducibility:
        report["reproducibility"], reproducibility_issues = _reproducibility_report()
        issues.extend(reproducibility_issues)
    else:
        report["reproducibility"] = {"checked": False}

    report["status"] = "passed" if not issues else "failed"
    report["issues"] = issues
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sbom_path = args.output.with_name("cogant-sbom.cdx.json")
    sbom_path.write_text(json.dumps(sbom, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report["sbom"]["path"] = str(sbom_path.relative_to(ROOT))
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"audit_release_integrity: {report['status']} ({args.output})")
    for issue in issues:
        print(f"- {issue}", file=sys.stderr)
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
