# API Reference

Complete reference for the Amplifier Foundation API.

## Core Classes

### Bundle

The core composable unit containing mount plan config and resources.

```python
from amplifier_foundation import Bundle
```

#### Constructor

```python
Bundle(
    name: str,
    version: str = "1.0.0",
    description: str = "",
    includes: list[str] = [],
    session: dict[str, Any] = {},
    providers: list[dict[str, Any]] = [],
    tools: list[dict[str, Any]] = [],
    hooks: list[dict[str, Any]] = [],
    agents: dict[str, dict[str, Any]] = {},
    context: dict[str, Path] = {},
    instruction: str | None = None,
    base_path: Path | None = None,
    source_base_paths: dict[str, Path] = {},  # Tracks base_path for each source namespace
)
```

#### Methods

**compose(*others: Bundle) -> Bundle**

Compose this bundle with others. Later bundles override earlier ones.

```python
result = base.compose(overlay1, overlay2)
```

**to_mount_plan() -> dict[str, Any]**

Compile to mount plan dict for AmplifierSession.

```python
mount_plan = bundle.to_mount_plan()
```

**prepare(install_deps: bool = True) -> PreparedBundle**

Prepare bundle for execution by activating all modules.

```python
prepared = await bundle.prepare()
```

**get_system_instruction() -> str | None**

Get the system instruction for this bundle.

```python
instruction = bundle.get_system_instruction()
```

**resolve_context_path(name: str) -> Path | None**

Resolve context file by name.

```python
path = bundle.resolve_context_path("guidelines")
```

**resolve_agent_path(name: str) -> Path | None**

Resolve agent file by name.

```python
path = bundle.resolve_agent_path("bug-hunter")
```

**from_dict(data: dict, base_path: Path | None = None) -> Bundle** (classmethod)

Create Bundle from parsed dict (from YAML/frontmatter).

```python
data = yaml.safe_load(yaml_content)
bundle = Bundle.from_dict(data, base_path=Path("/path/to/bundle"))
```

### PreparedBundle

A bundle prepared for execution with module resolver.

```python
from amplifier_foundation import Bundle

prepared = await bundle.prepare()
```

#### Attributes

- `mount_plan: dict[str, Any]` - The compiled mount plan
- `resolver: BundleModuleResolver` - Module path resolver
- `bundle: Bundle` - Original bundle

#### Methods

**create_session(...) -> AmplifierSession**

Create an AmplifierSession with the resolver properly mounted.

```python
async with prepared.create_session() as session:
    response = await session.execute("Hello!")
```

Parameters:
- `session_id: str | None` - Optional session ID for resuming
- `parent_id: str | None` - Optional parent session ID
- `approval_system: Any` - Optional approval system for hooks
- `display_system: Any` - Optional display system for hooks

**spawn(child_bundle, instruction, ...) -> dict[str, Any]**

Spawn a sub-session with a child bundle.

```python
result = await prepared.spawn(
    child_bundle=agent_bundle,
    instruction="Find the bug",
    parent_session=session,
)
# Returns: {"output": response, "session_id": child_id}
```

Parameters:
- `child_bundle: Bundle` - Bundle to spawn
- `instruction: str` - Task instruction
- `compose: bool = True` - Whether to compose with parent
- `parent_session: Any` - Parent session for UX inheritance
- `session_id: str | None` - For resuming existing session

### BundleRegistry

Manages named bundles and handles loading.

```python
from amplifier_foundation import BundleRegistry
```

#### Constructor

```python
BundleRegistry(home: Path | None = None)
```

Parameters:
- `home`: Base directory for registry operations. Resolves in order:
  1. Explicit parameter value
  2. `AMPLIFIER_HOME` environment variable
  3. `~/.amplifier` (default)

#### Methods

**register(bundles: dict[str, str]) -> None**

Register name → URI mappings for bundles.

```python
registry.register({"my-bundle": "git+https://github.com/example/bundle@main"})
```

**find(name: str) -> str | None**

Look up URI for a registered name.

```python
uri = registry.find("my-bundle")  # Returns URI or None
```

**list_registered() -> list[str]**

List all registered bundle names.

```python
names = registry.list_registered()  # Returns sorted list
```

**load(name_or_uri: str | None = None, *, auto_register: bool = True) -> Bundle | dict[str, Bundle]**

Load bundle(s) by name, URI, or all registered.

```python
# Load single bundle
bundle = await registry.load("my-bundle")
bundle = await registry.load("git+https://github.com/example/bundle@main")

# Load all registered bundles
all_bundles = await registry.load()  # Returns dict[str, Bundle]
```

**check_update(name: str | None = None) -> UpdateInfo | list[UpdateInfo] | None**

Check for available updates.

```python
# Check single bundle
update = await registry.check_update("my-bundle")

# Check all registered
updates = await registry.check_update()  # Returns list
```

**update(name: str | None = None) -> Bundle | dict[str, Bundle]**

Update to latest version (bypasses cache).

```python
bundle = await registry.update("my-bundle")
all_updated = await registry.update()  # Update all
```

**get_state(name: str | None = None) -> BundleState | dict[str, BundleState] | None**

Get tracked state for bundle(s).

```python
# Single bundle state
state = registry.get_state("my-bundle")
if state:
    print(f"Loaded at: {state.loaded_at}")

# All bundle states
all_states = registry.get_state()  # Returns dict[str, BundleState]
```

**save() -> None**

Persist registry state to disk.

```python
registry.save()  # Saves to home/registry.json
```

#### Properties

**home -> Path**

Base directory for all registry data.

### ValidationResult

Result of bundle validation.

```python
from amplifier_foundation import ValidationResult
```

#### Attributes

- `valid: bool` - Whether the bundle is valid
- `errors: list[str]` - Validation errors
- `warnings: list[str]` - Validation warnings

### BundleValidator

Validates bundle structure and configuration.

```python
from amplifier_foundation import BundleValidator
```

#### Methods

**validate(bundle: Bundle) -> ValidationResult**

Validate a bundle.

```python
result = validator.validate(bundle)
```

**validate_or_raise(bundle: Bundle) -> None**

Validate and raise `BundleValidationError` on errors.

**validate_completeness(bundle: Bundle) -> ValidationResult**

Validate that a bundle is complete for direct mounting.

**validate_completeness_or_raise(bundle: Bundle) -> None**

Validate completeness and raise on errors.

## Convenience Functions

### load_bundle

```python
from amplifier_foundation import load_bundle

async def load_bundle(
    source: str,
    auto_include: bool = True,
    registry: BundleRegistry | None = None,
) -> Bundle
```

Load a bundle from a source URI.

Parameters:
- `source`: Path or URI to load (file path, git URL, etc.)
- `auto_include`: Whether to automatically resolve includes (default: True)
- `registry`: Optional registry for caching and lookup

```python
bundle = await load_bundle("/path/to/bundle.md")
bundle = await load_bundle("git+https://github.com/example/bundle@main")
bundle = await load_bundle("my-bundle", registry=registry)
```

### validate_bundle

```python
from amplifier_foundation import validate_bundle

result = validate_bundle(bundle)
```

### validate_bundle_or_raise

```python
from amplifier_foundation import validate_bundle_or_raise

validate_bundle_or_raise(bundle)  # Raises BundleValidationError
```

## Exceptions

### BundleError

Base exception for bundle operations.

### BundleNotFoundError

Bundle could not be found at the specified location.

### BundleLoadError

Bundle could not be loaded (parse error, I/O error).

### BundleValidationError

Bundle validation failed.

### BundleDependencyError

Bundle dependency could not be resolved.

```python
from amplifier_foundation import (
    BundleError,
    BundleNotFoundError,
    BundleLoadError,
    BundleValidationError,
    BundleDependencyError,
)
```

## Protocols

### MentionResolverProtocol

Protocol for resolving @mentions in instructions.

```python
class MentionResolverProtocol(Protocol):
    async def resolve(self, mention: str) -> MentionResult | None: ...
```

### SourceResolverProtocol

Protocol for resolving source URIs.

```python
class SourceResolverProtocol(Protocol):
    async def resolve(self, uri: str) -> Path: ...
```

### CacheProviderProtocol

Protocol for caching resolved sources.

```python
class CacheProviderProtocol(Protocol):
    def get(self, key: str) -> Path | None: ...
    def set(self, key: str, path: Path) -> None: ...
```

## Utilities

### Dict Utilities

```python
from amplifier_foundation import deep_merge, merge_module_lists, get_nested, set_nested
```

**deep_merge(base: dict, overlay: dict) -> dict**

Deep merge two dicts. Overlay values override base.

```python
result = deep_merge({"a": {"b": 1}}, {"a": {"c": 2}})
# {"a": {"b": 1, "c": 2}}
```

**merge_module_lists(base: list, overlay: list) -> list**

Merge module lists by module ID. Same ID = update config, new = add.

```python
base = [{"module": "foo", "config": {"a": 1}}]
overlay = [{"module": "foo", "config": {"b": 2}}, {"module": "bar"}]
result = merge_module_lists(base, overlay)
# [{"module": "foo", "config": {"a": 1, "b": 2}}, {"module": "bar"}]
```

**get_nested(data: dict, path: list[str], default: Any = None) -> Any**

Get nested value by path.

```python
value = get_nested({"a": {"b": {"c": 1}}}, ["a", "b", "c"])  # 1
value = get_nested({"a": 1}, ["x", "y"], default="not found")  # "not found"
```

**set_nested(data: dict, path: list[str], value: Any) -> None**

Set nested value by path. Creates intermediate dicts as needed.

```python
d = {}
set_nested(d, ["a", "b", "c"], 1)  # {"a": {"b": {"c": 1}}}
```

### I/O Utilities

```python
from amplifier_foundation import (
    read_yaml,
    write_yaml,
    parse_frontmatter,
    read_with_retry,
    write_with_retry,
)
```

**async read_yaml(path: Path) -> dict | None**

Read YAML file asynchronously.

```python
data = await read_yaml(Path("config.yaml"))  # Returns dict or None if not found
```

**async write_yaml(path: Path, data: dict) -> None**

Write dict to YAML file asynchronously.

```python
await write_yaml(Path("config.yaml"), {"key": "value"})
```

**parse_frontmatter(content: str) -> tuple[dict, str]**

Parse YAML frontmatter from markdown.

```python
frontmatter, body = parse_frontmatter(markdown_content)
```

**async read_with_retry(path: Path, max_retries: int = 3, initial_delay: float = 0.1) -> str**

Read file with retry (for cloud-synced files like OneDrive, Dropbox).

```python
content = await read_with_retry(Path("data.txt"))
```

**async write_with_retry(path: Path, content: str, max_retries: int = 3, initial_delay: float = 0.1) -> None**

Write file with retry. Creates parent directories as needed.

```python
await write_with_retry(Path("output.txt"), "content")
```

### Path Utilities

```python
from amplifier_foundation import (
    parse_uri,
    ParsedURI,
    normalize_path,
    find_files,
    find_bundle_root,
)
```

**parse_uri(uri: str) -> ParsedURI**

Parse a source URI.

```python
parsed = parse_uri("git+https://github.com/org/repo@main")
# ParsedURI(scheme="git+https", host="github.com", path="org/repo", ref="main")
```

**normalize_path(path: str | Path, relative_to: Path | None = None) -> Path**

Normalize and resolve path.

```python
path = normalize_path("./config.yaml")  # Resolves to absolute path
path = normalize_path("config.yaml", relative_to=Path("/project"))  # /project/config.yaml
```

**async find_files(base: Path, pattern: str, recursive: bool = True) -> list[Path]**

Find files matching glob pattern.

```python
files = await find_files(Path("docs"), "*.md")  # All .md files recursively
files = await find_files(Path("docs"), "*.md", recursive=False)  # Top-level only
```

**async find_bundle_root(start: Path) -> Path | None**

Find bundle root by looking for bundle.md or bundle.yaml.

```python
root = await find_bundle_root(Path.cwd())  # Searches upward from cwd
```

### Mention Utilities

```python
from amplifier_foundation import (
    parse_mentions,
    load_mentions,
    BaseMentionResolver,
    ContentDeduplicator,
    ContextFile,
    MentionResult,
)
```

**parse_mentions(text: str) -> list[str]**

Parse @mentions from text.

```python
mentions = parse_mentions("See @foundation:context/guidelines.md")
# ["@foundation:context/guidelines.md"]
```

**async load_mentions(text: str, resolver: MentionResolverProtocol, deduplicator: ContentDeduplicator | None = None, relative_to: Path | None = None, max_depth: int = 3) -> list[MentionResult]**

Load content for all @mentions in text recursively with deduplication.

All mentions are opportunistic - if a file can't be found, it's silently skipped.

```python
results = await load_mentions(
    text="See @AGENTS.md and @foundation:context/guidelines.md",
    resolver=resolver,
    deduplicator=deduplicator,  # Optional, creates one if None
    relative_to=Path.cwd(),     # Base path for relative mentions
    max_depth=3,                # Maximum recursion depth
)
```

**BaseMentionResolver**

Reference implementation of MentionResolverProtocol.

```python
resolver = BaseMentionResolver(
    bundles={"foundation": foundation_bundle},
    base_path=Path.cwd(),
)
```

**ContentDeduplicator**

Tracks loaded content by SHA-256 hash to avoid duplicates.

```python
deduplicator = ContentDeduplicator()

# Add file (returns True if new, False if duplicate content)
was_new = deduplicator.add_file(path, content)

# Check if content has been seen
if not deduplicator.is_seen(content):
    # New content

# Get all unique files
unique_files = deduplicator.get_unique_files()  # Returns list[ContextFile]
```

## Reference Implementations

### SimpleSourceResolver

Simple source resolver for local and git URIs.

```python
from amplifier_foundation import SimpleSourceResolver

resolver = SimpleSourceResolver()
path = await resolver.resolve("git+https://github.com/org/repo@main")
```

### SimpleCache / DiskCache

Cache implementations.

```python
from amplifier_foundation import SimpleCache, DiskCache

cache = SimpleCache()  # In-memory
cache = DiskCache(Path("~/.amplifier/cache").expanduser())  # Persistent
```

## Type Exports

All public types are exported from the main module:

```python
from amplifier_foundation import (
    # Core
    Bundle,
    BundleRegistry,
    BundleState,
    UpdateInfo,
    BundleValidator,
    ValidationResult,
    # Exceptions
    BundleError,
    BundleNotFoundError,
    BundleLoadError,
    BundleValidationError,
    BundleDependencyError,
    # Protocols
    MentionResolverProtocol,
    SourceResolverProtocol,
    SourceHandlerProtocol,
    CacheProviderProtocol,
    # Implementations
    BaseMentionResolver,
    SimpleSourceResolver,
    SimpleCache,
    DiskCache,
    # Mentions
    parse_mentions,
    load_mentions,
    ContentDeduplicator,
    ContextFile,
    MentionResult,
    # I/O
    read_yaml,
    write_yaml,
    parse_frontmatter,
    read_with_retry,
    write_with_retry,
    # Dicts
    deep_merge,
    merge_module_lists,
    get_nested,
    set_nested,
    # Paths
    parse_uri,
    ParsedURI,
    normalize_path,
    construct_agent_path,
    construct_context_path,
    find_files,
    find_bundle_root,
    # Functions
    load_bundle,
    validate_bundle,
    validate_bundle_or_raise,
)
```
