"""Load .env (secrets only) + config.yaml (everything else).

Single source of truth :
- .env       → secrets + host paths + container-side env vars only.
                 (API_BASE_URL, API_KEY, OPENWEBUI_*, HOST_*, *_PORT, *_INTERVAL_SECONDS)
- config.yaml → application config (models, retry, agents, rag, scanning, …).

No overlap : a value lives in exactly one place. If you need to know where a
knob lives, this is the rule :
- it's a secret or a host-side path → .env
- it tunes runtime behaviour       → config.yaml
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


_REQUIRED_ENV_VARS = ("API_BASE_URL", "API_KEY")


def load_config(config_path: str = "config.yaml") -> dict[str, Any]:
    """Load .env then layer on config.yaml. Returns the merged dict."""
    repo_root = Path(__file__).parent.parent

    # Secrets from .env
    load_dotenv(repo_root / ".env")

    # Application config from YAML
    yaml_path = repo_root / config_path
    if not yaml_path.exists():
        raise FileNotFoundError(f"Missing {yaml_path}. Copy config.yaml from the repo.")
    with open(yaml_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    # Pull only what genuinely belongs in .env
    cfg["_defaults"] = {
        "api_base_url": os.getenv("API_BASE_URL", ""),
        "api_key":      os.getenv("API_KEY", ""),
    }

    # Retry policy is part of config.yaml now (was env).
    retry = cfg.setdefault("retry", {})
    retry.setdefault("max_attempts", 8)
    retry.setdefault("base_delay_s", 2.0)
    retry.setdefault("max_delay_s", 120.0)

    # Paths (runtime, Python-side)
    paths = cfg.setdefault("paths", {})
    paths.setdefault("workspace", "workspace")
    paths.setdefault("vectordb", ".vectordb")
    paths.setdefault("graphdb", ".graphdb")
    paths.setdefault("context", "context")

    # Validate required secrets
    missing = [v for v in _REQUIRED_ENV_VARS if not os.getenv(v)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Set them in .env (see .env.example)."
        )

    return cfg


def get_model_for_agent(cfg: dict, agent_name: str) -> str:
    """Resolve the model ID for a given agent."""
    agent_cfg = cfg.get("agents", {}).get(agent_name, {})
    model_alias = agent_cfg.get("model", "heavy")
    return cfg["models"].get(model_alias, model_alias)


def get_agent_temperature(cfg: dict, agent_name: str) -> float:
    return cfg.get("agents", {}).get(agent_name, {}).get("temperature", 0.5)


def get_agent_extra_params(cfg: dict, agent_name: str) -> dict:
    """Extra API kwargs (e.g. reasoning_effort). Provider ignores unknown keys."""
    return cfg.get("agents", {}).get(agent_name, {}).get("extra_params", {})


# ── Optional context builders (kept for backwards compat with existing call sites) ──

def build_custom_dsl_context(cfg: dict) -> str:
    """Return the DSL section to inject in agent prompts (empty if none)."""
    dsl = cfg.get("custom_dsl", {})
    if not dsl:
        return ""
    parts = []
    for key, val in dsl.items():
        parts.append(f"- **{key}**: {val}")
    return "\n".join(parts)


def build_domain_context(cfg: dict) -> str:
    """Return the domain section to inject in agent prompts (empty if none)."""
    dom = cfg.get("domain", {})
    if not dom:
        return ""
    parts = []
    sector = dom.get("sector")
    product = dom.get("product_type")
    if sector:
        parts.append(f"- **Sector**: {sector}")
    if product:
        parts.append(f"- **Product type**: {product}")
    return "\n".join(parts)
