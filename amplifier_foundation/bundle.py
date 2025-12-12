"""Bundle dataclass - the core composable unit."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any

from amplifier_foundation.dicts.merge import deep_merge
from amplifier_foundation.dicts.merge import merge_module_lists
from amplifier_foundation.paths.construction import construct_context_path


@dataclass
class Bundle:
    """Composable unit containing mount plan config and resources.

    Bundles replace both "profiles" (mount plan config) and "collections"
    (resource repositories). They produce mount plans for AmplifierSession.

    Attributes:
        name: Bundle name (namespace for @mentions).
        version: Bundle version string.
        description: Optional description.
        includes: List of bundle URIs to include.
        session: Session config (orchestrator, context).
        providers: List of provider configs.
        tools: List of tool configs.
        hooks: List of hook configs.
        agents: Dict mapping agent name to definition.
        context: Dict mapping context name to file path.
        instruction: System instruction from markdown body.
        base_path: Path to bundle root directory.
    """

    # Metadata
    name: str
    version: str = "1.0.0"
    description: str = ""
    includes: list[str] = field(default_factory=list)

    # Mount plan sections
    session: dict[str, Any] = field(default_factory=dict)
    providers: list[dict[str, Any]] = field(default_factory=list)
    tools: list[dict[str, Any]] = field(default_factory=list)
    hooks: list[dict[str, Any]] = field(default_factory=list)

    # Resources
    agents: dict[str, dict[str, Any]] = field(default_factory=dict)
    context: dict[str, Path] = field(default_factory=dict)
    instruction: str | None = None

    # Internal
    base_path: Path | None = None

    def compose(self, *others: Bundle) -> Bundle:
        """Compose this bundle with others (later overrides earlier).

        Creates a new Bundle with merged configuration. For each section:
        - session: deep merge (later overrides)
        - providers/tools/hooks: merge by module ID
        - agents/context: later overrides earlier
        - instruction: later replaces earlier

        Args:
            others: Bundles to compose with.

        Returns:
            New Bundle with merged configuration.
        """
        result = Bundle(
            name=self.name,
            version=self.version,
            description=self.description,
            includes=list(self.includes),
            session=dict(self.session),
            providers=list(self.providers),
            tools=list(self.tools),
            hooks=list(self.hooks),
            agents=dict(self.agents),
            context=dict(self.context),
            instruction=self.instruction,
            base_path=self.base_path,
        )

        for other in others:
            # Metadata: later wins
            result.name = other.name or result.name
            result.version = other.version or result.version
            if other.description:
                result.description = other.description

            # Session: deep merge
            result.session = deep_merge(result.session, other.session)

            # Module lists: merge by module ID
            result.providers = merge_module_lists(result.providers, other.providers)
            result.tools = merge_module_lists(result.tools, other.tools)
            result.hooks = merge_module_lists(result.hooks, other.hooks)

            # Resources: later overrides
            result.agents.update(other.agents)
            result.context.update(other.context)

            # Instruction: later replaces
            if other.instruction:
                result.instruction = other.instruction

            # Base path: use other's if set
            if other.base_path:
                result.base_path = other.base_path

        return result

    def to_mount_plan(self) -> dict[str, Any]:
        """Compile to mount plan for AmplifierSession.

        Returns:
            Dict suitable for AmplifierSession.create().
        """
        mount_plan: dict[str, Any] = {}

        if self.session:
            mount_plan["session"] = dict(self.session)

        if self.providers:
            mount_plan["providers"] = list(self.providers)

        if self.tools:
            mount_plan["tools"] = list(self.tools)

        if self.hooks:
            mount_plan["hooks"] = list(self.hooks)

        # Agents go in mount plan for sub-session delegation
        if self.agents:
            mount_plan["agents"] = dict(self.agents)

        return mount_plan

    def resolve_context_path(self, name: str) -> Path | None:
        """Resolve context file by name.

        Args:
            name: Context name.

        Returns:
            Path to context file, or None if not found.
        """
        # Check registered context
        if name in self.context:
            return self.context[name]

        # Try constructing path from base
        if self.base_path:
            path = construct_context_path(self.base_path, name)
            if path.exists():
                return path

        return None

    def resolve_agent_path(self, name: str) -> Path | None:
        """Resolve agent file by name.

        Handles both namespaced and simple names:
        - "foundation:bug-hunter" -> strips prefix, looks for bug-hunter.md
        - "bug-hunter" -> looks for bug-hunter.md

        Args:
            name: Agent name (may include bundle prefix).

        Returns:
            Path to agent file, or None if not found.
        """
        if not self.base_path:
            return None

        # Strip bundle prefix if present (e.g., "foundation:bug-hunter" -> "bug-hunter")
        simple_name = name.split(":", 1)[-1] if ":" in name else name

        # Look in agents/ directory
        agent_path = self.base_path / "agents" / f"{simple_name}.md"
        if agent_path.exists():
            return agent_path

        return None

    def get_system_instruction(self) -> str | None:
        """Get the system instruction for this bundle.

        Returns:
            Instruction text, or None if not set.
        """
        return self.instruction

    @classmethod
    def from_dict(cls, data: dict[str, Any], base_path: Path | None = None) -> Bundle:
        """Create Bundle from parsed dict (from YAML/frontmatter).

        Args:
            data: Dict with bundle configuration.
            base_path: Path to bundle root directory.

        Returns:
            Bundle instance.
        """
        bundle_meta = data.get("bundle", {})

        return cls(
            name=bundle_meta.get("name", ""),
            version=bundle_meta.get("version", "1.0.0"),
            description=bundle_meta.get("description", ""),
            includes=data.get("includes", []),
            session=data.get("session", {}),
            providers=data.get("providers", []),
            tools=data.get("tools", []),
            hooks=data.get("hooks", []),
            agents=_parse_agents(data.get("agents", {}), base_path),
            context=_parse_context(data.get("context", {}), base_path),
            instruction=None,  # Set separately from markdown body
            base_path=base_path,
        )


def _parse_agents(agents_config: dict[str, Any], base_path: Path | None) -> dict[str, dict[str, Any]]:
    """Parse agents config section.

    Handles both include lists and direct definitions.
    """
    if not agents_config:
        return {}

    result: dict[str, dict[str, Any]] = {}

    # Handle include list
    if "include" in agents_config:
        for name in agents_config["include"]:
            result[name] = {"name": name}

    # Handle direct definitions
    for key, value in agents_config.items():
        if key != "include" and isinstance(value, dict):
            result[key] = value

    return result


def _parse_context(context_config: dict[str, Any], base_path: Path | None) -> dict[str, Path]:
    """Parse context config section.

    Handles both include lists and direct path mappings.
    Context names may have bundle prefix (e.g., "foundation:file.md") which
    should be stripped when constructing paths.
    """
    if not context_config:
        return {}

    result: dict[str, Path] = {}

    # Handle include list
    if "include" in context_config:
        for name in context_config["include"]:
            if base_path:
                # Strip bundle prefix if present (e.g., "foundation:file.md" -> "file.md")
                path_part = name.split(":", 1)[-1] if ":" in name else name
                result[name] = construct_context_path(base_path, path_part)

    # Handle direct path mappings
    for key, value in context_config.items():
        if key != "include" and isinstance(value, str):
            if base_path:
                result[key] = base_path / value
            else:
                result[key] = Path(value)

    return result
