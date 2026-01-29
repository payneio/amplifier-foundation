# Domain Validator Authoring Guide

This guide captures the methodology for creating accurate, actionable domain validators as Amplifier recipes. It is based on learnings from building the bundle validator, where **50% of initial assumptions were wrong** when traced against actual code behavior.

---

## Overview

### What is a Domain Validator?

A domain validator is a recipe that systematically checks artifacts against:
- **Code-enforced requirements** (will break if violated)
- **Conventions** (code works, but deviates from patterns)
- **Best practices** (recommendations for quality)

### When to Create One

Create a domain validator when:
- A concept has multiple rules users struggle to remember
- Incorrect usage causes confusing errors or silent failures
- You want to codify expertise for consistent guidance
- Onboarding new users or contributors to a domain

### Success Criteria

A good validator:
- ✅ Produces **zero false positives** on known-good exemplars
- ✅ Catches **real issues** with actionable remediation
- ✅ Correctly **classifies severity** (ERROR vs WARNING vs SUGGESTION)
- ✅ **Aligns with code behavior**, not just documentation

---

## The Code Verification Imperative

> **Critical Learning**: In the bundle validator project, 50% of initial rules were inaccurate when traced against actual code behavior.

**Do NOT trust:**
- Documentation (may be outdated)
- Your intuition (may be based on old patterns)
- What "should" happen (may differ from what does happen)

**DO verify:**
- Trace code paths with LSP tools (`findReferences`, `hover`, `goToDefinition`)
- Find the actual enforcement point (or confirm there isn't one)
- Document evidence for each rule

### Examples of Assumptions vs Reality

| Assumption | Reality (from code) | Impact |
|------------|---------------------|--------|
| "Inline agents are deprecated" | Both formats fully supported by `_parse_agents()` | Would create false positives |
| "Standalone bundles must include foundation" | Need session config (orchestrator + context), any source | Misleading guidance |
| "`context.include` and `@mentions` are interchangeable" | Different composition semantics! (accumulates vs replaces) | Wrong advice |

### The Verification Pattern

```
1. Write initial rule based on documentation/intuition
2. Use LSP tools to trace actual code behavior
3. Find enforcement point (exception raised? validation fails?)
4. Adjust rule severity based on evidence
5. If code differs from docs, update DOCS (not your rule)
```

---

## Severity Classification Framework

This taxonomy is **critical** for validator usefulness. Misclassified severity causes either:
- **False urgency** (warnings treated as errors → user frustration)
- **Missed issues** (errors treated as suggestions → real problems ignored)

### The Three Levels

| Severity | Definition | Evidence Required | Example |
|----------|------------|-------------------|---------|
| **ERROR** | Code enforces this; violation causes failure | Exception raised, validation fails, function returns error | `bundle.name` missing → namespace won't register |
| **WARNING** | Convention violated; code works but deviation noted | No code enforcement, but documented pattern | Using `/bundles/` instead of `/behaviors/` |
| **SUGGESTION** | Best practice; pure recommendation | No documentation requirement, expertise-based | Adding `meta.description` for discoverability |

### The Litmus Test

```python
# Is it an ERROR?
# Search for enforcement in code:
grep -r "raise.*Error" | grep "your_concept"
# If found → ERROR

# Is it a WARNING?
# Search in documentation:
grep -r "should|must|required" docs/ | grep "your_concept"
# If only in docs, not code → WARNING

# Otherwise → SUGGESTION
# Based on expertise and best practices
```

### Real Examples from Bundle Validator

| Finding | Initial Severity | Verified Severity | Evidence |
|---------|------------------|-------------------|----------|
| Missing `bundle:` wrapper | ERROR | **ERROR** ✅ | `Bundle.from_dict()` raises `ValueError` |
| Not using DRY pattern | ERROR | **WARNING** ⬇️ | No code enforcement, just convention |
| Inline agents format | ERROR | **REMOVED** ❌ | Code explicitly supports both formats |
| Orphaned agent file | WARNING | **WARNING** ✅ | Valid concern, but code doesn't fail |

---

## Recipe Structure Patterns

### Single-Item vs Repository-Wide

| Pattern | Use When | Example |
|---------|----------|---------|
| **Single-item** | Validating one artifact in depth | `validate-bundle.yaml` |
| **Repository-wide** | Scanning entire repo for patterns | `validate-bundle-repo.yaml` |

Often you need both: repo-wide discovers items, then delegates to single-item for deep validation.

### The 5-Phase Architecture

Based on the exemplar recipes, validators follow this structure:

```yaml
steps:
  # Phase 1: ENVIRONMENT
  # Detect capabilities, versions, available tools
  - id: check-environment
    type: bash
    
  # Phase 2: STRUCTURAL (deterministic)
  # Parse files, check syntax, verify references exist
  - id: structural-validation
    type: bash  # or agent with parse_json
    
  # Phase 3: CONVENTION (agent reasoning)
  # Check patterns, naming, organization
  - id: convention-check
    agent: foundation:zen-architect
    
  # Phase 4: GOTCHAS (expert knowledge)
  # Domain-specific anti-patterns and edge cases
  - id: gotcha-detection
    agent: foundation:zen-architect
    
  # Phase 5: REPORT
  # Synthesize findings into actionable report
  - id: synthesize-report
    agent: foundation:zen-architect
```

### When to Use Bash vs Agent Steps

| Check Type | Tool | Rationale |
|------------|------|-----------|
| File exists | bash | Deterministic, fast |
| YAML syntax valid | bash | Deterministic |
| Regex pattern match | bash | Deterministic |
| Convention assessment | agent | Requires reasoning |
| Pattern detection | agent | Requires context |
| Report synthesis | agent | Requires judgment |

---

## The Complete Validation Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                 DOMAIN VALIDATOR LIFECYCLE                      │
└─────────────────────────────────────────────────────────────────┘

Phase 1: CREATE
├── Consult domain expert agent first (understand the domain)
├── Write initial recipe from documentation + intuition
├── Include deterministic checks (regex/parsing) + agent reasoning
└── Define severity levels (likely wrong at this stage!)

Phase 2: TEST (Three-Repo Pattern)
├── Run on EXEMPLAR repo (known-good) → Should PASS
├── Run on REAL-WORLD repo → Should find some issues
└── Run on EXPERIMENTAL repo → Should find boundary cases

Phase 3: VERIFY
├── For each finding, trace to actual code
├── Use LSP: findReferences, hover, incomingCalls
├── Document evidence for each rule
└── Identify FALSE findings (both positives and negatives)

Phase 4: FIX
├── Remove/downgrade overstated rules (ERROR → WARNING)
├── Upgrade understated rules (SUGGESTION → ERROR)
├── Reword misleading messages
└── Update documentation if code differs from docs

Phase 5: RE-TEST
├── Run on all 3 repos again
├── Confirm false positives removed
└── Confirm real issues still caught

Phase 6: RESULT-VALIDATE
├── Use recipes:result-validator for objective assessment
├── Criteria: accuracy, completeness, actionability
└── Ship or iterate
```

---

## The Three-Repo Testing Pattern

Different repositories reveal different types of issues:

| Repo Type | Purpose | What It Catches |
|-----------|---------|-----------------|
| **Exemplar** | Known-good reference implementation | False positives (should pass cleanly) |
| **Real-world** | Typical usage with natural drift | True positives, edge cases |
| **Experimental** | Boundary cases, intentional deviations | Severity misclassification |

### Example from Bundle Validator

| Repo | Expected | Actual | Insight |
|------|----------|--------|---------|
| `amplifier-bundle-recipes` | PASS | ✅ PASS (95%) | Canonical exemplar confirmed |
| `amplifier-foundation` | Minor warnings | ✅ PASS (95%) | Orphaned agent in `experiments/` correctly flagged |
| `amplifier-bundle-shadow` | Some warnings | ✅ PASS (92%) | Version mismatch, unconventional location caught |

---

## Result Validation Checkpoint

After recipe-author creates or updates a validator, **MUST** validate against original intent:

```yaml
# Example: Validating the validator
- Use recipes:result-validator
- Provide: The recipe output + original intent
- Expect: PASS/FAIL with evidence
```

### Criteria for Shipping

| Criterion | Required |
|-----------|----------|
| Zero false positives on exemplar repo | ✅ Yes |
| Catches known real issues | ✅ Yes |
| Severity correctly classified | ✅ Yes |
| Actionable remediation guidance | ✅ Yes |
| Consistent scoring format | Nice to have |

---

## Documentation Alignment

When validators find discrepancies between documentation and code:

> **Rule**: Update documentation to match code, NOT the other way around.

### The Pattern

```
1. Validator assumes X based on documentation
2. Code verification shows behavior is Y
3. Update validator rule to match code (Y)
4. ALSO update documentation to match code (Y)
5. Commit both: validator fix + doc fix
```

### Example from Bundle Validator

**Finding**: Documentation said `context.include` is only for behaviors.

**Code Reality**: Supported everywhere, but has different **composition semantics** (accumulates) vs `@mentions` (in instruction which replaces).

**Actions Taken**:
1. Fixed validator to not flag `context.include` in root bundles as error
2. Updated BUNDLE_GUIDE.md to explain the **semantic difference**
3. Both committed together for consistency

---

## Exemplar Recipes

Reference these as working examples:

### Single Bundle Validation

**Recipe**: `@foundation:recipes/validate-bundle.yaml`

Validates a single bundle file for:
- Structural requirements (YAML syntax, required fields)
- Convention compliance (naming, organization)
- Common gotchas (anti-patterns, mistakes)

### Repository-Wide Validation

**Recipe**: `@foundation:recipes/validate-bundle-repo.yaml`

Validates an entire bundle repository:
- Discovers all bundle files (root, behaviors, standalone, providers)
- Validates each individually (delegates to single-bundle recipe pattern)
- Checks composition (do pieces fit together?)
- Convention compliance across the whole repo

### Using the Exemplars

```bash
# Validate a single bundle
amplifier tool invoke recipes operation=execute \
  recipe_path=foundation:recipes/validate-bundle.yaml \
  context='{"bundle_path": "/path/to/bundle.yaml"}'

# Validate entire repository
amplifier tool invoke recipes operation=execute \
  recipe_path=foundation:recipes/validate-bundle-repo.yaml \
  context='{"repo_path": "/path/to/bundle-repo"}'
```

---

## Anti-Patterns to Avoid

### ❌ Encoding Assumptions Without Verification

```yaml
# BAD: Assumed from documentation
- prompt: "Flag ERROR if inline agents are used (deprecated)"

# GOOD: Verified against code
- prompt: "Both inline and include agent patterns are valid (bundle.py:_parse_agents)"
```

### ❌ Overstating Conventions as Errors

```yaml
# BAD: Convention treated as error
findings:
  - severity: ERROR
    message: "Not using DRY pattern"

# GOOD: Convention correctly classified
findings:
  - severity: WARNING
    message: "Consider DRY pattern (RECOMMENDED, not required)"
```

### ❌ Validating Against Docs Instead of Code

```yaml
# BAD: "Documentation says X"
- prompt: "Check if bundle follows the pattern described in BUNDLE_GUIDE.md"

# GOOD: "Code enforces X"
- prompt: "Check if bundle has required fields that Bundle.from_dict() validates"
```

### ❌ Skipping Result Validation

```
# BAD: Ship after initial testing
Create recipe → Test once → Ship

# GOOD: Full validation loop
Create → Test 3 repos → Verify with code → Fix → Re-test → Result-validate → Ship
```

---

## Quick Reference: Creating a New Domain Validator

### Checklist

```
[ ] Phase 1: Domain Understanding
    [ ] Consult domain expert agent
    [ ] List all rules (code-enforced, conventions, best practices)
    [ ] For each rule, note evidence source

[ ] Phase 2: Recipe Creation
    [ ] Use recipe-author agent (don't write YAML directly)
    [ ] Follow 5-phase architecture
    [ ] Define clear severity for each check

[ ] Phase 3: Code Verification
    [ ] For each ERROR, find code enforcement point
    [ ] For each WARNING, confirm no code enforcement
    [ ] Document evidence in recipe comments

[ ] Phase 4: Three-Repo Testing
    [ ] Test on exemplar (should PASS)
    [ ] Test on real-world (should find issues)
    [ ] Test on experimental (should handle edge cases)

[ ] Phase 5: Fix and Re-test
    [ ] Remove false positives
    [ ] Adjust severity based on evidence
    [ ] Update related documentation

[ ] Phase 6: Result Validation
    [ ] Run result-validator
    [ ] Confirm: accuracy, completeness, actionability
    [ ] Ship or iterate
```

### Time Investment

| Phase | Typical Time | Notes |
|-------|--------------|-------|
| Domain understanding | 1-2 hours | Consult experts, read code |
| Initial recipe | 30 min | Use recipe-author |
| Code verification | 2-4 hours | The critical investment |
| Three-repo testing | 30 min | Automated execution |
| Fix and re-test | 1-2 hours | Depends on findings |
| Result validation | 15 min | Quick checkpoint |
| **Total** | **5-9 hours** | For production-quality validator |

---

## Summary

Building accurate domain validators requires:

1. **Code verification first** - Don't trust assumptions
2. **Correct severity classification** - ERROR vs WARNING vs SUGGESTION
3. **Three-repo testing** - Exemplar + real-world + experimental
4. **The validation loop** - Create → Test → Verify → Fix → Re-test → Validate
5. **Documentation alignment** - Update docs when code differs

The investment pays off in:
- Consistent guidance across the ecosystem
- Reduced support burden
- Faster onboarding
- Codified expertise that scales

---

## See Also

- `@foundation:recipes/validate-bundle.yaml` - Single bundle validation exemplar
- `@foundation:recipes/validate-bundle-repo.yaml` - Repository validation exemplar
- `@foundation:docs/BUNDLE_GUIDE.md` - Bundle authoring guide (updated based on validator findings)
- `@recipes:docs/RECIPE_SCHEMA.md` - Recipe authoring reference
