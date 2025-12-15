# Validation Guide

How bundle validation works and how to use it effectively.

## Overview

Validation ensures bundles are structurally correct before use. This catches configuration errors early, before they cause runtime failures.

## Basic Validation

```python
from amplifier_foundation import load_bundle, validate_bundle

bundle = await load_bundle("/path/to/bundle.md")
result = validate_bundle(bundle)

if result.valid:
    print("Bundle is valid!")
else:
    for error in result.errors:
        print(f"Error: {error}")
    for warning in result.warnings:
        print(f"Warning: {warning}")
```

## Validation or Raise

For stricter validation:

```python
from amplifier_foundation import validate_bundle_or_raise, BundleValidationError

try:
    validate_bundle_or_raise(bundle)
except BundleValidationError as e:
    print(f"Validation failed: {e}")
```

## What Gets Validated

### Required Fields

| Field | Requirement |
|-------|-------------|
| `bundle.name` | Must be present and non-empty |

Error example:
```
Error: Bundle must have a name
```

### Module Lists

Providers, tools, and hooks must be structured correctly:

| Check | Requirement |
|-------|-------------|
| Type | Each entry must be a dict |
| Module field | Each entry must have `module` key |
| Config field | If present, must be a dict |

Error examples:
```
Error: providers[0]: Must be a dict, got str
Error: tools[1]: Missing required 'module' field
Error: hooks[0]: 'config' must be a dict, got list
```

### Session Configuration

| Check | Requirement |
|-------|-------------|
| Type | `session` must be a dict |
| Orchestrator | If present, must be a string |
| Context | If present, must be a string |

Error examples:
```
Error: session: Must be a dict, got list
Error: session.orchestrator: Must be a string, got dict
```

### Resources

| Check | Requirement |
|-------|-------------|
| Agents | Each agent must be a dict |
| Context paths | Paths should exist (warning only) |

Examples:
```
Error: agents.bug-hunter: Must be a dict, got str
Warning: context.guidelines: Path does not exist: /path/to/guidelines.md
```

## Completeness Validation

For bundles that should be directly mountable (e.g., in `bundles/` directory).

### Using BundleValidator (Recommended)

```python
from amplifier_foundation import BundleValidator

validator = BundleValidator()
result = validator.validate_completeness(bundle)

# Or raise on errors
validator.validate_completeness_or_raise(bundle)
```

### Convenience Functions

Standalone functions are available directly in the validator module:

```python
from amplifier_foundation.validator import (
    validate_bundle_completeness,
    validate_bundle_completeness_or_raise,
)

result = validate_bundle_completeness(bundle)

# Or raise on errors
validate_bundle_completeness_or_raise(bundle)  # Raises BundleValidationError
```

Note: These convenience functions are not exported from the main `amplifier_foundation` module. Use the BundleValidator class for the standard API.

### Completeness Requirements

| Section | Requirement |
|---------|-------------|
| `session` | Must be present |
| `session.orchestrator` | Must be specified |
| `session.context` | Must be specified |
| `providers` | At least one provider required |

Error examples:
```
Error: Mount plan requires 'session' section
Error: session: Missing required 'orchestrator' field
Error: Mount plan requires at least one provider
```

### When to Use Completeness Validation

- **Use for**: Bundles in `bundles/` directory that are meant to be run directly
- **Don't use for**: Partial bundles like providers/, behaviors/, agents/ that are meant to be composed

## Custom Validation

Extend the validator for app-specific rules:

```python
from amplifier_foundation import BundleValidator, ValidationResult

class AppValidator(BundleValidator):
    def validate(self, bundle) -> ValidationResult:
        # Run base validation first
        result = super().validate(bundle)

        # Add custom rules
        self._validate_custom_rules(bundle, result)

        return result

    def _validate_custom_rules(self, bundle, result):
        # Example: Require specific tool
        has_filesystem = any(
            t.get("module") == "tool-filesystem"
            for t in bundle.tools
        )
        if not has_filesystem:
            result.add_warning("Missing recommended filesystem tool")

        # Example: Enforce naming convention
        if not bundle.name.startswith("app-"):
            result.add_error("Bundle name must start with 'app-'")
```

## Validation Workflow

### Development Workflow

```python
# 1. Load bundle
bundle = await load_bundle("./bundle.md")

# 2. Validate
result = validate_bundle(bundle)
if not result.valid:
    print("Fix these errors before proceeding:")
    for error in result.errors:
        print(f"  - {error}")
    sys.exit(1)

# 3. Review warnings
for warning in result.warnings:
    print(f"Warning: {warning}")

# 4. Proceed with valid bundle
prepared = await bundle.prepare()
```

### CI/CD Workflow

```python
import sys

def validate_all_bundles(directory: Path) -> bool:
    all_valid = True

    for bundle_path in directory.glob("**/*.md"):
        try:
            bundle = await load_bundle(bundle_path)
            result = validate_bundle(bundle)

            if not result.valid:
                print(f"FAIL: {bundle_path}")
                for error in result.errors:
                    print(f"  Error: {error}")
                all_valid = False
            else:
                print(f"OK: {bundle_path}")

        except Exception as e:
            print(f"ERROR: {bundle_path}: {e}")
            all_valid = False

    return all_valid

if not validate_all_bundles(Path("./bundles")):
    sys.exit(1)
```

## Common Validation Errors

### Missing Bundle Name

```yaml
# Wrong
bundle:
  version: 1.0.0

# Right
bundle:
  name: my-bundle
  version: 1.0.0
```

### Invalid Module Entry

```yaml
# Wrong - string instead of dict
providers:
  - provider-anthropic

# Right
providers:
  - module: provider-anthropic
    source: git+https://...
```

### Missing Module Field

```yaml
# Wrong - no module field
tools:
  - source: git+https://...
    config: {}

# Right
tools:
  - module: tool-filesystem
    source: git+https://...
```

### Invalid Config Type

```yaml
# Wrong - config is a list
providers:
  - module: provider-anthropic
    config:
      - model: claude-sonnet-4-5

# Right
providers:
  - module: provider-anthropic
    config:
      default_model: claude-sonnet-4-5
```

## Interactive Validation

Use the `notebooks/validation_checker.ipynb` notebook to interactively test validation:

1. Paste your bundle YAML
2. Run validation
3. See errors with explanations
4. Fix and re-run
