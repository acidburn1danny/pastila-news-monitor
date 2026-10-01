"""Canonical GUI adapter over the existing VNext product boundary."""
from __future__ import annotations

import html
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .vnext_product_orchestrator_v1 import FactualReviewInstruction, PolicyInstruction, ProductOrchestrator

VOICE_STATE = "DISABLED_UNTIL_PROMOTION"
_ACTIONS: dict[str, tuple[str, ...]] = {
    "DISCOVERED": ("capture",), "CAPTURED": ("group",), "GROUPED": ("select",),
    "EDITOR_DRAFT_READY": ("factual_review",), "FACTUAL_REVIEW_PENDING": ("factual_review",),
    "ACCEPTED_SETUP": ("policy",), "SOURCE_FALLBACK": ("policy",),
    "VOICE_DISABLED": ("policy",), "POLICY_REVIEW_PENDING": ("policy",),
    "APPROVED_FOR_FINAL": ("export",), "FINAL_READY": ("export",),
}

class GuiBoundaryError(RuntimeError):
    pass

@dataclass(frozen=True)
class GuiView:
    workflow_identity: str
    workflow_state: str
    allowed_actions: tuple[str, ...]
    voice_state: str = VOICE_STATE
    terminal: bool = False
    def as_dict(self) -> dict[str, object]:
        return asdict(self)

class CanonicalProductGui:
    """Presentation adapter; all product mutation stays in ProductOrchestrator."""
    def __init__(self, *, product_root: Path, orchestrator: ProductOrchestrator, canonical_startup: Callable[[Path], Mapping[str, object]]) -> None:
        self.product_root = product_root.resolve(strict=True)
        self.orchestrator = orchestrator
        result = dict(canonical_startup(self.product_root))
        if result.get("status") != "PASS_STARTUP_READY":
            raise GuiBoundaryError("canonical startup did not pass")
        if result.get("legacy_dependency_count") != 0:
            raise GuiBoundaryError("legacy dependency closure failed")
        self.startup_result = result

    def snapshot(self, workflow_identity: str) -> GuiView:
        state = str(self.orchestrator.store.load_workflow(workflow_identity)["state"])
        terminal = state in {"EXPORTED","REJECTED","REVISION_REQUIRED","ABSTAINED","CAPTURE_FAILED","NO_ELIGIBLE_CONTENT","EDITOR_FAILED","FACTUAL_ACCEPTANCE_FAILED","VOICE_UNAVAILABLE","FINAL_ASSEMBLY_FAILED"}
        return GuiView(workflow_identity, state, () if terminal else _ACTIONS.get(state, ()), terminal=terminal)

    def create_workflow(self, workflow_identity: str) -> GuiView:
        self.orchestrator.create_workflow(workflow_identity)
        return self.snapshot(workflow_identity)

    def capture_and_group(self, **kwargs: Any):
        return self.orchestrator.capture_and_group(**kwargs)

    def select_and_generate_editor_draft(self, **kwargs: Any):
        return self.orchestrator.select_and_generate_editor_draft(**kwargs)

    def apply_factual_review(self, workflow_identity: str, *, instruction: FactualReviewInstruction, observed_at: str):
        bundle = self.orchestrator.load_editor_review_bundle(workflow_identity)
        return self.orchestrator.apply_factual_review(bundle, instruction=instruction, observed_at=observed_at)

    def apply_policy_and_export(self, workflow_identity: str, *, instruction: PolicyInstruction, policy_entry_observed_at: str, policy_decision_observed_at: str, final_observed_at: str):
        bundle = self.orchestrator.load_factual_result_bundle(workflow_identity)
        return self.orchestrator.apply_policy_and_export(bundle, instruction=instruction, policy_entry_observed_at=policy_entry_observed_at, policy_decision_observed_at=policy_decision_observed_at, final_observed_at=final_observed_at)

    def recover(self, workflow_identity: str) -> GuiView:
        view = self.snapshot(workflow_identity)
        state = view.workflow_state
        if state in {"EDITOR_DRAFT_READY", "FACTUAL_REVIEW_PENDING"}:
            self.orchestrator.load_editor_review_bundle(workflow_identity)
        elif state in {"ACCEPTED_SETUP","SOURCE_FALLBACK","ABSTAINED","VOICE_DISABLED","POLICY_REVIEW_PENDING","APPROVED_FOR_FINAL","FINAL_READY","EXPORTED","REJECTED","REVISION_REQUIRED"}:
            self.orchestrator.load_factual_result_bundle(workflow_identity)
        return view

def render_html(view: GuiView) -> str:
    workflow = html.escape(view.workflow_identity, quote=True)
    state = html.escape(view.workflow_state, quote=True)
    actions = "".join(f'<li data-action="{html.escape(a, quote=True)}">{html.escape(a)}</li>' for a in view.allowed_actions)
    return "<!doctype html><html lang=\"ro\"><head><meta charset=\"utf-8\"><title>Pastila VNext</title></head><body>" + f"<main data-workflow=\"{workflow}\"><h1>Pastila VNext</h1><p id=\"workflow-state\">{state}</p><p id=\"voice-state\">{VOICE_STATE}</p><ul id=\"allowed-actions\">{actions}</ul></main></body></html>"
