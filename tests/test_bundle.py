"""Tests for Bundle class."""

from pathlib import Path
from tempfile import TemporaryDirectory

from amplifier_foundation.bundle import Bundle


class TestBundle:
    """Tests for Bundle dataclass."""

    def test_create_minimal(self) -> None:
        """Can create bundle with just name."""
        bundle = Bundle(name="test")
        assert bundle.name == "test"
        assert bundle.version == "1.0.0"
        assert bundle.providers == []
        assert bundle.tools == []
        assert bundle.hooks == []

    def test_from_dict_minimal(self) -> None:
        """Can create bundle from minimal dict."""
        data = {"bundle": {"name": "test"}}
        bundle = Bundle.from_dict(data)
        assert bundle.name == "test"

    def test_from_dict_full(self) -> None:
        """Can create bundle from full config dict."""
        data = {
            "bundle": {
                "name": "full-test",
                "version": "2.0.0",
                "description": "A full test bundle",
            },
            "session": {"orchestrator": "loop-basic"},
            "providers": [{"module": "provider-anthropic", "config": {"model": "test"}}],
            "tools": [{"module": "tool-bash"}],
            "hooks": [{"module": "hooks-logging"}],
            "includes": ["base-bundle"],
        }
        bundle = Bundle.from_dict(data)
        assert bundle.name == "full-test"
        assert bundle.version == "2.0.0"
        assert bundle.session == {"orchestrator": "loop-basic"}
        assert len(bundle.providers) == 1
        assert len(bundle.tools) == 1
        assert len(bundle.hooks) == 1
        assert bundle.includes == ["base-bundle"]


class TestBundleCompose:
    """Tests for Bundle.compose method."""

    def test_compose_empty_bundles(self) -> None:
        """Composing empty bundles returns empty bundle."""
        base = Bundle(name="base")
        child = Bundle(name="child")
        result = base.compose(child)
        assert result.name == "child"
        assert result.providers == []

    def test_compose_session_deep_merge(self) -> None:
        """Session configs are deep merged."""
        base = Bundle(name="base", session={"orchestrator": "loop-basic", "context": "simple"})
        child = Bundle(name="child", session={"orchestrator": "loop-streaming"})
        result = base.compose(child)
        assert result.session["orchestrator"] == "loop-streaming"
        assert result.session["context"] == "simple"

    def test_compose_providers_merge_by_module(self) -> None:
        """Providers are merged by module ID."""
        base = Bundle(
            name="base",
            providers=[{"module": "provider-a", "config": {"x": 1, "y": 2}}],
        )
        child = Bundle(
            name="child",
            providers=[{"module": "provider-a", "config": {"y": 3, "z": 4}}],
        )
        result = base.compose(child)
        assert len(result.providers) == 1
        assert result.providers[0]["config"] == {"x": 1, "y": 3, "z": 4}

    def test_compose_multiple_bundles(self) -> None:
        """Can compose multiple bundles at once."""
        base = Bundle(name="base", providers=[{"module": "a"}])
        mid = Bundle(name="mid", providers=[{"module": "b"}])
        top = Bundle(name="top", providers=[{"module": "c"}])
        result = base.compose(mid, top)
        assert result.name == "top"
        modules = [p["module"] for p in result.providers]
        assert set(modules) == {"a", "b", "c"}

    def test_compose_instruction_replaced(self) -> None:
        """Later instruction replaces earlier."""
        base = Bundle(name="base", instruction="Base instruction")
        child = Bundle(name="child", instruction="Child instruction")
        result = base.compose(child)
        assert result.instruction == "Child instruction"


class TestBundleToMountPlan:
    """Tests for Bundle.to_mount_plan method."""

    def test_minimal_mount_plan(self) -> None:
        """Empty bundle produces empty mount plan."""
        bundle = Bundle(name="test")
        plan = bundle.to_mount_plan()
        assert plan == {}

    def test_full_mount_plan(self) -> None:
        """Bundle produces complete mount plan."""
        bundle = Bundle(
            name="test",
            session={"orchestrator": "loop-basic"},
            providers=[{"module": "provider-anthropic"}],
            tools=[{"module": "tool-bash"}],
            hooks=[{"module": "hooks-logging"}],
            agents={"my-agent": {"name": "my-agent"}},
        )
        plan = bundle.to_mount_plan()
        assert plan["session"] == {"orchestrator": "loop-basic"}
        assert len(plan["providers"]) == 1
        assert len(plan["tools"]) == 1
        assert len(plan["hooks"]) == 1
        assert "my-agent" in plan["agents"]


class TestBundleResolveContext:
    """Tests for Bundle.resolve_context_path method."""

    def test_resolve_registered_context(self) -> None:
        """Resolves context from registered context dict."""
        bundle = Bundle(name="test", context={"myfile": Path("/tmp/myfile.md")})
        result = bundle.resolve_context_path("myfile")
        assert result == Path("/tmp/myfile.md")

    def test_resolve_from_base_path(self) -> None:
        """Resolves context from base path if file exists."""
        with TemporaryDirectory() as tmpdir:
            # Create a context file
            context_dir = Path(tmpdir) / "context"
            context_dir.mkdir()
            context_file = context_dir / "test.md"
            context_file.write_text("Test content")

            bundle = Bundle(name="test", base_path=Path(tmpdir))
            # Context paths are explicit - include full path relative to bundle root
            result = bundle.resolve_context_path("context/test.md")
            assert result is not None
            assert result.exists()

    def test_resolve_not_found(self) -> None:
        """Returns None for unknown context."""
        bundle = Bundle(name="test")
        result = bundle.resolve_context_path("unknown")
        assert result is None
