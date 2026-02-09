"""
System prompt factory for dynamic @mention resolution.

This module provides the core factory creation used by both:
- PreparedBundle.create_session() for root sessions
- spawn_bundle() for child sessions
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Awaitable, Callable

if TYPE_CHECKING:
    from amplifier_foundation.bundle import Bundle


async def create_system_prompt_factory(
    bundle: Bundle,
    bundle_registry: dict[str, Bundle] | None = None,
    base_path: Path | None = None,
) -> Callable[[], Awaitable[str]]:
    """
    Create a factory that produces fresh system prompt content on each call.

    The factory re-reads context files and re-processes @mentions each time,
    enabling dynamic content like AGENTS.md to be picked up immediately when
    modified during a session.

    Args:
        bundle: Bundle containing instruction and context files.
        bundle_registry: Dict mapping namespace to Bundle for @mention resolution.
            Each Bundle should have base_path set for that namespace.
            If None, only local @mentions (relative to base_path) will resolve.
        base_path: Working directory for resolving local @mentions like @AGENTS.md.
            Falls back to bundle.base_path or cwd().

    Returns:
        Async callable that returns the system prompt string.

    Example:
        # For root sessions (PreparedBundle builds the registry)
        registry = prepared._build_bundles_for_resolver(bundle)
        factory = await create_system_prompt_factory(
            bundle=bundle,
            bundle_registry=registry,
            base_path=session_cwd,
        )

        # For spawned sessions
        registry = _build_bundle_registry(prepared, parent_session)
        factory = await create_system_prompt_factory(
            bundle=child_bundle,
            bundle_registry=registry,
            base_path=working_dir,
        )
    """
    from amplifier_foundation.mentions import (
        BaseMentionResolver,
        ContentDeduplicator,
        format_context_block,
        load_mentions,
    )

    # Determine base path for local @mentions
    effective_base_path = base_path or bundle.base_path or Path.cwd()

    # Capture state for closure
    captured_bundle = bundle
    captured_registry = bundle_registry or {}
    captured_base_path = effective_base_path

    async def factory() -> str:
        # Main instruction from bundle
        main_instruction = captured_bundle.instruction or ""

        # Create resolver for this invocation
        resolver = BaseMentionResolver(
            bundles=captured_registry,
            base_path=captured_base_path,
        )

        # Fresh deduplicator each call (files may have changed)
        deduplicator = ContentDeduplicator()

        # Build mention_to_path map for context block attribution
        # This includes BOTH bundle context files AND @mentions from instruction
        mention_to_path: dict[str, Path] = {}

        # 1. Bundle context files (from context: section)
        # Add to deduplicator and mention_to_path for unified formatting
        for context_name, context_path in captured_bundle.context.items():
            if context_path.exists():
                content = context_path.read_text(encoding="utf-8")
                # Add to deduplicator for content-based deduplication
                deduplicator.add_file(context_path, content)
                # Add to mention_to_path for attribution (context_name → path)
                mention_to_path[context_name] = context_path

        # 2. Resolve @mentions from main instruction (re-loads files each call)
        mention_results = await load_mentions(
            main_instruction,
            resolver=resolver,
            deduplicator=deduplicator,
        )

        # Add @mention results to mention_to_path for attribution
        for mr in mention_results:
            if mr.resolved_path:
                mention_to_path[mr.mention] = mr.resolved_path

        # 3. Format ALL context as XML blocks (bundle context + @mentions)
        # format_context_block uses deduplicator for unique content and
        # mention_to_path for attribution (showing name → resolved path)
        all_context = format_context_block(deduplicator, mention_to_path)

        # Final structure: main instruction FIRST, then all context files
        if all_context:
            return f"{main_instruction}\n\n---\n\n{all_context}"
        else:
            return main_instruction

    return factory
