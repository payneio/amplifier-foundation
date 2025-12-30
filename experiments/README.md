# Experimental Bundles

This directory contains experimental bundle configurations for testing new ideas and patterns before potentially promoting them to the main foundation bundle.

## Available Experiments

### `delegation-only/`

**Status**: Active Experiment

A bundle that has **NO direct tool access** - the coordinator must delegate ALL work to specialized agents. This tests:

1. **Context offloading** - Agents handle heavy exploration, return summaries
2. **Reduced context bloat** - Main conversation stays clean and focused
3. **Effective delegation patterns** - How to communicate with stateless agents

**To use:**
```bash
amplifier bundle use foundation:experiments/delegation-only
```

**Key insight**: Agents cannot see the main conversation history, and the coordinator cannot see agent internal work. This means:
- Provide COMPLETE context in every delegation
- Specify EXACTLY what information to return
- Assume agents know NOTHING about prior work

## Adding New Experiments

1. Create a new directory under `experiments/`
2. Add a `bundle.md` with the bundle definition
3. Add any custom agents in an `agents/` subdirectory
4. Update this README with the experiment description
5. Document the hypothesis and what you're testing

## Promotion Path

Experiments that prove successful may be:
- Merged into the main `foundation` bundle as options
- Extracted to their own standalone bundle
- Used to inform changes to existing patterns

## Guidelines

- Keep experiments focused on a single idea/hypothesis
- Document what you're testing and why
- Include instructions for others to try it
- Note any limitations or known issues
