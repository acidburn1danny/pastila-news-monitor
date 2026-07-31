"""Opt-in one-request validation for the corrected Part 5B provider DTO."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from validate_openai_controlled_revision_e2e import SCENARIOS, execute_scenario

from pastila_scout.ai.provider import resolve_openai_api_key
from pastila_scout.config import load_application_config

OPT_IN = "SCOUT_RUN_LIVE_OPENAI_PART5B"


def main() -> int:
    app = load_application_config(Path("config/config.yaml"))
    available = resolve_openai_api_key() is not None
    print("Controlled Revision Part 5B live smoke — Preflight")
    print("Provider: openai")
    print(f"Configured model: {app.ai.model}")
    print("Schema: controlled_revision_patch_v1")
    print("Maximum attempts: 1")
    print("Live-request budget: 1")
    print(f"Credential available: {'YES' if available else 'NO'}")
    if not available:
        print("Status: STOPPED — approved credential unavailable")
        return 2
    if os.environ.get(OPT_IN) != "1":
        print(f"Status: SKIPPED — set {OPT_IN}=1 for one live request")
        print("SDK requests: 0")
        return 0

    result = execute_scenario(SCENARIOS[0], 1, app.ai.model)
    print(f"Status: {'PASS' if result.passed else 'FAIL'}")
    print(f"Classification: {result.classification}")
    print(f"Runtime attempts: {result.attempts}")
    print(f"SDK requests: {result.sdk_requests}")
    print(f"Projection count: {result.projections}")
    print(f"Credential resolutions: {result.credential_resolutions}")
    print(f"SDK client constructions: {result.sdk_constructions}")
    print(f"Interpretations: {result.interpretations}")
    print(f"Gateway results: {result.gateway_results}")
    print(f"Input tokens: {result.prompt_tokens}")
    print(f"Output tokens: {result.completion_tokens}")
    print(f"Total tokens: {result.total_tokens}")
    print(f"Duration milliseconds: {result.duration_ms:.0f}")
    print(
        "Provider request ID available: "
        f"{'YES' if result.request_id_available else 'NO'}"
    )
    print(
        "Returned model ID available: "
        f"{'YES' if result.model_id_available else 'NO'}"
    )
    print(f"Safe reporting: {'PASS' if result.passed else 'FAIL'}")
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
