#!/usr/bin/env python3
"""End-to-end example: Load foundation bundle, select provider, execute prompt.

This interactive example demonstrates the complete workflow:
1. Load the foundation bundle (local or from GitHub)
2. Discover and display available provider bundles
3. Let user select a provider
4. Compose foundation + provider into complete mount plan
5. Let user enter a prompt
6. Execute via AmplifierSession and display response

Requirements:
- API key environment variable set for chosen provider:
  - Anthropic: ANTHROPIC_API_KEY
  - OpenAI: OPENAI_API_KEY
"""

import asyncio
import os
from pathlib import Path

from amplifier_foundation import Bundle
from amplifier_foundation import load_bundle


def discover_providers(foundation_path: Path) -> list[dict]:
    """Discover available provider bundles in the foundation."""
    providers_dir = foundation_path / "providers"
    if not providers_dir.exists():
        return []

    providers = []
    for provider_file in sorted(providers_dir.glob("*.yaml")):
        import yaml

        with open(provider_file) as f:
            data = yaml.safe_load(f)

        bundle_info = data.get("bundle", {})
        provider_config = data.get("providers", [{}])[0]

        # Determine required env var
        module = provider_config.get("module", "")
        if "anthropic" in module:
            env_var = "ANTHROPIC_API_KEY"
        elif "openai" in module:
            env_var = "OPENAI_API_KEY"
        else:
            env_var = "API_KEY"

        providers.append(
            {
                "name": bundle_info.get("name", provider_file.stem),
                "description": bundle_info.get("description", ""),
                "model": provider_config.get("config", {}).get("default_model", "unknown"),
                "file": provider_file,
                "env_var": env_var,
                "env_set": bool(os.environ.get(env_var)),
            }
        )

    return providers


def display_providers(providers: list[dict]) -> None:
    """Display available providers with status."""
    print("\nAvailable Providers:")
    print("-" * 60)

    for i, p in enumerate(providers, 1):
        status = "✓" if p["env_set"] else "✗"
        env_status = f"({p['env_var']} {'set' if p['env_set'] else 'NOT set'})"
        print(f"  [{i}] {p['name']}")
        print(f"      Model: {p['model']}")
        print(f"      Status: {status} {env_status}")
        print()


def select_provider(providers: list[dict]) -> dict | None:
    """Let user select a provider."""
    while True:
        try:
            choice = input(f"Select provider [1-{len(providers)}] (or 'q' to quit): ")
            if choice.lower() == "q":
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(providers):
                selected = providers[idx]
                if not selected["env_set"]:
                    print(f"\n⚠ {selected['env_var']} is not set.")
                    print("You can either:")
                    print("  1. Enter your API key now (will be used for this session only)")
                    print("  2. Skip and set the environment variable later")
                    api_key = input(f"\nEnter {selected['env_var']} (or press Enter to skip): ").strip()
                    if api_key:
                        selected["api_key"] = api_key
                        print("      ✓ API key provided")
                    else:
                        print("\n      Skipping - provider may fail without API key.")
                        proceed = input("      Continue anyway? [y/N]: ")
                        if proceed.lower() != "y":
                            continue
                return selected
            print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a number.")


def get_user_prompt() -> str | None:
    """Get prompt from user."""
    print("\nEnter your prompt (or 'q' to quit):")
    print("-" * 40)
    prompt = input("> ")
    if prompt.lower() == "q":
        return None
    return prompt


async def main() -> None:
    """Interactive end-to-end demo."""
    print("=" * 60)
    print("Amplifier Foundation: End-to-End Demo")
    print("=" * 60)

    # Determine foundation path (local if available, otherwise remote)
    local_foundation = Path(__file__).parent.parent.parent
    if (local_foundation / "bundle.md").exists():
        foundation_path = local_foundation
        print(f"\n[1/5] Using local foundation bundle: {foundation_path}")
    else:
        print("\n[1/5] Local foundation not found, will load from GitHub...")
        foundation_path = None

    # Load foundation bundle
    if foundation_path:
        foundation = await load_bundle(str(foundation_path), auto_include=False)
    else:
        foundation = await load_bundle(
            "git+https://github.com/microsoft/amplifier-foundation@main",
            auto_include=False,
        )
    print(f"      Loaded: {foundation.name} v{foundation.version}")
    print(f"      Tools: {len(foundation.tools)}")

    # Discover providers
    print("\n[2/5] Discovering available providers...")
    if foundation_path:
        providers = discover_providers(foundation_path)
    else:
        # For remote, we'd need to check the resolved path
        # For simplicity, define inline options
        providers = [
            {
                "name": "anthropic-sonnet",
                "description": "Anthropic Claude Sonnet",
                "model": "claude-sonnet-4-5",
                "env_var": "ANTHROPIC_API_KEY",
                "env_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
                "inline": {
                    "module": "provider-anthropic",
                    "source": "git+https://github.com/microsoft/amplifier-module-provider-anthropic@main",
                    "config": {"default_model": "claude-sonnet-4-5"},
                },
            },
            {
                "name": "anthropic-opus",
                "description": "Anthropic Claude Opus",
                "model": "claude-opus-4-5",
                "env_var": "ANTHROPIC_API_KEY",
                "env_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
                "inline": {
                    "module": "provider-anthropic",
                    "source": "git+https://github.com/microsoft/amplifier-module-provider-anthropic@main",
                    "config": {"default_model": "claude-opus-4-5"},
                },
            },
            {
                "name": "openai-gpt",
                "description": "OpenAI GPT",
                "model": "gpt-4o",
                "env_var": "OPENAI_API_KEY",
                "env_set": bool(os.environ.get("OPENAI_API_KEY")),
                "inline": {
                    "module": "provider-openai",
                    "source": "git+https://github.com/microsoft/amplifier-module-provider-openai@main",
                    "config": {"default_model": "gpt-4o"},
                },
            },
        ]

    if not providers:
        print("      No providers found!")
        return

    print(f"      Found {len(providers)} provider(s)")
    display_providers(providers)

    # Select provider
    print("[3/5] Select a provider...")
    selected = select_provider(providers)
    if not selected:
        print("\nExiting.")
        return

    print(f"\n      Selected: {selected['name']} ({selected['model']})")

    # Load/create provider bundle
    print("\n[4/5] Composing bundles...")
    if "file" in selected:
        # Load from file
        provider_bundle = await load_bundle(str(selected["file"]))
        # If user provided API key, inject it into the provider config
        if "api_key" in selected and provider_bundle.providers:
            provider_bundle.providers[0].setdefault("config", {})["api_key"] = selected["api_key"]
    else:
        # Create inline - include api_key if user provided it
        provider_config = dict(selected["inline"])
        if "api_key" in selected:
            provider_config.setdefault("config", {})["api_key"] = selected["api_key"]
        provider_bundle = Bundle(
            name=selected["name"],
            version="1.0.0",
            providers=[provider_config],
        )

    # Compose
    composed = foundation.compose(provider_bundle)

    # Prepare bundle - downloads and activates all modules
    print("      Preparing modules (downloading and installing)...")
    prepared = await composed.prepare()

    mount_plan = prepared.mount_plan
    print(f"      Session: {mount_plan.get('session', {}).get('orchestrator', {}).get('module', 'default')}")
    print(f"      Providers: {len(mount_plan.get('providers', []))}")
    print(f"      Tools: {len(mount_plan.get('tools', []))}")

    # Get user prompt
    prompt = get_user_prompt()
    if not prompt:
        print("\nExiting.")
        return

    # Execute
    print("\n[5/5] Executing via AmplifierSession...")
    print("-" * 60)

    try:
        # Use PreparedBundle.create_session() which properly mounts the resolver
        session = await prepared.create_session()
        async with session:
            response = await session.execute(prompt)
            print(f"\nResponse:\n{response}")

    except ImportError:
        print("ERROR: amplifier-core not installed")
        print("Install with: pip install amplifier-core")
        print("\nMount plan was successfully created:")
        _print_mount_plan_summary(mount_plan)
    except Exception as e:
        print(f"Execution error: {e}")
        print("\nMount plan for debugging:")
        _print_mount_plan_summary(mount_plan)

    print("\n" + "=" * 60)
    print("Demo complete")
    print("=" * 60)


def _print_mount_plan_summary(mount_plan: dict) -> None:
    """Print a summary of the mount plan."""
    import json

    summary = {
        "session": mount_plan.get("session", {}),
        "providers": [
            {"module": p.get("module"), "model": p.get("config", {}).get("default_model")}
            for p in mount_plan.get("providers", [])
        ],
        "tools": [t.get("module") for t in mount_plan.get("tools", [])],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
