"""Module activation for amplifier-foundation.

This module provides basic module resolution - downloading modules from URIs
and making them importable. This enables foundation to provide a turn-key
experience where bundles can be loaded and executed without additional libraries.

For advanced resolution strategies (layered resolution, settings-based overrides,
workspace conventions), see amplifier-module-resolution.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from amplifier_foundation.paths.resolution import get_amplifier_home
from amplifier_foundation.sources.resolver import SimpleSourceResolver

logger = logging.getLogger(__name__)


class ModuleActivator:
    """Activate modules by downloading and making them importable.

    This class handles the basic mechanism of:
    1. Downloading module source from git/file/http URIs
    2. Installing Python dependencies (via uv or pip)
    3. Adding module paths to sys.path for import

    Apps provide the policy (which modules to load, from where).
    This class provides the mechanism (how to load them).
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        install_deps: bool = True,
        base_path: Path | None = None,
    ) -> None:
        """Initialize module activator.

        Args:
            cache_dir: Directory for caching downloaded modules.
            install_deps: Whether to install Python dependencies.
            base_path: Base path for resolving relative module paths.
                       For bundles loaded from git, this should be the cloned
                       bundle's base_path so relative paths like ./modules/foo
                       resolve correctly.
        """
        self.cache_dir = cache_dir or get_amplifier_home() / "cache"
        self.install_deps = install_deps
        self._resolver = SimpleSourceResolver(cache_dir=self.cache_dir, base_path=base_path)
        self._activated: set[str] = set()

    async def activate(self, module_name: str, source_uri: str) -> Path:
        """Activate a module by downloading and making it importable.

        Args:
            module_name: Name of the module (e.g., "loop-streaming").
            source_uri: URI to download from (e.g., "git+https://...").

        Returns:
            Local path to the activated module.

        Raises:
            ModuleActivationError: If activation fails.
        """
        # Skip if already activated this session
        cache_key = f"{module_name}:{source_uri}"
        if cache_key in self._activated:
            resolved = await self._resolver.resolve(source_uri)
            return resolved.active_path

        # Download module source
        resolved = await self._resolver.resolve(source_uri)
        module_path = resolved.active_path

        # Install dependencies if requested
        if self.install_deps:
            await self._install_dependencies(module_path)

        # Add to sys.path if not already there
        path_str = str(module_path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

        self._activated.add(cache_key)
        return module_path

    async def activate_all(self, modules: list[dict]) -> dict[str, Path]:
        """Activate multiple modules.

        Args:
            modules: List of module specs with 'module' and 'source' keys.

        Returns:
            Dict mapping module names to their local paths.
        """
        results = {}
        for mod in modules:
            module_name = mod.get("module")
            source_uri = mod.get("source")

            if not module_name or not source_uri:
                continue

            path = await self.activate(module_name, source_uri)
            results[module_name] = path

        return results

    async def activate_bundle_package(self, bundle_path: Path) -> None:
        """Install a bundle's own Python package to enable internal imports.

        When a bundle contains both a Python package (pyproject.toml at root) and
        modules that import from that package, we need to install the bundle's
        package BEFORE activating modules. This enables patterns like:

            # In modules/tool-shadow/__init__.py
            from amplifier_bundle_shadow import ShadowManager

        where amplifier_bundle_shadow is the bundle's own package.

        Args:
            bundle_path: Path to bundle root directory containing pyproject.toml.

        Note:
            This is a no-op if the bundle has no pyproject.toml.
            Must be called BEFORE activate_all() for modules that need it.
        """
        if not bundle_path or not bundle_path.exists():
            return

        pyproject = bundle_path / "pyproject.toml"
        if not pyproject.exists():
            logger.debug(f"No pyproject.toml at {bundle_path}, skipping bundle package install")
            return

        logger.debug(f"Installing bundle package from {bundle_path}")
        await self._install_dependencies(bundle_path)

    async def _install_dependencies(self, module_path: Path) -> None:
        """Install Python dependencies for a module.

        Uses uv to install into the current Python environment. The --python flag
        ensures installation targets the correct environment even when run via
        `uv tool install` where there's no active virtualenv.

        Args:
            module_path: Path to the module directory.

        Raises:
            subprocess.CalledProcessError: If installation fails.
        """
        # Check for pyproject.toml or requirements.txt
        pyproject = module_path / "pyproject.toml"
        requirements = module_path / "requirements.txt"

        if pyproject.exists():
            try:
                subprocess.run(
                    [
                        "uv",
                        "pip",
                        "install",
                        "-e",
                        str(module_path),
                        "--python",
                        sys.executable,
                        "--quiet",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install module from {module_path}.\nstdout: {e.stdout}\nstderr: {e.stderr}")
                raise
            except FileNotFoundError:
                logger.error(
                    "uv is not installed. Please install uv: https://docs.astral.sh/uv/getting-started/installation/"
                )
                raise
        elif requirements.exists():
            try:
                subprocess.run(
                    [
                        "uv",
                        "pip",
                        "install",
                        "-r",
                        str(requirements),
                        "--python",
                        sys.executable,
                        "--quiet",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as e:
                logger.error(
                    f"Failed to install requirements from {requirements}.\nstdout: {e.stdout}\nstderr: {e.stderr}"
                )
                raise
            except FileNotFoundError:
                logger.error(
                    "uv is not installed. Please install uv: https://docs.astral.sh/uv/getting-started/installation/"
                )
                raise


class ModuleActivationError(Exception):
    """Raised when module activation fails."""

    pass
