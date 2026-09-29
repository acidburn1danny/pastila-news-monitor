"""Isolated product orchestrator over the published VNext core boundaries."""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .vnext_core_final_v1 import (
    assemble_and_export_final,
    authorize_policy_session,
    build_policy_decision,
    enter_policy_review,
    persist_policy_decision,
)
from .vnext_editor_vertical_slice_v1 import (
    R2Backend,
    persist_editor_draft,
    run_editor_vertical_slice,
    validate_editor_draft,
)
from .vnext_factual_acceptance_v1 import (
    adjudicate,
    authorize_review_session,
    build_review_decision,
    persist_factual_result,
    validate_factual_output,
)
from .vnext_foundation_v1 import BoundaryError, contained_path
from .vnext_scout_production_v1 import (
    CaptureFailure,
    EventGroup,
    SourceDefinition,
    Transport,
    build_source_packet,
    capture_sources,
    persist_capture_and_grouping,
)
from .vnext_state_sqlite_v1 import SQLiteStateStore


class ProductOrchestratorError(BoundaryError):
    pass


@dataclass(frozen=True)
class FactualReviewInstruction:
    actor: str
    outcome: str
    authorization_identity: str
    reason_code: str
    fallback_span_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class PolicyInstruction:
    actor: str
    outcome: str
    authorization_identity: str
    reason_code: str


@dataclass(frozen=True)
class WorkflowTimes:
    capture: str
    source_packet: str
    editor: str
    factual_review: str
    policy_entry: str
    policy_decision: str
    final: str


@dataclass(frozen=True)
class EditorReviewBundle:
    workflow_identity: str
    packet: Mapping[str, object]
    invocation: Mapping[str, object]
    draft: Mapping[str, object]


@dataclass(frozen=True)
class FactualResultBundle:
    workflow_identity: str
    packet: Mapping[str, object]
    invocation: Mapping[str, object]
    draft: Mapping[str, object]
    decision: Mapping[str, object]
    receipt: Mapping[str, object]
    artifact: Mapping[str, object]


@dataclass(frozen=True)
class ExportBundle:
    workflow_identity: str
    final: Mapping[str, object]
    receipt: Mapping[str, object]


class ProductOrchestrator:
    """Coordinates active boundaries without acquiring their decision authority."""

    def __init__(self, store: SQLiteStateStore):
        self.store = store

    def create_workflow(self, workflow_identity: str) -> None:
        self.store.create_workflow(workflow_identity)

    def _load_json(self, relative: str, label: str) -> dict[str, object]:
        try:
            path = contained_path(self.store.root, Path(relative), allow_missing=False)
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, BoundaryError) as exc:
            raise ProductOrchestratorError(f"{label} is missing or invalid") from exc
        if not isinstance(value, dict):
            raise ProductOrchestratorError(f"{label} must be an object")
        return value

    def load_editor_review_bundle(self, workflow_identity: str) -> EditorReviewBundle:
        self.store.load_workflow(workflow_identity)
        with self.store.read() as connection:
            packet_rows = connection.execute(
                "SELECT sp.payload_ref FROM source_packets sp "
                "JOIN state_transitions st ON st.output_identity=sp.packet_identity "
                "WHERE st.workflow_identity=? AND st.resulting_state='SOURCE_PACKET_READY'",
                (workflow_identity,),
            ).fetchall()
            draft_rows = connection.execute(
                "SELECT payload_ref FROM workflow_artifacts "
                "WHERE workflow_identity=? AND artifact_kind='EDITOR_DRAFT'",
                (workflow_identity,),
            ).fetchall()
        if len(packet_rows) != 1 or len(draft_rows) != 1:
            raise ProductOrchestratorError("persisted editor ownership is absent or ambiguous")
        packet = self._load_json(str(packet_rows[0]["payload_ref"]), "SourcePacket")
        draft = self._load_json(str(draft_rows[0]["payload_ref"]), "EditorDraft")
        receipt_identity = draft.get("invocation_receipt_identity")
        if not isinstance(receipt_identity, str):
            raise ProductOrchestratorError("EditorDraft invocation binding is missing")
        invocation = self._load_json(
            f"blobs/editor-invocations/{receipt_identity}.json",
            "EDITOR invocation",
        )
        validate_editor_draft(
            draft,
            source_packet=packet,
            invocation_receipt=invocation,
        )
        return EditorReviewBundle(workflow_identity, packet, invocation, draft)

    def load_factual_result_bundle(self, workflow_identity: str) -> FactualResultBundle:
        editor = self.load_editor_review_bundle(workflow_identity)
        with self.store.read() as connection:
            rows = connection.execute(
                "SELECT artifact_identity,payload_ref FROM workflow_artifacts "
                "WHERE workflow_identity=? AND artifact_kind IN ('ACCEPTED_SETUP','SOURCE_FALLBACK')",
                (workflow_identity,),
            ).fetchall()
        if len(rows) != 1:
            raise ProductOrchestratorError("persisted factual ownership is absent or ambiguous")
        artifact = self._load_json(str(rows[0]["payload_ref"]), "factual output")
        decision_identity = artifact.get("decision_identity")
        if not isinstance(decision_identity, str):
            raise ProductOrchestratorError("factual decision binding is missing")
        decision = self._load_json(
            f"blobs/factual-decisions/{decision_identity}.json",
            "factual decision",
        )
        with self.store.read() as connection:
            decision_rows = connection.execute(
                "SELECT receipt_identity FROM decisions "
                "WHERE workflow_identity=? AND decision_identity=? AND decision_kind='FACTUAL'",
                (workflow_identity, decision_identity),
            ).fetchall()
        if len(decision_rows) != 1:
            raise ProductOrchestratorError("persisted factual decision is absent or ambiguous")
        receipt = self._load_json(
            f"blobs/factual-receipts/{decision_rows[0]['receipt_identity']}.json",
            "factual receipt",
        )
        validate_factual_output(
            artifact,
            workflow_identity=workflow_identity,
            packet=editor.packet,
            decision=decision,
            receipt=receipt,
            draft=editor.draft,
            invocation_receipt=editor.invocation,
        )
        return FactualResultBundle(
            workflow_identity,
            editor.packet,
            editor.invocation,
            editor.draft,
            decision,
            receipt,
            artifact,
        )

    def capture_and_group(
        self,
        *,
        workflow_identity: str,
        sources_identity: str,
        sources: Sequence[SourceDefinition],
        transport: Transport,
        captured_at: str,
        timeout: float = 20.0,
        maximum_workers: int = 8,
    ) -> tuple[tuple[EventGroup, ...], tuple[CaptureFailure, ...]]:
        if self.store.load_workflow(workflow_identity)["state"] != "DISCOVERED":
            raise ProductOrchestratorError("workflow is not ready for SCOUT capture")
        articles, failures = capture_sources(
            sources,
            transport=transport,
            captured_at=captured_at,
            timeout=timeout,
            maximum_workers=maximum_workers,
        )
        groups = persist_capture_and_grouping(
            self.store,
            workflow_identity=workflow_identity,
            sources_identity=sources_identity,
            articles=articles,
            failures=failures,
            observed_at=captured_at,
        )
        return groups, failures

    def select_and_generate_editor_draft(
        self,
        *,
        workflow_identity: str,
        selected_event_identity: str,
        backend: R2Backend,
        source_packet_observed_at: str,
        editor_observed_at: str,
    ) -> EditorReviewBundle:
        if self.store.load_workflow(workflow_identity)["state"] != "GROUPED":
            raise ProductOrchestratorError("workflow is not ready for explicit event selection")
        packet = build_source_packet(
            self.store,
            workflow_identity=workflow_identity,
            event_identity=selected_event_identity,
            observed_at=source_packet_observed_at,
        )
        invocation, draft = run_editor_vertical_slice(packet, backend)
        persist_editor_draft(
            self.store,
            workflow_identity=workflow_identity,
            packet=packet,
            invocation=invocation,
            draft=draft,
            observed_at=editor_observed_at,
        )
        return EditorReviewBundle(workflow_identity, packet, invocation, draft)

    def apply_factual_review(
        self,
        bundle: EditorReviewBundle,
        *,
        instruction: FactualReviewInstruction,
        observed_at: str,
    ) -> FactualResultBundle:
        if bundle.workflow_identity != str(
            self.store.load_workflow(bundle.workflow_identity)["workflow_identity"]
        ):
            raise ProductOrchestratorError("workflow ownership mismatch")
        session = authorize_review_session(
            self.store,
            workflow_identity=bundle.workflow_identity,
            packet=bundle.packet,
            actor=instruction.actor,
            allowed_outcome=instruction.outcome,
            authorization_identity=instruction.authorization_identity,
            draft=bundle.draft,
            invocation_receipt=bundle.invocation,
        )
        decision = build_review_decision(
            workflow_identity=bundle.workflow_identity,
            review_session=session,
            packet=bundle.packet,
            outcome=instruction.outcome,
            actor=instruction.actor,
            reason_code=instruction.reason_code,
            draft=bundle.draft,
            invocation_receipt=bundle.invocation,
            fallback_span_ids=instruction.fallback_span_ids,
        )
        receipt, artifact = adjudicate(
            workflow_identity=bundle.workflow_identity,
            packet=bundle.packet,
            decision=decision,
            draft=bundle.draft,
            invocation_receipt=bundle.invocation,
        )
        persist_factual_result(
            self.store,
            workflow_identity=bundle.workflow_identity,
            packet=bundle.packet,
            decision=decision,
            receipt=receipt,
            artifact=artifact,
            draft=bundle.draft,
            invocation_receipt=bundle.invocation,
            observed_at=observed_at,
        )
        return FactualResultBundle(
            bundle.workflow_identity,
            bundle.packet,
            bundle.invocation,
            bundle.draft,
            decision,
            receipt,
            artifact,
        )

    def apply_policy_and_export(
        self,
        bundle: FactualResultBundle,
        *,
        instruction: PolicyInstruction,
        policy_entry_observed_at: str,
        policy_decision_observed_at: str,
        final_observed_at: str,
    ) -> ExportBundle:
        if instruction.outcome != "APPROVE_FINAL":
            raise ProductOrchestratorError(
                "isolated export path requires explicit APPROVE_FINAL authority"
            )
        enter_policy_review(
            self.store,
            workflow_identity=bundle.workflow_identity,
            factual_output=bundle.artifact,
            observed_at=policy_entry_observed_at,
        )
        session = authorize_policy_session(
            self.store,
            workflow_identity=bundle.workflow_identity,
            factual_output=bundle.artifact,
            actor=instruction.actor,
            allowed_outcome=instruction.outcome,
            authorization_identity=instruction.authorization_identity,
        )
        decision = build_policy_decision(
            workflow_identity=bundle.workflow_identity,
            factual_output=bundle.artifact,
            session=session,
            outcome=instruction.outcome,
            actor=instruction.actor,
            reason_code=instruction.reason_code,
        )
        persist_policy_decision(
            self.store,
            workflow_identity=bundle.workflow_identity,
            factual_output=bundle.artifact,
            session=session,
            decision=decision,
            observed_at=policy_decision_observed_at,
        )
        final, receipt = assemble_and_export_final(
            self.store,
            workflow_identity=bundle.workflow_identity,
            factual_output=bundle.artifact,
            decision=decision,
            observed_at=final_observed_at,
        )
        return ExportBundle(bundle.workflow_identity, final, receipt)


def bootstrap_store(root: Path, *, writer_identity: str) -> SQLiteStateStore:
    root.mkdir(parents=True, exist_ok=True)
    store = SQLiteStateStore(
        root=root,
        database=Path("state.db"),
        writer_identity=writer_identity,
    )
    store.bootstrap()
    return store
