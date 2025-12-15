# Core Concepts

Understanding the key concepts in Amplifier Foundation.

## What is a Bundle?

A **Bundle** is a composable unit of configuration that produces a **mount plan** for AmplifierSession.

Think of bundles as configuration packages that can be combined, layered, and reused.

```
Bundle → to_mount_plan() → Mount Plan → AmplifierSession
```

### Bundle Contents

A bundle contains:

| Section | Purpose | Example |
|---------|---------|---------|
| `bundle` | Metadata (name, version) | `name: my-app` |
| `session` | Orchestrator and context manager | `orchestrator: loop-streaming` |
| `providers` | LLM backends | `provider-anthropic` |
| `tools` | Agent capabilities | `tool-filesystem`, `tool-bash` |
| `hooks` | Observability and control | `hooks-logging` |
| `agents` | Named agent configurations | Sub-session delegation |
| `context` | Context files to include | System instructions |
| `instruction` | System instruction (markdown body) | "You are a helpful assistant." |
| `source_base_paths` | Base paths for @mention resolution (internal) | Tracks namespaces during composition |

### Bundle Format

Bundles are markdown files with YAML frontmatter:

```markdown
---
bundle:
  name: my-app
  version: 1.0.0

session:
  orchestrator:
    module: loop-streaming
  context:
    module: context-simple

providers:
  - module: provider-anthropic
    source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
    config:
      default_model: claude-sonnet-4-5
---

You are a helpful assistant.

This markdown body becomes the system instruction.
```

## Composition

Bundles can be **composed** to layer configuration. Later bundles override earlier ones.

```python
result = base.compose(overlay)
```

### Merge Rules

| Section | Rule | Behavior |
|---------|------|----------|
| `session` | Deep merge | Nested dicts merged recursively |
| `providers` | Merge by module ID | Same ID = update config, new = add |
| `tools` | Merge by module ID | Same ID = update config, new = add |
| `hooks` | Merge by module ID | Same ID = update config, new = add |
| `instruction` | Replace | Later completely replaces earlier |

### Example

```python
base = Bundle(
    name="base",
    providers=[{"module": "provider-mock", "config": {"debug": False}}],
    tools=[{"module": "tool-filesystem"}],
)

overlay = Bundle(
    name="overlay",
    providers=[{"module": "provider-mock", "config": {"debug": True}}],  # Updates
    tools=[{"module": "tool-bash"}],  # Adds
)

result = base.compose(overlay)
# result.providers = [{"module": "provider-mock", "config": {"debug": True}}]
# result.tools = [{"module": "tool-filesystem"}, {"module": "tool-bash"}]
```

### Includes (Declarative Composition)

The `includes:` section declares bundles to compose with:

```yaml
bundle:
  name: my-app
  version: 1.0.0

includes:
  - foundation  # Named bundle from registry
  - git+https://github.com/example/bundle@main  # URI
```

Includes are resolved first, then composed in order.

## Mount Plan

A **mount plan** is the final configuration dict consumed by AmplifierSession.

```python
mount_plan = bundle.to_mount_plan()
# Returns:
# {
#     "session": {"orchestrator": "loop-streaming", "context": "context-simple"},
#     "providers": [...],
#     "tools": [...],
#     "hooks": [...],
#     "agents": {...}
# }
```

### What Goes in a Mount Plan

Only sections needed by AmplifierSession:
- `session` - Orchestrator and context manager selection
- `providers` - LLM backends to load
- `tools` - Tools to make available
- `hooks` - Hooks for observability/control
- `agents` - Agent configs for sub-session delegation

**Not included**: `includes` (resolved), `context` (processed separately), `instruction` (injected into context).

## Prepared Bundle

A **PreparedBundle** is a bundle ready for execution with all modules activated.

```python
# Load bundle
bundle = await load_bundle("/path/to/bundle.md")

# Prepare (downloads and installs modules)
prepared = await bundle.prepare()

# Create session
async with prepared.create_session() as session:
    response = await session.execute("Hello!")
```

### Why Prepare?

`prepare()` handles module resolution:
1. Collects all modules from the mount plan
2. Downloads from git URLs if needed
3. Installs Python dependencies
4. Returns a PreparedBundle with module resolver

This separation allows:
- Bundles to be loaded and inspected without downloading
- Module installation to happen once before session creation
- Explicit control over when downloads occur

### @Mention Resolution

PreparedBundle resolves `@mentions` in instructions to include context files from composed bundles.

**Syntax**: `@namespace:path/to/file.md`

```markdown
---
bundle:
  name: my-app
includes:
  - foundation  # Provides namespace "foundation"
---

See @foundation:context/guidelines.md for project guidelines.
```

**How it works**:
1. During composition, each bundle's `base_path` is tracked in `source_base_paths` by namespace
2. When a PreparedBundle resolves instructions, it finds `@namespace:path` references
3. The path is resolved relative to the namespace's original `base_path`
4. Content is loaded and included inline

**Namespaces** come from:
- Bundle names (from `bundle.name`)
- Explicit namespace assignments during composition

This allows instructions to reference context files from any included bundle without knowing their absolute paths.

## Bundle Registry

The **BundleRegistry** manages named bundles and handles loading.

```python
from amplifier_foundation import BundleRegistry

registry = BundleRegistry()

# Register a named bundle
registry.register("my-bundle", "git+https://github.com/example/bundle@main")

# Load by name
bundle = await registry.load("my-bundle")

# Load by URI directly
bundle = await registry.load("git+https://github.com/example/other@main")
```

### Convenience Function

For simple loading, use `load_bundle()`:

```python
from amplifier_foundation import load_bundle

# Load from path
bundle = await load_bundle("/path/to/bundle.md")

# Load from git
bundle = await load_bundle("git+https://github.com/example/bundle@main")
```

## Source URIs

Bundles and modules are loaded via URI strings:

| Format | Example | Use |
|--------|---------|-----|
| Local path | `/path/to/bundle.md` | Development |
| Local dir | `/path/to/bundle/` | Bundle with context/ |
| Git HTTPS | `git+https://github.com/org/repo@main` | Public repos |
| Git SSH | `git+ssh://git@github.com/org/repo@v1.0.0` | Private repos |

See [URI_FORMATS.md](URI_FORMATS.md) for complete documentation.

## Validation

Bundles can be validated before use:

```python
from amplifier_foundation import validate_bundle, validate_bundle_or_raise

result = validate_bundle(bundle)
if not result.valid:
    for error in result.errors:
        print(f"Error: {error}")
    for warning in result.warnings:
        print(f"Warning: {warning}")

# Or raise on errors
validate_bundle_or_raise(bundle)  # Raises BundleValidationError
```

### What Gets Validated

- Required fields (name)
- Module list structure (must have `module` key)
- Session configuration types
- Resource references (context paths exist)

See [VALIDATION.md](VALIDATION.md) for the complete validation guide.

## Philosophy

Amplifier Foundation follows these principles:

### Mechanism, Not Policy

Foundation provides the **mechanism** for bundle composition. It doesn't decide:
- Which bundles to use
- What providers/tools to include
- How to configure them

Those are **policy** decisions for your application.

### Ruthless Simplicity

- One composition mechanism: `includes:` + `compose()`
- Simple merge rules (documented above)
- No magic, no implicit behavior

### Text-First

- Bundles are markdown files (human-readable)
- Configuration is YAML (diffable)
- No binary formats

## Next Steps

- **[QUICKSTART.md](QUICKSTART.md)** - Get running in 5 minutes
- **[API_REFERENCE.md](API_REFERENCE.md)** - Complete API documentation
- **[PATTERNS.md](PATTERNS.md)** - Common usage patterns
