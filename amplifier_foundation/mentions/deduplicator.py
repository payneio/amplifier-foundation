"""Content deduplication for @mentioned files."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .models import ContextFile


class ContentDeduplicator:
    """Deduplicate content by SHA-256 hash.

    Tracks files that have been added and returns only unique content.
    Useful when loading recursive @mentions to avoid including
    the same content multiple times.
    """

    def __init__(self) -> None:
        """Initialize deduplicator."""
        self._seen_hashes: set[str] = set()
        self._files: list[ContextFile] = []

    def add_file(self, path: Path, content: str) -> bool:
        """Add a file if its content hasn't been seen.

        Args:
            path: Path to the file.
            content: File content.

        Returns:
            True if file was added (new content), False if duplicate.
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        if content_hash in self._seen_hashes:
            return False

        self._seen_hashes.add(content_hash)
        self._files.append(ContextFile(path=path, content=content, content_hash=content_hash))
        return True

    def get_unique_files(self) -> list[ContextFile]:
        """Get list of unique files added.

        Returns:
            List of ContextFile instances with unique content.
        """
        return list(self._files)

    def is_seen(self, content: str) -> bool:
        """Check if content has already been seen.

        Args:
            content: Content to check.

        Returns:
            True if content hash has been seen.
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        return content_hash in self._seen_hashes

    def get_known_hashes(self) -> set[str]:
        """Return hashes currently tracked by the deduplicator.

        Returns:
            Set of SHA-256 hash strings for all seen content.
        """
        return set(self._seen_hashes)
