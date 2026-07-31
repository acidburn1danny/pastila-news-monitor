"""Deterministic UTF-8-safe renderers for structural composition artifacts."""

from pydantic import BaseModel

from .fingerprint import canonical_json


def render_artifact(artifact: BaseModel) -> str:
    """Render canonical reference-only JSON without volatile metadata."""
    return canonical_json(artifact, indent=2) + "\n"


__all__ = ("render_artifact",)
