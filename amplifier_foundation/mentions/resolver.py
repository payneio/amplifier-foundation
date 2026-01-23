"""Base @mention resolver implementation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from amplifier_foundation.bundle import Bundle


class BaseMentionResolver:
    """Base implementation of MentionResolverProtocol.

    Supports patterns:
    - @bundle-name:context-name - From bundle's context namespace
    - @path - Relative to current working directory (CWD)
    - @~/path - Relative to user's home directory
    - @~user/path - Relative to another user's home directory

    Apps extend this class to add shortcuts like @user:, @project:.
    """

    def __init__(
        self,
        bundles: dict[str, Bundle] | None = None,
        base_path: Path | None = None,  # Kept for API compatibility; not used for @path
    ) -> None:
        """Initialize resolver.

        Args:
            bundles: Dict mapping bundle names to Bundle instances.
            base_path: Unused (kept for API compatibility). Relative @path
                       mentions always resolve against CWD.
        """
        self.bundles = bundles or {}
        self.base_path = base_path or Path.cwd()  # Stored but not used for @path

    def resolve(self, mention: str) -> Path | None:
        """Resolve an @mention to a file path.

        Args:
            mention: The mention string (including @ prefix).

        Returns:
            Path to the resolved file, or None if not found.
        """
        if not mention.startswith("@"):
            return None

        mention_body = mention[1:]  # Remove @ prefix

        # Pattern 1: @bundle-name:context-name
        if ":" in mention_body:
            namespace, name = mention_body.split(":", 1)
            if bundle := self.bundles.get(namespace):
                return bundle.resolve_context_path(name)
            return None

        # Pattern 2: @path (relative to CWD, or home directory for ~ paths)
        if mention_body.startswith("~"):
            # Home directory path (~/... or ~user/...)
            path = Path(mention_body).expanduser()
            path_md = Path(f"{mention_body}.md").expanduser()
        else:
            # Relative to current working directory
            cwd = Path.cwd()
            path = cwd / mention_body
            path_md = cwd / f"{mention_body}.md"

        if path.exists():
            return path

        # Try with .md extension
        if path_md.exists():
            return path_md

        return None

    def register_bundle(self, name: str, bundle: Bundle) -> None:
        """Register a bundle for namespace resolution.

        Args:
            name: Bundle name (namespace for @mentions).
            bundle: Bundle instance.
        """
        self.bundles[name] = bundle
