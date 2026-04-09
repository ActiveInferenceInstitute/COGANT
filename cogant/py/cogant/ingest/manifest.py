"""Manifest parsing for dependency extraction and metadata."""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import tomllib
except ImportError:
    # Python < 3.11: provide minimal TOML parsing
    def _parse_toml(content: str) -> Dict[str, Any]:
        """Minimal TOML parser for pyproject.toml (handles common patterns)."""
        result = {}
        current_section = None
        current_dict = result

        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Section headers [section]
            if line.startswith("["):
                section = line.strip("[]").strip()
                current_section = section
                # Handle nested sections like [tool.poetry.dev-dependencies]
                parts = section.split(".")
                current_dict = result
                for part in parts[:-1]:
                    if part not in current_dict:
                        current_dict[part] = {}
                    current_dict = current_dict[part]
                if section not in result:
                    result[section] = {}
                current_dict = result[section]
                continue

            # Key-value pairs
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Parse value
                if value.startswith("["):
                    # Array
                    value = value.strip("[]").split(",")
                    value = [v.strip().strip("\"'") for v in value]
                elif value.startswith("{"):
                    # Dict (simplified)
                    pass
                elif value.startswith('"') or value.startswith("'"):
                    value = value.strip('"\'')
                elif value.lower() in ("true", "false"):
                    value = value.lower() == "true"
                else:
                    try:
                        value = int(value)
                    except ValueError:
                        try:
                            value = float(value)
                        except ValueError:
                            pass

                current_dict[key] = value

        return result

    class _TomlLib:
        """Tiny ``tomllib`` shim used on Python versions that lack it."""

        @staticmethod
        def load(f):
            """Read a TOML file and return it as a nested dict."""
            content = f.read()
            if isinstance(content, bytes):
                content = content.decode("utf-8")
            return _parse_toml(content)

    tomllib = _TomlLib()  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class Dependency:
    """A package dependency."""

    name: str
    """Package name."""

    version: Optional[str] = None
    """Version specifier (e.g., ">=1.0,<2.0")."""

    is_dev: bool = False
    """Whether this is a development dependency."""

    is_local: bool = False
    """Whether this is a local/relative dependency."""


class ManifestParser:
    """Parse package manifests to extract dependencies and metadata."""

    def parse(self, path: Path) -> Tuple[Dict, List[Dependency]]:
        """Parse a manifest file, automatically detecting type.

        Args:
            path: Path to manifest file (pyproject.toml, setup.py, package.json, Cargo.toml, requirements.txt)

        Returns:
            Tuple of (metadata dict, dependencies list)
        """
        path = Path(path)
        filename = path.name.lower()

        if filename == "pyproject.toml":
            return self.parse_pyproject_toml(path)
        elif filename == "setup.py":
            return self.parse_setup_py(path)
        elif filename == "package.json":
            return self.parse_package_json(path)
        elif filename == "cargo.toml":
            return self.parse_cargo_toml(path)
        elif filename == "requirements.txt":
            # requirements.txt has different return type, wrap it
            deps = self.parse_requirements_txt(path)
            return {}, deps
        else:
            raise ValueError(f"Unknown manifest file type: {filename}")

    def parse_setup_py(self, path: Path) -> Tuple[Dict, List[Dependency]]:
        """Parse Python setup.py file.

        Args:
            path: Path to setup.py

        Returns:
            Tuple of (metadata dict, dependencies list)
        """
        metadata = {}
        dependencies = []

        try:
            with open(path, "r") as f:
                content = f.read()

            # Extract setup() call arguments using regex
            # This is a simple approach for common patterns

            # Extract name
            name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
            if name_match:
                metadata["name"] = name_match.group(1)

            # Extract version
            version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            if version_match:
                metadata["version"] = version_match.group(1)

            # Extract description
            desc_match = re.search(
                r'description\s*=\s*["\']([^"\']+)["\']', content
            )
            if desc_match:
                metadata["description"] = desc_match.group(1)

            # Extract install_requires
            install_match = re.search(
                r"install_requires\s*=\s*\[(.*?)\]", content, re.DOTALL
            )
            if install_match:
                deps_str = install_match.group(1)
                dependencies.extend(self._parse_requirements_string(deps_str))

            # Extract extras_require (dev dependencies)
            extras_match = re.search(
                r"extras_require\s*=\s*\{(.*?)\}", content, re.DOTALL
            )
            if extras_match:
                extras_str = extras_match.group(1)
                # Parse dev extras (common names: dev, test, develop)
                for pattern in ["dev", "test", "develop"]:
                    dev_match = re.search(
                        rf'["\']?{pattern}["\']?\s*:\s*\[(.*?)\]',
                        extras_str,
                        re.DOTALL,
                    )
                    if dev_match:
                        dev_deps_str = dev_match.group(1)
                        dev_deps = self._parse_requirements_string(dev_deps_str)
                        for dep in dev_deps:
                            dep.is_dev = True
                        dependencies.extend(dev_deps)

        except Exception as e:
            logger.warning(f"Failed to parse setup.py at {path}: {e}")

        return metadata, dependencies

    def parse_pyproject_toml(self, path: Path) -> Tuple[Dict, List[Dependency]]:
        """Parse Python pyproject.toml file.

        Args:
            path: Path to pyproject.toml

        Returns:
            Tuple of (metadata dict, dependencies list)
        """
        metadata = {}
        dependencies = []

        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)

            # Extract project metadata
            if "project" in data:
                project = data["project"]
                metadata.update({
                    "name": project.get("name"),
                    "version": project.get("version"),
                    "description": project.get("description"),
                })

                # Extract dependencies
                if "dependencies" in project:
                    dependencies.extend(
                        self._parse_requirement_list(project["dependencies"])
                    )

                # Extract optional dependencies (dev)
                if "optional-dependencies" in project:
                    for extra_type, extra_deps in project[
                        "optional-dependencies"
                    ].items():
                        is_dev = extra_type in ["dev", "test", "develop"]
                        for dep in self._parse_requirement_list(extra_deps):
                            dep.is_dev = is_dev
                            dependencies.append(dep)

        except Exception as e:
            logger.warning(f"Failed to parse pyproject.toml at {path}: {e}")

        return metadata, dependencies

    def parse_requirements_txt(self, path: Path) -> List[Dependency]:
        """Parse Python requirements.txt file.

        Args:
            path: Path to requirements.txt

        Returns:
            List of dependencies
        """
        dependencies = []

        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    dep = self._parse_requirement_line(line)
                    if dep:
                        dependencies.append(dep)

        except Exception as e:
            logger.warning(f"Failed to parse requirements.txt at {path}: {e}")

        return dependencies

    def parse_package_json(self, path: Path) -> Tuple[Dict, List[Dependency]]:
        """Parse Node.js package.json file.

        Args:
            path: Path to package.json

        Returns:
            Tuple of (metadata dict, dependencies list)
        """
        metadata = {}
        dependencies = []

        try:
            with open(path, "r") as f:
                data = json.load(f)

            metadata = {
                "name": data.get("name"),
                "version": data.get("version"),
                "description": data.get("description"),
            }

            # Extract dependencies
            if "dependencies" in data:
                for name, version in data["dependencies"].items():
                    dependencies.append(
                        Dependency(name=name, version=version, is_dev=False)
                    )

            # Extract devDependencies
            if "devDependencies" in data:
                for name, version in data["devDependencies"].items():
                    dependencies.append(
                        Dependency(name=name, version=version, is_dev=True)
                    )

        except Exception as e:
            logger.warning(f"Failed to parse package.json at {path}: {e}")

        return metadata, dependencies

    def parse_cargo_toml(self, path: Path) -> Tuple[Dict, List[Dependency]]:
        """Parse Rust Cargo.toml file.

        Args:
            path: Path to Cargo.toml

        Returns:
            Tuple of (metadata dict, dependencies list)
        """
        metadata = {}
        dependencies = []

        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)

            # Extract package metadata
            if "package" in data:
                package = data["package"]
                metadata = {
                    "name": package.get("name"),
                    "version": package.get("version"),
                    "description": package.get("description"),
                }

            # Extract dependencies
            if "dependencies" in data:
                for name, spec in data["dependencies"].items():
                    version = None
                    if isinstance(spec, dict):
                        version = spec.get("version")
                    elif isinstance(spec, str):
                        version = spec
                    dependencies.append(
                        Dependency(name=name, version=version, is_dev=False)
                    )

            # Extract dev-dependencies
            if "dev-dependencies" in data:
                for name, spec in data["dev-dependencies"].items():
                    version = None
                    if isinstance(spec, dict):
                        version = spec.get("version")
                    elif isinstance(spec, str):
                        version = spec
                    dependencies.append(
                        Dependency(name=name, version=version, is_dev=True)
                    )

        except Exception as e:
            logger.warning(f"Failed to parse Cargo.toml at {path}: {e}")

        return metadata, dependencies

    @staticmethod
    def _parse_requirements_string(req_str: str) -> List[Dependency]:
        """Parse requirements from a string (setup.py format).

        Args:
            req_str: Requirements string with comma or list separators.

        Returns:
            List of dependencies.
        """
        dependencies = []

        # Split by comma and parse each requirement
        for line in req_str.split(","):
            line = line.strip()
            if not line:
                continue

            # Remove quotes
            line = line.strip("'\"")

            dep = ManifestParser._parse_requirement_line(line)
            if dep:
                dependencies.append(dep)

        return dependencies

    @staticmethod
    def _parse_requirement_list(reqs: List[str]) -> List[Dependency]:
        """Parse requirements from a list.

        Args:
            reqs: List of requirement strings.

        Returns:
            List of dependencies.
        """
        dependencies = []
        for req in reqs:
            dep = ManifestParser._parse_requirement_line(req)
            if dep:
                dependencies.append(dep)
        return dependencies

    @staticmethod
    def _parse_requirement_line(line: str) -> Optional[Dependency]:
        """Parse a single requirement line.

        Args:
            line: Requirement line (e.g., "requests>=2.0,<3.0").

        Returns:
            Dependency or None if could not parse.
        """
        line = line.strip()
        if not line:
            return None

        # Handle path-based dependencies
        if line.startswith("-e"):
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                if parts[1].startswith(("file:", ".")):
                    return Dependency(
                        name=parts[1].split("/")[-1], is_local=True
                    )

        # Parse name and version specifier
        # Handle common version specifiers: ==, >=, <=, >, <, ~=, !=
        match = re.match(r"^([a-zA-Z0-9._-]+)(.*?)$", line)

        if match:
            name = match.group(1).strip()
            version = match.group(2).strip() if match.group(2) else None
            return Dependency(name=name, version=version)

        return None
