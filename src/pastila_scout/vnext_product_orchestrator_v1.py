"""Isolated product orchestrator over the published VNext core boundaries."""
from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .vnext_core_final_v1 import (
    assemble_and_export_final,
    load_exported_final,
    authorize_policy_session,
    build_policy_decision,
    enter_policy_review,
    persist_policy_decision,
)
from .vnext_editor_vertical_slice_v1 import (
    R2Backend,
    build_structural_failure,
    persist_editor_draft,
    persist_structural_failure,
    run_editor_vertical_slice,
    validate_editor_draft,
    validate_structural_failure,
)
from .vnext_factual_acceptance_v1 import (
    adjudicate,
    authorize_review_session,
    build_review_decision,
    persist_factual_result,
    validate_factual_output,
)
from .vnext_foundation_v1 import BoundaryError, contained_path, object_identity
from .vnext_scout_production_v1 import (
    CaptureFailure,
    EventGroup,
    SourceDefinition,
    ValidatedSourceSet,
    Transport,
    build_source_packet,
    capture_sources,
    persist_capture_and_grouping,
    validate_terminal_capture_outcome,
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
    invocation: Mapping[str, object] | None
    draft: Mapping[str, object] | None
    decision: Mapping[str, object]
    receipt: Mapping[str, object]
    artifact: Mapping[str, object]
    terminal_state: str | None = None
    structural_failure: Mapping[str, object] | None = None


@dataclass(frozen=True)
class ExportBundle:
    workflow_identity: str
    final: Mapping[str, object]
    receipt: Mapping[str, object]


@dataclass(frozen=True)
class PolicyTerminalBundle:
    workflow_identity: str
    state: str
    decision: Mapping[str, object]


@dataclass(frozen=True)
class EditorFailureBundle:
    workflow_identity: str
    packet: Mapping[str, object]
    failure: Mapping[str, object]


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

    def load_source_packet(self, workflow_identity: str) -> dict[str, object]:
        self.store.load_workflow(workflow_identity)
        with self.store.read() as connection:
            rows = connection.execute(
                "SELECT sp.packet_identity,sp.event_identity,sp.payload_identity,sp.payload_ref "
                "FROM source_packets sp "
                "JOIN state_transitions st ON st.output_identity=sp.packet_identity "
                "WHERE st.workflow_identity=? AND st.previous_state='SELECTED' "
                "AND st.resulting_state='SOURCE_PACKET_READY'",
                (workflow_identity,),
            ).fetchall()
        if len(rows) != 1:
            raise ProductOrchestratorError("persisted SourcePacket ownership is absent or ambiguous")
        row = rows[0]
        packet = self._load_json(str(row["payload_ref"]), "SourcePacket")
        from .vnext_scout_production_v1 import (
            validate_scout_packet,
            validate_selection_receipt,
            validate_workflow_event_membership,
        )
        try:
            validate_scout_packet(packet)
            packet_identity = str(packet["packet_identity"])
            event_identity = str(packet["event_identity"])
            validate_workflow_event_membership(
                self.store,
                workflow_identity=workflow_identity,
                event_identity=event_identity,
            )
        except BoundaryError as exc:
            raise ProductOrchestratorError(str(exc)) from exc
        selection_receipt = packet.get("selection_receipt")
        if not isinstance(selection_receipt, Mapping):
            raise ProductOrchestratorError("SourcePacket selection authority is missing")
        try:
            validate_selection_receipt(
                selection_receipt,
                event_identity=event_identity,
                workflow_identity=workflow_identity,
            )
        except BoundaryError as exc:
            raise ProductOrchestratorError(str(exc)) from exc
        persisted_selection = self._load_json(
            f"blobs/source-selections/{selection_receipt['receipt_identity']}.json",
            "source selection receipt",
        )
        if persisted_selection != selection_receipt:
            raise ProductOrchestratorError("SourcePacket selection receipt persistence mismatch")
        expected_row = (
            packet_identity,
            event_identity,
            packet_identity,
            f"blobs/source-packets/{packet_identity}.json",
        )
        if tuple(row) != expected_row:
            raise ProductOrchestratorError("SourcePacket row binding mismatch")
        selection_transition = self._require_owned_transition(
            workflow_identity=workflow_identity,
            previous_state="GROUPED",
            resulting_state="SELECTED",
            operation_identity="scout:select",
            actor=str(selection_receipt["actor"]),
            outcome="PASS",
            input_identity=event_identity,
            output_identity=event_identity,
            label="explicit source selection",
        )
        if (
            selection_receipt.get("transition_receipt_identity")
            != selection_transition.get("receipt_identity")
        ):
            raise ProductOrchestratorError(
                "SourcePacket selection transition receipt binding mismatch"
            )
        self._require_owned_transition(
            workflow_identity=workflow_identity,
            previous_state="SELECTED",
            resulting_state="SOURCE_PACKET_READY",
            operation_identity="scout:source-packet",
            actor="SCOUT",
            outcome="PASS",
            input_identity=event_identity,
            output_identity=packet_identity,
            label="SourcePacket",
        )
        return packet

    def load_editor_review_bundle(self, workflow_identity: str) -> EditorReviewBundle:
        packet = self.load_source_packet(workflow_identity)
        with self.store.read() as connection:
            draft_rows = connection.execute(
                "SELECT artifact_identity,payload_identity,payload_ref,schema_identity "
                "FROM workflow_artifacts "
                "WHERE workflow_identity=? AND artifact_kind='EDITOR_DRAFT'",
                (workflow_identity,),
            ).fetchall()
        if len(draft_rows) != 1:
            raise ProductOrchestratorError("persisted editor ownership is absent or ambiguous")
        draft = self._load_json(str(draft_rows[0]["payload_ref"]), "EditorDraft")
        receipt_identity = draft.get("invocation_receipt_identity")
        if not isinstance(receipt_identity, str):
            raise ProductOrchestratorError("EditorDraft invocation binding is missing")
        invocation = self._load_json(
            f"blobs/editor-invocations/{receipt_identity}.json",
            "EDITOR invocation",
        )
        validate_editor_draft(draft, source_packet=packet, invocation_receipt=invocation)
        draft_identity = str(draft["draft_identity"])
        expected_artifact = (
            draft_identity,
            draft_identity,
            f"blobs/editor-drafts/{draft_identity}.json",
            "vnext-editor-draft-v1",
        )
        if tuple(draft_rows[0]) != expected_artifact:
            raise ProductOrchestratorError("EditorDraft artifact binding mismatch")
        with self.store.read() as connection:
            transitions = connection.execute(
                "SELECT input_identity,output_identity FROM state_transitions "
                "WHERE workflow_identity=? AND previous_state='EDITOR_PENDING' "
                "AND resulting_state='EDITOR_DRAFT_READY'",
                (workflow_identity,),
            ).fetchall()
        if (
            len(transitions) != 1
            or transitions[0]["output_identity"] != draft.get("draft_identity")
        ):
            raise ProductOrchestratorError("EditorDraft transition ownership is absent or ambiguous")
        transition_input = str(transitions[0]["input_identity"])
        if transition_input != receipt_identity:
            retry = self._load_json(
                f"blobs/editor-retry-authorizations/{transition_input}.json",
                "EDITOR retry authorization",
            )
            required = {
                "schema", "schema_version", "workflow_identity",
                "source_packet_identity", "invocation_receipt_identity",
                "authorization_identity", "receipt_identity",
            }
            if (
                set(retry) != required
                or retry.get("schema") != "vnext-editor-retry-authorization-receipt"
                or retry.get("schema_version") != 1
                or retry.get("workflow_identity") != workflow_identity
                or retry.get("source_packet_identity") != packet.get("packet_identity")
                or retry.get("invocation_receipt_identity") != receipt_identity
                or re.fullmatch(r"[0-9a-f]{64}", str(retry.get("authorization_identity"))) is None
                or retry.get("receipt_identity") != transition_input
                or retry.get("receipt_identity") != object_identity(
                    {key: value for key, value in retry.items() if key != "receipt_identity"}
                )
            ):
                raise ProductOrchestratorError("EDITOR retry authorization binding mismatch")
        self._require_owned_transition(
            workflow_identity=workflow_identity,
            previous_state="EDITOR_PENDING",
            resulting_state="EDITOR_DRAFT_READY",
            operation_identity="editor:editor-draft",
            actor="EDITOR",
            outcome="PASS",
            input_identity=transition_input,
            output_identity=draft_identity,
            label="EditorDraft",
        )
        self._require_owned_transition(
            workflow_identity=workflow_identity,
            previous_state="EDITOR_DRAFT_READY",
            resulting_state="FACTUAL_REVIEW_PENDING",
            operation_identity="editor:editor-structural-pass",
            actor="EDITOR",
            outcome="PASS",
            input_identity=draft_identity,
            output_identity=draft_identity,
            label="EditorDraft factual review",
        )
        return EditorReviewBundle(workflow_identity, packet, invocation, draft)

    def _require_owned_transition(
        self,
        *,
        workflow_identity: str,
        previous_state: str,
        resulting_state: str,
        operation_identity: str,
        actor: str,
        outcome: str,
        input_identity: str,
        output_identity: str | None,
        label: str,
    ) -> dict[str, object]:
        with self.store.read() as connection:
            rows = connection.execute(
                "SELECT receipt_identity,operation_identity,previous_state,resulting_state,"
                "actor,outcome,input_identity,output_identity,attempt_identity,"
                "idempotency_identity,receipt_json FROM state_transitions "
                "WHERE workflow_identity=? AND previous_state=? AND resulting_state=?",
                (workflow_identity, previous_state, resulting_state),
            ).fetchall()
        if len(rows) != 1:
            raise ProductOrchestratorError(f"{label} transition ownership is absent or ambiguous")
        row = rows[0]
        expected = {
            "operation_identity": operation_identity,
            "previous_state": previous_state,
            "resulting_state": resulting_state,
            "actor": actor,
            "outcome": outcome,
            "input_identity": input_identity,
            "output_identity": output_identity,
        }
        if any(row[key] != value for key, value in expected.items()):
            raise ProductOrchestratorError(f"{label} transition binding mismatch")
        try:
            receipt = json.loads(row["receipt_json"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise ProductOrchestratorError(f"{label} transition receipt is invalid") from exc
        receipt_expected = {
            "workflow_identity": workflow_identity,
            "receipt_identity": row["receipt_identity"],
            "attempt_identity": row["attempt_identity"],
            "idempotency_identity": row["idempotency_identity"],
            **expected,
        }
        if (
            not isinstance(receipt, dict)
            or any(receipt.get(key) != value for key, value in receipt_expected.items())
            or receipt.get("receipt_identity") != object_identity({
                key: receipt.get(key) for key in (
                    "schema", "schema_version", "workflow_identity",
                    "operation_identity", "previous_state", "resulting_state",
                    "actor", "outcome", "input_identity", "output_identity",
                    "attempt_identity", "idempotency_identity",
                )
            })
        ):
            raise ProductOrchestratorError(f"{label} transition receipt binding mismatch")
        return receipt

    def load_editor_failure_bundle(self, workflow_identity: str) -> EditorFailureBundle:
        packet = self.load_source_packet(workflow_identity)
        with self.store.read() as connection:
            rows = connection.execute(
                "SELECT artifact_identity,payload_identity,payload_ref,schema_identity "
                "FROM workflow_artifacts "
                "WHERE workflow_identity=? AND artifact_kind='STRUCTURAL_FAILURE'",
                (workflow_identity,),
            ).fetchall()
        if len(rows) != 1:
            raise ProductOrchestratorError("persisted structural failure is absent or ambiguous")
        row = rows[0]
        failure = self._load_json(str(row["payload_ref"]), "structural failure")
        validate_structural_failure(failure, packet=packet)
        failure_identity = str(failure["failure_identity"])
        expected_artifact = (
            failure_identity,
            failure_identity,
            f"blobs/editor-failures/{failure_identity}.json",
            "vnext-editor-structural-failure-v1",
        )
        if tuple(row) != expected_artifact:
            raise ProductOrchestratorError("structural failure artifact binding mismatch")
        self._require_owned_transition(
            workflow_identity=workflow_identity,
            previous_state="EDITOR_PENDING",
            resulting_state="STRUCTURAL_FAIL",
            operation_identity="editor:editor-structural-fail",
            actor="EDITOR",
            outcome="PASS",
            input_identity=str(packet["packet_identity"]),
            output_identity=failure_identity,
            label="structural failure",
        )
        self._require_owned_transition(
            workflow_identity=workflow_identity,
            previous_state="STRUCTURAL_FAIL",
            resulting_state="FACTUAL_REVIEW_PENDING",
            operation_identity="editor:editor-failure-review",
            actor="EDITOR",
            outcome="PASS",
            input_identity=failure_identity,
            output_identity=failure_identity,
            label="structural failure review",
        )
        return EditorFailureBundle(workflow_identity, packet, failure)

    def _require_factual_review_session(
        self,
        *,
        workflow_identity: str,
        packet: Mapping[str, object],
        decision: Mapping[str, object],
    ) -> None:
        decision_identity = str(decision.get("decision_identity"))
        with self.store.read() as connection:
            rows = connection.execute(
                "SELECT review_session_identity,workflow_identity,issued_by,actor,"
                "source_packet_identity,input_kind,input_identity,allowed_outcome,"
                "authorization_identity,status,decision_identity,request_identity "
                "FROM review_sessions WHERE workflow_identity=? AND decision_identity=?",
                (workflow_identity, decision_identity),
            ).fetchall()
        if len(rows) != 1:
            raise ProductOrchestratorError(
                "persisted factual review-session authority is absent or ambiguous"
            )
        row = rows[0]
        authorization_identity = str(row["authorization_identity"])
        if re.fullmatch(r"[0-9a-f]{64}", authorization_identity) is None:
            raise ProductOrchestratorError(
                "persisted factual review-session authorization is invalid"
            )
        expected_request = object_identity({
            "workflow_identity": workflow_identity,
            "actor": decision.get("actor"),
            "source_packet_identity": packet.get("packet_identity"),
            "input_kind": decision.get("input_kind"),
            "input_identity": decision.get("input_identity"),
            "allowed_outcome": decision.get("outcome"),
            "authorization_identity": authorization_identity,
        })
        expected_session = {
            "schema": "vnext-factual-review-session",
            "schema_version": 2,
            "request_identity": expected_request,
            "workflow_identity": workflow_identity,
            "issued_by": self.store.writer_identity,
            "actor": decision.get("actor"),
            "source_packet_identity": packet.get("packet_identity"),
            "input_kind": decision.get("input_kind"),
            "input_identity": decision.get("input_identity"),
            "allowed_outcome": decision.get("outcome"),
            "authorization_identity": authorization_identity,
            "status": "OPEN",
        }
        session_identity = object_identity(expected_session)
        expected_row = (
            session_identity,
            workflow_identity,
            self.store.writer_identity,
            decision.get("actor"),
            packet.get("packet_identity"),
            decision.get("input_kind"),
            decision.get("input_identity"),
            decision.get("outcome"),
            authorization_identity,
            "CONSUMED",
            decision_identity,
            expected_request,
        )
        if decision.get("review_session_identity") != session_identity or tuple(row) != expected_row:
            raise ProductOrchestratorError(
                "persisted factual review-session row binding mismatch"
            )

    def load_factual_result_bundle(self, workflow_identity: str) -> FactualResultBundle:
        packet = self.load_source_packet(workflow_identity)
        with self.store.read() as connection:
            rows = connection.execute(
                "SELECT artifact_identity,payload_identity,payload_ref,schema_identity FROM workflow_artifacts "
                "WHERE workflow_identity=? AND artifact_kind IN ('ACCEPTED_SETUP','SOURCE_FALLBACK','ABSTAINED')",
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
                "SELECT decision_identity,workflow_identity,decision_kind,outcome,actor,"
                "input_identity,receipt_identity FROM decisions "
                "WHERE workflow_identity=? AND decision_identity=? AND decision_kind='FACTUAL'",
                (workflow_identity, decision_identity),
            ).fetchall()
        if len(decision_rows) != 1:
            raise ProductOrchestratorError("persisted factual decision is absent or ambiguous")
        decision_row = decision_rows[0]
        receipt = self._load_json(
            f"blobs/factual-receipts/{decision_row['receipt_identity']}.json",
            "factual receipt",
        )
        review_kind = artifact.get("review_input_kind")
        if review_kind == "EDITOR_DRAFT":
            editor = self.load_editor_review_bundle(workflow_identity)
            invocation = editor.invocation
            draft = editor.draft
            structural_failure = None
        elif review_kind == "STRUCTURAL_FAILURE":
            failure_bundle = self.load_editor_failure_bundle(workflow_identity)
            invocation = None
            draft = None
            structural_failure = failure_bundle.failure
        else:
            raise ProductOrchestratorError("unsupported factual review input kind")
        validate_factual_output(
            artifact,
            workflow_identity=workflow_identity,
            packet=packet,
            decision=decision,
            receipt=receipt,
            draft=draft,
            invocation_receipt=invocation,
            structural_failure=structural_failure,
        )
        expected_decision_row = (
            decision["decision_identity"],
            workflow_identity,
            "FACTUAL",
            decision["outcome"],
            decision["actor"],
            decision["input_identity"],
            receipt["receipt_identity"],
        )
        self._require_factual_review_session(
            workflow_identity=workflow_identity,
            packet=packet,
            decision=decision,
        )
        if tuple(decision_row) != expected_decision_row:
            raise ProductOrchestratorError("persisted factual decision binding mismatch")
        artifact_identity = str(artifact["artifact_identity"])
        expected_artifact_row = (
            artifact_identity,
            artifact_identity,
            f"blobs/factual-outputs/{artifact_identity}.json",
            "vnext-factual-output-v2",
        )
        if tuple(rows[0]) != expected_artifact_row:
            raise ProductOrchestratorError("persisted factual artifact binding mismatch")
        self._require_owned_transition(
            workflow_identity=workflow_identity,
            previous_state="FACTUAL_REVIEW_PENDING",
            resulting_state=str(artifact["artifact_kind"]),
            operation_identity="factual:adjudicate",
            actor="FACTUAL_REVIEW",
            outcome=str(decision["outcome"]),
            input_identity=str(decision["input_identity"]),
            output_identity=artifact_identity,
            label="factual result",
        )
        with self.store.read() as connection:
            transition_rows = connection.execute(
                "SELECT receipt_json FROM state_transitions WHERE workflow_identity=? "
                "AND previous_state='FACTUAL_REVIEW_PENDING' AND resulting_state=?",
                (workflow_identity, artifact["artifact_kind"]),
            ).fetchall()
        transition_receipt = json.loads(transition_rows[0]["receipt_json"])
        provenance = transition_receipt.get("provenance")
        if (
            not isinstance(provenance, dict)
            or provenance.get("decision_receipt_identity") != receipt["receipt_identity"]
        ):
            raise ProductOrchestratorError("factual result transition receipt provenance mismatch")
        return FactualResultBundle(
            workflow_identity,
            packet,
            invocation,
            draft,
            decision,
            receipt,
            artifact,
            "ABSTAINED" if artifact.get("artifact_kind") == "ABSTAINED" else None,
            structural_failure,
        )

    def load_capture_terminal_result(
        self, workflow_identity: str
    ) -> Mapping[str, object]:
        try:
            return validate_terminal_capture_outcome(
                self.store, workflow_identity=workflow_identity
            )
        except BoundaryError as exc:
            raise ProductOrchestratorError(str(exc)) from exc

    def capture_and_group(
        self,
        *,
        workflow_identity: str,
        source_set: ValidatedSourceSet,
        transport: Transport,
        captured_at: str,
        timeout: float = 20.0,
        maximum_workers: int = 8,
    ) -> tuple[tuple[EventGroup, ...], tuple[CaptureFailure, ...]]:
        if self.store.load_workflow(workflow_identity)["state"] != "DISCOVERED":
            raise ProductOrchestratorError("workflow is not ready for SCOUT capture")
        if not isinstance(source_set, ValidatedSourceSet):
            raise ProductOrchestratorError("validated SourceSet required")
        articles, failures = capture_sources(
            source_set.definitions,
            transport=transport,
            captured_at=captured_at,
            timeout=timeout,
            maximum_workers=maximum_workers,
        )
        groups = persist_capture_and_grouping(
            self.store,
            workflow_identity=workflow_identity,
            source_set=source_set,
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
        selection_actor: str,
        selection_authorization_identity: str,
        backend: R2Backend,
        source_packet_observed_at: str,
        editor_observed_at: str,
    ) -> EditorReviewBundle:
        state = str(self.store.load_workflow(workflow_identity)["state"])
        if state == "GROUPED":
            packet = build_source_packet(
                self.store,
                workflow_identity=workflow_identity,
                event_identity=selected_event_identity,
                selection_actor=selection_actor,
                selection_authorization_identity=selection_authorization_identity,
                observed_at=source_packet_observed_at,
            )
        elif state in {"SOURCE_PACKET_READY", "EDITOR_PENDING"}:
            packet = self.load_source_packet(workflow_identity)
            if packet.get("event_identity") != selected_event_identity:
                raise ProductOrchestratorError("selected event conflicts with persisted SourcePacket")
            if state == "EDITOR_PENDING":
                raise ProductOrchestratorError(
                    "EDITOR_PENDING requires explicit retry or failure disposition"
                )
        else:
            raise ProductOrchestratorError(f"workflow is not editor-routable: {state}")
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

    def retry_editor_generation(
        self,
        *,
        workflow_identity: str,
        backend: R2Backend,
        retry_authorization_identity: str,
        editor_observed_at: str,
    ) -> EditorReviewBundle:
        if re.fullmatch(r"[0-9a-f]{64}", retry_authorization_identity) is None:
            raise ProductOrchestratorError("explicit retry authorization identity required")
        if self.store.load_workflow(workflow_identity)["state"] != "EDITOR_PENDING":
            raise ProductOrchestratorError("workflow is not awaiting explicit EDITOR disposition")
        packet = self.load_source_packet(workflow_identity)
        invocation, draft = run_editor_vertical_slice(packet, backend)
        persist_editor_draft(
            self.store,
            workflow_identity=workflow_identity,
            packet=packet,
            invocation=invocation,
            draft=draft,
            observed_at=editor_observed_at,
            retry_authorization_identity=retry_authorization_identity,
        )
        return EditorReviewBundle(workflow_identity, packet, invocation, draft)

    def record_editor_failure(
        self,
        *,
        workflow_identity: str,
        failure_code: str,
        evidence_identity: str,
        observed_at: str,
    ) -> EditorFailureBundle:
        state = str(self.store.load_workflow(workflow_identity)["state"])
        if state not in {"SOURCE_PACKET_READY", "EDITOR_PENDING"}:
            raise ProductOrchestratorError("workflow is not awaiting EDITOR disposition")
        packet = self.load_source_packet(workflow_identity)
        failure = build_structural_failure(
            packet,
            failure_code=failure_code,
            evidence_identity=evidence_identity,
        )
        persist_structural_failure(
            self.store,
            workflow_identity=workflow_identity,
            packet=packet,
            failure=failure,
            observed_at=observed_at,
        )
        return EditorFailureBundle(workflow_identity, packet, failure)

    def apply_factual_review(
        self,
        bundle: EditorReviewBundle | EditorFailureBundle,
        *,
        instruction: FactualReviewInstruction,
        observed_at: str,
    ) -> FactualResultBundle:
        if bundle.workflow_identity != str(
            self.store.load_workflow(bundle.workflow_identity)["workflow_identity"]
        ):
            raise ProductOrchestratorError("workflow ownership mismatch")
        if isinstance(bundle, EditorReviewBundle):
            invocation = bundle.invocation
            draft = bundle.draft
            structural_failure = None
        elif isinstance(bundle, EditorFailureBundle):
            invocation = None
            draft = None
            structural_failure = bundle.failure
        else:
            raise ProductOrchestratorError("unsupported factual review bundle")
        session = authorize_review_session(
            self.store,
            workflow_identity=bundle.workflow_identity,
            packet=bundle.packet,
            actor=instruction.actor,
            allowed_outcome=instruction.outcome,
            authorization_identity=instruction.authorization_identity,
            draft=draft,
            invocation_receipt=invocation,
            structural_failure=structural_failure,
        )
        decision = build_review_decision(
            workflow_identity=bundle.workflow_identity,
            review_session=session,
            packet=bundle.packet,
            outcome=instruction.outcome,
            actor=instruction.actor,
            reason_code=instruction.reason_code,
            draft=draft,
            invocation_receipt=invocation,
            structural_failure=structural_failure,
            fallback_span_ids=instruction.fallback_span_ids,
        )
        receipt, artifact = adjudicate(
            workflow_identity=bundle.workflow_identity,
            packet=bundle.packet,
            decision=decision,
            draft=draft,
            invocation_receipt=invocation,
            structural_failure=structural_failure,
        )
        persist_factual_result(
            self.store,
            workflow_identity=bundle.workflow_identity,
            packet=bundle.packet,
            decision=decision,
            receipt=receipt,
            artifact=artifact,
            draft=draft,
            invocation_receipt=invocation,
            structural_failure=structural_failure,
            observed_at=observed_at,
        )
        return FactualResultBundle(
            bundle.workflow_identity,
            bundle.packet,
            invocation,
            draft,
            decision,
            receipt,
            artifact,
            "ABSTAINED" if artifact.get("artifact_kind") == "ABSTAINED" else None,
            structural_failure,
        )

    def _load_policy_decision(
        self,
        bundle: FactualResultBundle,
        instruction: PolicyInstruction,
    ) -> dict[str, object]:
        with self.store.read() as connection:
            rows = connection.execute(
                "SELECT d.decision_identity,d.workflow_identity,d.decision_kind,d.outcome,"
                "d.actor,d.input_identity,d.receipt_identity,"
                "ps.policy_session_identity,ps.request_identity,"
                "ps.workflow_identity AS session_workflow_identity,ps.issued_by,"
                "ps.actor AS session_actor,ps.input_kind,"
                "ps.input_identity AS session_input_identity,ps.allowed_outcome,"
                "ps.authorization_identity,ps.status,"
                "ps.decision_identity AS session_decision_identity "
                "FROM decisions d JOIN policy_sessions ps "
                "ON ps.decision_identity=d.decision_identity "
                "WHERE d.workflow_identity=? AND d.decision_kind='APPROVAL'",
                (bundle.workflow_identity,),
            ).fetchall()
        if len(rows) != 1:
            raise ProductOrchestratorError("persisted policy authority is absent or ambiguous")
        row = rows[0]
        decision_identity = str(row["decision_identity"])
        decision = self._load_json(
            f"blobs/policy-decisions/{decision_identity}.json",
            "policy decision",
        )
        expected_target = {
            "APPROVE_FINAL": "APPROVED_FOR_FINAL",
            "REJECT": "REJECTED",
            "REVISE": "REVISION_REQUIRED",
        }.get(instruction.outcome)
        expected_input = str(bundle.artifact["artifact_identity"])
        expected_actor = instruction.actor.strip()
        if expected_target is None:
            raise ProductOrchestratorError("unsupported policy outcome")
        if (
            decision.get("schema") != "vnext-policy-decision"
            or decision.get("schema_version") != 1
            or decision.get("decision_kind") != "APPROVAL"
            or decision.get("decision_identity") != decision_identity
            or decision.get("workflow_identity") != bundle.workflow_identity
            or decision.get("outcome") != instruction.outcome
            or decision.get("actor") != expected_actor
            or decision.get("reason_code") != instruction.reason_code.strip()
            or decision.get("input_kind") != bundle.artifact.get("artifact_kind")
            or decision.get("input_identity") != expected_input
            or decision.get("decision_identity") != object_identity(
                {key: value for key, value in decision.items() if key != "decision_identity"}
            )
        ):
            raise ProductOrchestratorError("persisted policy decision payload mismatch")
        expected_decision_receipt = object_identity({
            "decision": decision_identity,
            "target": expected_target,
        })
        decision_row_expected = {
            "workflow_identity": bundle.workflow_identity,
            "decision_kind": "APPROVAL",
            "outcome": instruction.outcome,
            "actor": expected_actor,
            "input_identity": expected_input,
            "receipt_identity": expected_decision_receipt,
        }
        if any(row[key] != value for key, value in decision_row_expected.items()):
            raise ProductOrchestratorError("persisted policy decision row binding mismatch")
        expected_request = object_identity({
            "workflow_identity": bundle.workflow_identity,
            "actor": expected_actor,
            "input_identity": expected_input,
            "allowed_outcome": instruction.outcome,
            "authorization_identity": instruction.authorization_identity,
        })
        expected_session = {
            "schema": "vnext-policy-session",
            "schema_version": 1,
            "request_identity": expected_request,
            "workflow_identity": bundle.workflow_identity,
            "issued_by": self.store.writer_identity,
            "actor": expected_actor,
            "input_kind": bundle.artifact.get("artifact_kind"),
            "input_identity": expected_input,
            "allowed_outcome": instruction.outcome,
            "authorization_identity": instruction.authorization_identity,
            "status": "OPEN",
        }
        session_identity = object_identity(expected_session)
        if decision.get("policy_session_identity") != session_identity:
            raise ProductOrchestratorError("persisted policy-session identity mismatch")
        session_row_expected = {
            "policy_session_identity": session_identity,
            "request_identity": expected_request,
            "session_workflow_identity": bundle.workflow_identity,
            "issued_by": self.store.writer_identity,
            "session_actor": expected_actor,
            "input_kind": bundle.artifact.get("artifact_kind"),
            "session_input_identity": expected_input,
            "allowed_outcome": instruction.outcome,
            "authorization_identity": instruction.authorization_identity,
            "status": "CONSUMED",
            "session_decision_identity": decision_identity,
        }
        if any(row[key] != value for key, value in session_row_expected.items()):
            raise ProductOrchestratorError("persisted policy-session row binding mismatch")
        self._require_owned_transition(
            workflow_identity=bundle.workflow_identity,
            previous_state=str(bundle.artifact["artifact_kind"]),
            resulting_state="VOICE_DISABLED",
            operation_identity="core:voice-disabled",
            actor="system",
            outcome="VOICE_DISABLED",
            input_identity=expected_input,
            output_identity=None,
            label="factual result to VOICE-disabled",
        )
        self._require_owned_transition(
            workflow_identity=bundle.workflow_identity,
            previous_state="VOICE_DISABLED",
            resulting_state="POLICY_REVIEW_PENDING",
            operation_identity="core:policy-pending",
            actor="system",
            outcome="POLICY_REQUIRED",
            input_identity=expected_input,
            output_identity=None,
            label="Policy entry",
        )
        self._require_owned_transition(
            workflow_identity=bundle.workflow_identity,
            previous_state="POLICY_REVIEW_PENDING",
            resulting_state=expected_target,
            operation_identity="core:policy-decision",
            actor="POLICY",
            outcome=instruction.outcome,
            input_identity=expected_input,
            output_identity=decision_identity,
            label="policy decision",
        )
        return decision

    def apply_policy_and_export(
        self,
        bundle: FactualResultBundle,
        *,
        instruction: PolicyInstruction,
        policy_entry_observed_at: str,
        policy_decision_observed_at: str,
        final_observed_at: str,
    ) -> ExportBundle | PolicyTerminalBundle:
        persisted_bundle = self.load_factual_result_bundle(bundle.workflow_identity)
        if persisted_bundle != bundle:
            raise ProductOrchestratorError("factual result bundle conflicts with persisted authority")
        if bundle.terminal_state == "ABSTAINED":
            raise ProductOrchestratorError("ABSTAINED is terminal and cannot enter policy")
        state = str(self.store.load_workflow(bundle.workflow_identity)["state"])
        terminal_by_outcome = {"REJECT": "REJECTED", "REVISE": "REVISION_REQUIRED"}
        if state in {"APPROVED_FOR_FINAL", "FINAL_READY", "EXPORTED", "REJECTED", "REVISION_REQUIRED"}:
            decision = self._load_policy_decision(bundle, instruction)
        else:
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
            decision = self._load_policy_decision(bundle, instruction)
            state = str(self.store.load_workflow(bundle.workflow_identity)["state"])
        if instruction.outcome in terminal_by_outcome:
            expected = terminal_by_outcome[instruction.outcome]
            if state != expected:
                raise ProductOrchestratorError("policy terminal routing mismatch")
            return PolicyTerminalBundle(bundle.workflow_identity, state, decision)
        if instruction.outcome != "APPROVE_FINAL":
            raise ProductOrchestratorError("unsupported policy outcome")
        if state == "EXPORTED":
            with self.store.read() as connection:
                rows = connection.execute(
                    "SELECT artifact_identity FROM workflow_artifacts "
                    "WHERE workflow_identity=? AND artifact_kind='FINAL_OUTPUT'",
                    (bundle.workflow_identity,),
                ).fetchall()
            if len(rows) != 1:
                raise ProductOrchestratorError("persisted FINAL ownership is absent or ambiguous")
            final, receipt = load_exported_final(
                self.store,
                workflow_identity=bundle.workflow_identity,
                final_identity=str(rows[0]["artifact_identity"]),
            )
        else:
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
