# Troubleshooting

Common issues and solutions when using Amplifier Foundation.

## Bundle Loading Errors

### BundleNotFoundError

**Symptom:**
```
BundleNotFoundError: Bundle not found: /path/to/bundle.md
```

**Causes:**
- Path doesn't exist
- Typo in path
- Missing file extension

**Solutions:**
1. Verify the path exists: `ls /path/to/bundle.md`
2. Check for typos in the path
3. For directories, ensure `bundle.md` or `bundle.yaml` exists inside

### BundleLoadError: Parse Error

**Symptom:**
```
BundleLoadError: Failed to parse YAML: ...
```

**Causes:**
- Invalid YAML syntax
- Incorrect frontmatter format
- Encoding issues

**Solutions:**
1. Validate YAML syntax using an online validator
2. Ensure frontmatter is between `---` delimiters
3. Check file encoding is UTF-8

**Example fix:**
```yaml
# Wrong - missing colon
bundle
  name: my-app

# Right
bundle:
  name: my-app
```

### Git Clone Failures

**Symptom:**
```
BundleLoadError: Failed to clone repository: ...
```

**Causes:**
- Network issues
- Authentication problems
- Invalid repository URL
- Non-existent ref (branch/tag)

**Solutions:**

For HTTPS:
```bash
# Test access
git ls-remote https://github.com/org/repo

# For private repos, set credentials
export GIT_USERNAME=user
export GIT_PASSWORD=token
```

For SSH:
```bash
# Test SSH access
ssh -T git@github.com

# Ensure key is loaded
ssh-add ~/.ssh/id_rsa
```

## Validation Errors

### "Bundle must have a name"

**Solution:** Add the name field:
```yaml
bundle:
  name: my-bundle  # Add this
  version: 1.0.0
```

### "Missing required 'module' field"

**Solution:** Each provider/tool/hook needs a module field:
```yaml
providers:
  - module: provider-anthropic  # Required
    source: git+https://...
```

### "config must be a dict"

**Solution:** Use key-value pairs, not a list:
```yaml
# Wrong
config:
  - model: claude-sonnet-4-5

# Right
config:
  default_model: claude-sonnet-4-5
```

## Preparation Errors

### Module Download Failures

**Symptom:**
```
ModuleActivationError: Failed to download module: tool-filesystem
```

**Causes:**
- Network issues
- Missing source URL
- Invalid git reference

**Solutions:**
1. Check network connectivity
2. Verify source URL is correct
3. Test manually: `git clone <source-url>`

### Dependency Installation Failures

**Symptom:**
```
ModuleActivationError: Failed to install dependencies for: provider-anthropic
```

**Causes:**
- Missing system dependencies
- Incompatible Python version
- pip/uv installation issues

**Solutions:**
1. Check module's requirements
2. Verify Python version compatibility
3. Try `pip install <module-package>` manually to see detailed errors

### Module Not Found After Prepare

**Symptom:**
```
ModuleNotFoundError: Module 'tool-bash' not found in prepared bundle
```

**Causes:**
- Module missing from bundle configuration
- Source URL not specified

**Solutions:**
1. Ensure module is in bundle config with source URL:
```yaml
tools:
  - module: tool-bash
    source: git+https://github.com/microsoft/amplifier-module-tool-bash@main
```

## Session Errors

### "No provider available"

**Symptom:**
```
SessionError: No provider available for request
```

**Causes:**
- No providers in bundle
- Provider failed to initialize
- Missing API key

**Solutions:**
1. Add at least one provider to bundle
2. Check provider logs for initialization errors
3. Set required environment variables:
```bash
export ANTHROPIC_API_KEY=your-key
export OPENAI_API_KEY=your-key
```

### Context Manager Errors

**Symptom:**
```
SessionError: Context manager not available
```

**Causes:**
- Missing context in session config
- Context module failed to load

**Solutions:**
1. Add context to session config:
```yaml
session:
  orchestrator: {module: loop-streaming}
  context: {module: context-simple}  # Required
```

## @Mention Resolution Errors

### "Unknown namespace" Error

**Symptom:**
```
MentionResolutionError: Unknown namespace 'myns' in @myns:context/file.md
```

**Causes:**
- Referenced namespace not in `source_base_paths`
- Bundle not included or incorrectly named
- Typo in namespace name

**Solutions:**
1. Verify the namespace exists in composed bundles:
```python
bundle = base.compose(overlay)
print(bundle.source_base_paths.keys())  # Should include 'myns'
```

2. Check bundle names match:
```yaml
# included_bundle.md
bundle:
  name: myns  # This becomes the namespace
```

3. Use correct syntax: `@namespace:path/to/file.md`

### "File not found" in @Mention

**Symptom:**
```
MentionResolutionError: File not found: context/missing.md for @myns:context/missing.md
```

**Causes:**
- File doesn't exist at resolved path
- Wrong relative path in mention
- Bundle's base_path incorrectly set

**Solutions:**
1. Verify the file exists in the source bundle:
```bash
ls /path/to/myns-bundle/context/missing.md
```

2. Check the base_path was correctly tracked:
```python
print(bundle.source_base_paths)  # {'myns': Path('/path/to/myns-bundle')}
```

3. Use `resolve_context_path` to debug resolution:
```python
path = bundle.resolve_context_path("guidelines")
print(f"Resolved to: {path}")
```

### @Mention Not Resolving

**Symptom:** `@namespace:path` appears literally in output instead of being replaced with file content.

**Causes:**
- Using raw Bundle instead of PreparedBundle
- @mention syntax incorrect
- Resolver not configured

**Solutions:**
1. Use PreparedBundle which handles @mention resolution:
```python
prepared = await bundle.prepare()
# PreparedBundle resolves @mentions during session creation
```

2. Check @mention syntax (no spaces):
```markdown
# Wrong
@ foundation : context/file.md

# Right
@foundation:context/file.md
```

## Composition Issues

### Config Not Merging

**Symptom:** Overlay config not appearing in result.

**Causes:**
- Wrong merge understanding
- Missing module ID match

**Explanation:**
Module lists merge by `module` field. Same module ID = update config.

```python
base = [{"module": "foo", "config": {"a": 1}}]
overlay = [{"module": "foo", "config": {"b": 2}}]
# Result: [{"module": "foo", "config": {"a": 1, "b": 2}}]

# Different module IDs don't merge:
overlay = [{"module": "bar", "config": {"b": 2}}]
# Result: [{"module": "foo", "config": {"a": 1}}, {"module": "bar", "config": {"b": 2}}]
```

### Instruction Not Replaced

**Symptom:** Base instruction persists after compose.

**Solution:** Overlay must have non-empty instruction:
```python
# This replaces
overlay = Bundle(name="overlay", instruction="New instruction")

# This doesn't replace (None preserves base)
overlay = Bundle(name="overlay", instruction=None)
```

## Performance Issues

### Slow Bundle Loading

**Causes:**
- Downloading from git every time
- Large repositories

**Solutions:**
1. Use a BundleRegistry which caches by default:
```python
from amplifier_foundation import BundleRegistry
from pathlib import Path

# Registry uses ~/.amplifier by default for caching
registry = BundleRegistry()

# Or specify custom home directory
registry = BundleRegistry(home=Path("~/.myapp").expanduser())
```

2. Use local paths during development

### Slow Module Preparation

**Causes:**
- Downloading many modules
- Installing dependencies

**Solutions:**
1. Prepare once, use multiple times:
```python
prepared = await bundle.prepare()
# Reuse prepared for multiple sessions
```

2. Use local module overrides during development

## I/O Errors

### Cloud Sync Errors

**Symptom:**
```
OSError: [Errno 5] Input/output error
```

**Causes:**
- Files in cloud-synced directories (OneDrive, Dropbox)
- Files not downloaded locally

**Solutions:**
1. Use `read_with_retry` and `write_with_retry`:
```python
from amplifier_foundation import read_with_retry, write_with_retry

content = read_with_retry(Path("file.txt"))
write_with_retry(Path("output.txt"), content)
```

2. Enable "Always keep on this device" for development directories

3. Use non-synced directories for data

## Debugging Tips

### Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect Bundle Contents

```python
bundle = await load_bundle("...")
print(f"Name: {bundle.name}")
print(f"Providers: {bundle.providers}")
print(f"Tools: {bundle.tools}")
print(f"Mount plan: {bundle.to_mount_plan()}")
```

### Test URI Parsing

```python
from amplifier_foundation import parse_uri

parsed = parse_uri("git+https://github.com/org/repo@main#path")
print(f"Scheme: {parsed.scheme}")
print(f"Host: {parsed.host}")
print(f"Path: {parsed.path}")
print(f"Ref: {parsed.ref}")
print(f"Subpath: {parsed.subpath}")
```

### Validate Before Use

Always validate bundles before preparing:
```python
from amplifier_foundation import validate_bundle_or_raise

bundle = await load_bundle("...")
validate_bundle_or_raise(bundle)  # Fail early with clear error
prepared = await bundle.prepare()
```

## Getting Help

If you're still stuck:

1. Check the examples in `examples/` directory
2. Use the notebooks in `notebooks/` for interactive exploration
3. Review the API reference in `docs/API_REFERENCE.md`
