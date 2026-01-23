"""@mention extraction from text."""

from __future__ import annotations

import re


def parse_mentions(text: str) -> list[str]:
    """Extract @mentions from text, excluding code blocks.

    Finds patterns like:
    - @bundle:context-name
    - @path/to/file
    - @./relative/path

    Excludes mentions inside:
    - Inline code (`...`)
    - Fenced code blocks (```...```)

    Args:
        text: Text to extract mentions from.

    Returns:
        List of unique mentions (including @ prefix).
    """
    # Remove code blocks first
    text_without_code = _remove_code_blocks(text)

    # Find @mentions
    # Pattern: @ followed by word chars, colons, slashes, dots, hyphens, tildes
    # But not email addresses (no @ followed by domain pattern)
    pattern = r"@(?![a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})([a-zA-Z0-9_:./\~-]+)"

    matches = re.findall(pattern, text_without_code)

    # Return unique mentions with @ prefix, preserving order
    seen: set[str] = set()
    result: list[str] = []
    for match in matches:
        mention = f"@{match}"
        if mention not in seen:
            seen.add(mention)
            result.append(mention)

    return result


def _remove_code_blocks(text: str) -> str:
    """Remove code blocks from text.

    Removes:
    - Fenced code blocks (```...```)
    - Inline code (`...`)
    """
    # Remove fenced code blocks (including language identifier)
    text = re.sub(r"```[^\n]*\n.*?```", "", text, flags=re.DOTALL)

    # Remove inline code
    text = re.sub(r"`[^`]+`", "", text)

    return text
