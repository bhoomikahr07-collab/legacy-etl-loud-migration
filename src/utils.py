"""Shared helpers: config loading."""
import os
import yaml

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "config.yaml")


def load_config(env: str) -> dict:
    with open(CONFIG_PATH) as f:
        full_config = yaml.safe_load(f)
    if env not in full_config:
        raise ValueError(f"Unknown environment '{env}'. Expected one of: dev, test, prod, local")
    return full_config[env]
