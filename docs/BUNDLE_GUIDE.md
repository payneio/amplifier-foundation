# Creating Bundles with amplifier-foundation

**Purpose**: Guide for creating bundles to package AI agent capabilities using amplifier-foundation.

---

## What is a Bundle?

A **bundle** is a composable unit of configuration that produces a mount plan for AmplifierSession. Bundles package:

- **Tools** - Capabilities the agent can use
- **Agents** - Sub-agent definitions for task delegation
- **Hooks** - Observability and control mechanisms
- **Providers** - LLM backend configurations
- **Instructions** - System prompts and context

Bundles are the primary way to share and compose AI agent configurations.

**Key insight**: Bundles are **configuration**, not Python packages. A bundle repo does not need a root `pyproject.toml`.

---

## Bundle File Structure

A bundle is a markdown file with YAML frontmatter:

```markdown
---
bundle:
  name: my-bundle
  version: 1.0.0
  description: What this bundle provides

includes:
  - bundle: foundation              # Inherit from other bundles

tools:
  - module: tool-name
    source: ./modules/tool-name     # Local path
    config:
      setting: value

agents:
  include:
    - my-bundle:agent-name          # Reference agents in this bundle

hooks:
  - module: hooks-logging
    source: git+https://github.com/microsoft/amplifier-module-hooks-logging@main
---

# System Instructions

Your markdown instructions here. This becomes the system prompt.

Reference documentation with @mentions:
@my-bundle:docs/GUIDE.md
```

---

## Bundle Directory Structure

A typical bundle repository:

```
my-bundle/
├── bundle.md                 # Main bundle definition
├── agents/                   # Agent definitions
│   └── my-agent.md
├── modules/                  # Local modules (optional)
│   └── tool-my-tool/
│       ├── pyproject.toml    # Module's own package config
│       └── my_module/
│           └── __init__.py   # Contains mount() function
├── docs/                     # Documentation (can be @mentioned)
├── README.md                 # For humans browsing the repo
├── LICENSE
├── SECURITY.md
└── CODE_OF_CONDUCT.md
```

**Note**: No `pyproject.toml` at the root. Bundles are configuration, not Python packages. Only modules inside `modules/` need their own `pyproject.toml`.

---

## Creating a Bundle Step-by-Step

### Step 1: Create bundle.md

The bundle definition file at your repository root:

```markdown
---
bundle:
  name: my-capability
  version: 1.0.0
  description: Provides X capability for Y purpose

includes:
  - bundle: foundation    # Optional: inherit from foundation

tools:
  - module: tool-my-capability
    source: ./modules/tool-my-capability
    config:
      default_setting: value

agents:
  include:
    - my-capability:helper-agent
---

# My Capability

You have access to the my-capability tool.

## Usage

[Instructions for the agent on how to use this capability]

For details, see @my-capability:docs/USAGE.md
```

### Step 2: Create Agent Definitions

Place agent files in `agents/` with proper frontmatter:

```markdown
---
meta:
  name: helper-agent
  description: "Description shown when listing agents. Include usage examples..."
---

# Helper Agent

You are a specialized agent for [specific purpose].

## Your Capabilities

[Agent-specific instructions]

## Guidelines

[Behavioral guidelines]
```

**Frontmatter requirements**:
- `meta.name` - Agent identifier (used in `agents: include:`)
- `meta.description` - Shown in agent listings, should include examples

### Step 3: Create Local Modules (if needed)

For custom tools, create a module in `modules/`:

```
modules/tool-my-capability/
├── pyproject.toml
└── my_module_name/
    └── __init__.py
```

**pyproject.toml** (inside the module directory):
```toml
[project]
name = "amplifier-module-tool-my-capability"
version = "0.1.0"
dependencies = ["pyyaml>=6.0"]  # Your dependencies

[project.entry-points."amplifier.modules"]
tool-my-capability = "my_module_name:mount"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**__init__.py**:
```python
async def mount(coordinator, config):
    """Mount the tool module."""
    tool = MyCapabilityTool(config)
    coordinator.mount_points["tools"]["my-capability"] = tool
    return tool

class MyCapabilityTool:
    name = "my-capability"
    description = "What this tool does"
    input_schema = {...}  # JSON schema

    async def execute(self, input_data: dict) -> dict:
        """Execute the tool."""
        # Implementation
        return {"result": "..."}
```

### Step 4: Reference the Module in bundle.md

```yaml
tools:
  - module: tool-my-capability
    source: ./modules/tool-my-capability  # Relative path
    config:
      setting: value
```

The `./` prefix tells the resolver to look relative to the bundle location.

### Step 5: Add Documentation

Create documentation that can be @mentioned in instructions:

```
docs/
├── USAGE.md
├── SCHEMA.md
└── EXAMPLES.md
```

Reference in bundle instructions:
```markdown
For the complete schema, see @my-capability:docs/SCHEMA.md
```

### Step 6: Add README and Standard Files

Create a README.md for humans browsing the repository:
- What the bundle provides
- How to load/use it
- Link to documentation

Copy standard files: LICENSE, SECURITY.md, CODE_OF_CONDUCT.md, SUPPORT.md

---

## Source URI Formats

Bundles support multiple source formats for modules:

| Format | Example | Use Case |
|--------|---------|----------|
| Local path | `./modules/my-module` | Modules within the bundle |
| Relative path | `../shared-module` | Sibling directories |
| Git URL | `git+https://github.com/org/repo@main` | External modules |
| Git with subpath | `git+https://github.com/org/repo@main#subdirectory=modules/foo` | Module within larger repo |

**Local paths are resolved relative to the bundle's location.**

---

## Composition with includes:

Bundles can inherit from other bundles:

```yaml
includes:
  - bundle: foundation                    # Well-known bundle name
  - bundle: git+https://github.com/...    # Git URL
  - bundle: ./bundles/variant.yaml        # Local file
```

**Merge rules**:
- Later bundles override earlier ones
- `session`, `providers`, `tools`, `hooks` are deep-merged by module ID
- `agents` are merged by agent name
- Markdown instructions replace entirely (later wins)

---

## Using @mentions for Context

Reference files in your bundle's instructions without a separate `context:` section:

```markdown
---
bundle:
  name: my-bundle
---

# Instructions

Follow the guidelines in @my-bundle:docs/GUIDELINES.md

For API details, see @my-bundle:docs/API.md
```

**Format**: `@namespace:path/to/file.md`

The namespace is the bundle name. Paths are relative to the bundle root.

---

## Loading a Bundle

```bash
# Load from local file
amplifier run --bundle ./bundle.md "prompt"

# Load from git URL
amplifier run --bundle git+https://github.com/org/amplifier-bundle-foo@main "prompt"

# Include in another bundle
includes:
  - bundle: git+https://github.com/org/amplifier-bundle-foo@main
```

---

## Best Practices

### Keep Modules Local When Possible

For bundle-specific tools, keep them in `modules/` within the bundle:
- Simpler distribution (one repo)
- Versioning stays synchronized
- No external dependency management

Extract to separate repo only when:
- Multiple bundles need the same module
- Module needs independent versioning
- Module is generally useful outside the bundle

### Use Descriptive Agent Metadata

The `meta.description` is shown when listing agents. Include:
- What the agent does
- When to use it
- Usage examples in the description string

### Document with @mentions

Keep documentation in `docs/` and reference via @mentions. This:
- Avoids duplicating content in instructions
- Keeps docs maintainable
- Allows detailed reference material

### Start Without includes:

You don't need to include `foundation` if your bundle is self-contained. Add `includes:` only when you need capabilities from other bundles.

### No Root pyproject.toml

Bundles are configuration, not Python packages. Don't add a `pyproject.toml` at the bundle root - it serves no purpose and adds confusion about what bundles are.

---

## Troubleshooting

### "Module not found" errors

- Verify `source:` path is correct relative to bundle location
- Check module has `pyproject.toml` with entry point
- Ensure `mount()` function exists in module

### Agent not loading

- Verify `meta:` frontmatter exists with `name` and `description`
- Check agent file is in `agents/` directory
- Verify `agents: include:` uses correct namespace prefix

### @mentions not resolving

- Verify file exists at the referenced path
- Check namespace matches bundle name
- Ensure path is relative to bundle root

---

## Example: Complete Bundle

See `amplifier-bundle-recipes` for a complete real-world example:

```
amplifier-bundle-recipes/
├── bundle.md                 # Bundle definition
├── agents/
│   ├── recipe-author.md      # Conversational recipe creation
│   └── result-validator.md   # Pass/fail validation
├── modules/
│   └── tool-recipes/         # Full tool implementation
│       ├── pyproject.toml
│       └── amplifier_module_tool_recipes/
├── docs/                     # Comprehensive documentation
├── examples/                 # Working recipe examples
├── templates/                # Starter templates
├── README.md
├── LICENSE
├── SECURITY.md
├── CODE_OF_CONDUCT.md
└── SUPPORT.md
```

Key features demonstrated:
- Local module with `source: ./modules/tool-recipes`
- Multiple agents with proper `meta:` frontmatter
- @mentions for documentation in bundle instructions
- No root pyproject.toml (bundles are configuration, not packages)

---

## Reference

- **[URI Formats](URI_FORMATS.md)** - Complete source URI documentation
- **[Validation](VALIDATION.md)** - Bundle validation rules
- **[API Reference](API_REFERENCE.md)** - Programmatic bundle loading
