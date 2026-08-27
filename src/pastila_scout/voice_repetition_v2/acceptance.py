"""Recoverable atomic acceptance for deterministic Voice commentary previews."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from pastila_scout.editor.generation.semantic_draft_v2 import (
    AcidCommentaryExecutionProvenanceV2,
    AcidCommentaryV2,
    PastilaEditorSemanticDraftV2,
    SemanticDraftModeV2,
)
from pastila_scout.voice_executor_v2 import DeterministicVoiceExecutorV2
from pastila_scout.voice_executor_v2.models import (
    DeterministicBackendKindV2,
    DeterministicTerminalKindV2,
    VoiceGeneratedResultV2,
)
from pastila_scout.voice_fact_atoms_v2.persistence import (
    canonical_bytes,
    canonical_identity,
)
from pastila_scout.voice_workflow_v2 import semantic_draft_revision_identity

from .ledger import (
    derive_repetition_snapshot_v1,
    effective_uses_v1,
    finalize_ledger_v1,
    finalize_order_authority_v1,
)
from .models import (
    ZERO,
    AcceptanceCandidatePreviewV1,
    CommittedVoiceUseV1,
    RepetitionLedgerEventKindV1,
    RepetitionLedgerEventV1,
    VoiceAcceptanceReceiptV1,
    VoiceAcceptanceRequestV1,
    VoiceRepetitionLedgerV1,
)
from .persistence import atomic_write, load_ledger, load_receipt


class VoiceAcceptanceIntegrityError(ValueError):
    pass


class SimulatedAcceptanceCrash(RuntimeError):
    pass


class _Pointer(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_name: Literal["pastilaacida-voice-acceptance-current"] = (
        "pastilaacida-voice-acceptance-current"
    )
    schema_version: Literal["1"] = "1"
    transaction_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    ledger_relative_path: str
    receipt_relative_path: str
    draft_relative_path: str
    pointer_identity: str = ZERO


def _seal(value, field: str) -> str:
    return canonical_identity(value.model_copy(update={field: ZERO}))


def finalize_candidate_v1(value: AcceptanceCandidatePreviewV1):
    return value.model_copy(
        update={"candidate_identity": _seal(value, "candidate_identity")}
    )


def finalize_acceptance_request_v1(value: VoiceAcceptanceRequestV1):
    return value.model_copy(
        update={"request_identity": _seal(value, "request_identity")}
    )


def _finalize_receipt(value: VoiceAcceptanceReceiptV1):
    return value.model_copy(
        update={"receipt_identity": _seal(value, "receipt_identity")}
    )


class VoiceAtomicAcceptanceStoreV1:
    """A current-pointer protocol: staged files are invisible until pointer swap."""

    def __init__(self, root: Path):
        self.root = root
        self.transactions = root / "transactions"
        self.pointer = root / "current.json"

    def _empty_ledger(self) -> VoiceRepetitionLedgerV1:
        return finalize_ledger_v1(VoiceRepetitionLedgerV1())

    def current_ledger(self) -> VoiceRepetitionLedgerV1:
        if not self.pointer.exists():
            return self._empty_ledger()
        raw = self.pointer.read_bytes()
        try:
            payload = json.loads(raw.decode("utf-8"))
            pointer = _Pointer.model_validate(payload)
        except Exception as exc:
            raise VoiceAcceptanceIntegrityError("invalid acceptance pointer") from exc
        if canonical_bytes(pointer) != raw or pointer.pointer_identity != _seal(
            pointer, "pointer_identity"
        ):
            raise VoiceAcceptanceIntegrityError("noncanonical acceptance pointer")
        ledger = load_ledger(self.root / pointer.ledger_relative_path)
        receipt = json.loads(
            (self.root / pointer.receipt_relative_path).read_text(encoding="utf-8")
        )
        if (
            ledger.ledger_identity != receipt.get("committed_repetition_identity")
            or receipt.get("transaction_identity") != pointer.transaction_identity
        ):
            raise VoiceAcceptanceIntegrityError("orphan acceptance pointer")
        draft_path = self.root / pointer.draft_relative_path
        draft = PastilaEditorSemanticDraftV2.model_validate_json(
            draft_path.read_bytes()
        )
        if semantic_draft_revision_identity(draft) != (
            receipt.get("resulting_semantic_draft_revision_identity")
        ):
            raise VoiceAcceptanceIntegrityError("orphan accepted commentary revision")
        return ledger

    def current_draft(self) -> PastilaEditorSemanticDraftV2 | None:
        if not self.pointer.exists():
            return None
        pointer = _Pointer.model_validate_json(self.pointer.read_bytes())
        return PastilaEditorSemanticDraftV2.model_validate_json(
            (self.root / pointer.draft_relative_path).read_bytes()
        )

    def current_receipt(self) -> VoiceAcceptanceReceiptV1 | None:
        if not self.pointer.exists():
            return None
        pointer = _Pointer.model_validate_json(self.pointer.read_bytes())
        return load_receipt(self.root / pointer.receipt_relative_path)

    def _publish_state(
        self,
        *,
        transaction_identity: str,
        ledger_path: Path,
        receipt_path: Path,
        draft_path: Path,
    ) -> None:
        pointer = _Pointer(
            transaction_identity=transaction_identity,
            ledger_relative_path=str(ledger_path.relative_to(self.root)).replace(
                "\\", "/"
            ),
            receipt_relative_path=str(receipt_path.relative_to(self.root)).replace(
                "\\", "/"
            ),
            draft_relative_path=str(draft_path.relative_to(self.root)).replace(
                "\\", "/"
            ),
        )
        pointer = pointer.model_copy(
            update={"pointer_identity": _seal(pointer, "pointer_identity")}
        )
        atomic_write(self.pointer, canonical_bytes(pointer))

    def _validate_request(self, request: VoiceAcceptanceRequestV1, ledger):
        if finalize_acceptance_request_v1(request) != request:
            raise VoiceAcceptanceIntegrityError("acceptance request identity mismatch")
        candidate = request.candidate
        if finalize_candidate_v1(candidate) != candidate:
            raise VoiceAcceptanceIntegrityError(
                "acceptance candidate identity mismatch"
            )
        if (
            finalize_order_authority_v1(request.order_authority)
            != request.order_authority
        ):
            raise VoiceAcceptanceIntegrityError("order authority identity mismatch")
        if (
            candidate.order_authority_identity
            != request.order_authority.authority_identity
        ):
            raise VoiceAcceptanceIntegrityError("stale episode ordering")
        preview = candidate.preview
        if preview.terminal_result.kind is not DeterministicTerminalKindV2.GENERATED:
            raise VoiceAcceptanceIntegrityError(
                "only a generated preview can be accepted"
            )
        if preview.sidecar_identity != _seal(preview, "sidecar_identity"):
            raise VoiceAcceptanceIntegrityError("preview sidecar identity mismatch")
        if preview.source_semantic_draft_revision_identity != (
            semantic_draft_revision_identity(request.draft)
        ):
            raise VoiceAcceptanceIntegrityError("stale authored story revision")
        request_snapshot = candidate.execution_request.repetition_snapshot
        derived = derive_repetition_snapshot_v1(
            ledger=ledger,
            order_authority=request.order_authority,
            event_id=preview.event_id,
        )
        if derived.snapshot != request_snapshot:
            raise VoiceAcceptanceIntegrityError("stale repetition snapshot")
        result = preview.terminal_result
        if result.backend_kind is DeterministicBackendKindV2.DETERMINISTIC_RENDERER:
            rerun = DeterministicVoiceExecutorV2(
                activation_policy=candidate.execution_request.activation_policy
            ).execute(candidate.execution_request)
            if rerun != result:
                raise VoiceAcceptanceIntegrityError("preview no longer matches execution")
        else:
            expected_result_identity = canonical_identity(
                result.model_copy(update={"result_identity": "sha256:" + "0" * 64})
            )
            if (
                result.result_identity != expected_result_identity
                or result.realization_receipt_identity is None
                or result.realization_receipt is None
                or result.realization_receipt.receipt_identity
                != result.realization_receipt_identity
                or result.realization_receipt.commentary_sha256
                != result.rendered_sha256
                or result.realization_receipt.factual_summary_sha256
                != __import__("hashlib").sha256(
                    next(
                        story.factual_summary.text
                        for story in request.draft.stories
                        if story.event_id == preview.event_id
                    ).encode("utf-8")
                ).hexdigest()
                or result.rendered_sha256
                != __import__("hashlib").sha256(result.rendered_utf8).hexdigest()
                or len(result.provenance) != 1
                or result.provenance[0].source_identity
                != result.realization_receipt_identity
            ):
                raise VoiceAcceptanceIntegrityError(
                    "governed realization receipt mismatch"
                )

    def accept(
        self,
        request: VoiceAcceptanceRequestV1,
        *,
        fault_after: Literal["intent", "draft", "ledger"] | None = None,
    ) -> VoiceAcceptanceReceiptV1:
        transaction_identity = canonical_identity(
            {
                "idempotency_key": request.idempotency_key,
                "request": request.request_identity,
            }
        )
        transaction_dir = self.transactions / transaction_identity.removeprefix(
            "sha256:"
        )
        receipt_path = transaction_dir / "receipt.json"
        if receipt_path.exists():
            receipt = load_receipt(receipt_path)
            if receipt.request_identity != request.request_identity:
                raise VoiceAcceptanceIntegrityError("idempotency-key conflict")
            if self.current_receipt() == receipt:
                return receipt
        ledger = self.current_ledger()
        self._validate_request(request, ledger)
        transaction_dir.mkdir(parents=True, exist_ok=True)
        atomic_write(transaction_dir / "intent.json", canonical_bytes(request))
        if fault_after == "intent":
            raise SimulatedAcceptanceCrash("after intent")

        preview = request.candidate.preview
        result = preview.terminal_result
        assert isinstance(result, VoiceGeneratedResultV2)
        stories = list(request.draft.stories)
        matches = [
            index
            for index, item in enumerate(stories)
            if item.event_id == preview.event_id
        ]
        if len(matches) != 1:
            raise VoiceAcceptanceIntegrityError("accepted story is missing")
        index = matches[0]
        provenance_identity = canonical_identity(
            [item.model_dump(mode="json") for item in result.provenance]
        )
        commentary = AcidCommentaryV2(
            text=result.rendered_utf8.decode("utf-8"),
            factual_boundary_receipt=preview.sidecar_identity,
            execution_provenance=AcidCommentaryExecutionProvenanceV2(
                backend_kind=(
                    "deterministic_renderer"
                    if result.backend_kind
                    is DeterministicBackendKindV2.DETERMINISTIC_RENDERER
                    else "model"
                ),
                backend_identity=result.renderer_identity,
                canonical_ir_identity=result.canonical_ir_identity,
                character_provenance_identity=provenance_identity,
                acceptance_transaction_identity=transaction_identity,
                model_calls=result.model_calls,
                provider_calls=result.provider_calls,
                model_loads=result.model_loads,
            ),
        )
        stories[index] = stories[index].model_copy(
            update={"acid_commentary": commentary, "acid_commentary_status": "present"}
        )
        authored = PastilaEditorSemanticDraftV2.assemble(
            episode_id=request.draft.episode_id,
            mode=SemanticDraftModeV2.CORE_PLUS_VOICE,
            stories=tuple(stories),
            transitions=request.draft.transitions,
            intro=request.draft.intro,
            final_monologue=request.draft.final_monologue,
            provenance_references=request.draft.provenance_references
            + (preview.sidecar_identity,),
            generation_receipts=request.draft.generation_receipts,
        )
        authored_identity = semantic_draft_revision_identity(authored)
        draft_path = transaction_dir / "accepted-draft.json"
        atomic_write(draft_path, canonical_bytes(authored))
        if fault_after == "draft":
            raise SimulatedAcceptanceCrash("after authored revision")

        execution = request.candidate.execution_request
        selected = next(
            item
            for item in execution.program_eligibility.shortlist
            if item.candidate_id == execution.program_selection.selected_candidate_id
        )
        expression = None
        if execution.expression_eligibility and execution.expression_selection:
            expression = next(
                (
                    item
                    for item in execution.expression_eligibility.shortlist
                    if item.candidate_id
                    == execution.expression_selection.selected_candidate_id
                ),
                None,
            )
        callbacks = tuple(
            sorted(
                {span.callback_id for span in execution.ir.spans if span.callback_id}
            )
        )
        mappings = tuple(
            sorted(
                {
                    span.nonliteral_mapping_id
                    for span in execution.ir.spans
                    if span.nonliteral_mapping_id
                }
            )
        )
        position = request.order_authority.ordered_event_ids.index(preview.event_id) + 1
        commit_identity = canonical_identity(
            {"transaction": transaction_identity, "revision": authored_identity}
        )
        commit = CommittedVoiceUseV1(
            commit_identity=commit_identity,
            episode_id=request.order_authority.episode_id,
            episode_ordinal=request.order_authority.episode_ordinal,
            event_id=preview.event_id,
            story_position=position,
            order_authority_identity=request.order_authority.authority_identity,
            accepted_commentary_revision_identity=authored_identity,
            mechanic_identity=selected.mechanic_id.value,
            realization_program_identity=selected.program_id,
            cadence_signature=selected.cadence_signature,
            approved_voice_surface_identities=(
                selected.surface_ids
                if result.backend_kind
                is DeterministicBackendKindV2.DETERMINISTIC_RENDERER
                else ()
            ),
            expression_identity=None
            if expression is None
            else expression.expression_id,
            expression_surface_identity=None
            if expression is None
            else expression.surface_id,
            expression_family_identity=(
                None if expression is None else expression.expression_family_identity
            ),
            expression_pool_identity=None
            if expression is None
            else expression.pool_identity,
            callback_identities=callbacks,
            mapping_identities=mappings,
            committed_at=request.accepted_at,
        )
        events = list(ledger.events)
        if request.replaces_commit_identity:
            effective = {
                item.commit_identity: item for item in effective_uses_v1(ledger)
            }
            replaced = effective.get(request.replaces_commit_identity)
            if replaced is None or replaced.publication_state.value == "published":
                raise VoiceAcceptanceIntegrityError("replacement target is unavailable")
            revocation = RepetitionLedgerEventV1(
                sequence=len(events) + 1,
                event_kind=RepetitionLedgerEventKindV1.REVOKE,
                transaction_identity=transaction_identity,
                target_commit_identity=replaced.commit_identity,
                actor_identity=request.owner_identity,
                reason="accepted_unpublished_commentary_replacement",
                occurred_at=request.accepted_at,
            )
            events.append(revocation)
        events.append(
            RepetitionLedgerEventV1(
                sequence=len(events) + 1,
                event_kind=RepetitionLedgerEventKindV1.COMMIT,
                transaction_identity=transaction_identity,
                commit=commit,
                actor_identity=request.owner_identity,
                reason="explicit_owner_acceptance",
                occurred_at=request.accepted_at,
            )
        )
        next_ledger = finalize_ledger_v1(
            VoiceRepetitionLedgerV1(
                prior_ledger_identity=ledger.ledger_identity,
                events=tuple(events),
            )
        )
        ledger_path = transaction_dir / "ledger.json"
        atomic_write(ledger_path, canonical_bytes(next_ledger))
        if fault_after == "ledger":
            raise SimulatedAcceptanceCrash("after ledger append")

        receipt = _finalize_receipt(
            VoiceAcceptanceReceiptV1(
                transaction_identity=transaction_identity,
                request_identity=request.request_identity,
                preview_sidecar_identity=preview.sidecar_identity,
                source_semantic_draft_revision_identity=(
                    preview.source_semantic_draft_revision_identity
                ),
                authority_identity=preview.event_authority_identity,
                fact_atom_bundle_identity=preview.fact_atom_bundle_identity,
                relationship_binding_identities=preview.relationship_binding_identities,
                program_eligibility_identity=preview.program_eligibility_identity,
                program_selection_receipt_identity=(
                    preview.program_selection_receipt_identity
                ),
                expression_eligibility_identity=preview.expression_eligibility_identity,
                expression_selection_receipt_identity=(
                    preview.expression_selection_receipt_identity
                ),
                repetition_snapshot_identity=preview.repetition_snapshot_identity,
                order_authority_identity=request.order_authority.authority_identity,
                activation_policy_identity=preview.activation_policy_identity,
                executor_identity=result.renderer_identity,
                canonical_ir_identity=result.canonical_ir_identity,
                rendered_output_sha256=result.rendered_sha256,
                provenance_identity=provenance_identity,
                resulting_semantic_draft_revision_identity=authored_identity,
                committed_repetition_identity=next_ledger.ledger_identity,
                owner_identity=request.owner_identity,
                accepted_at=request.accepted_at,
            )
        )
        atomic_write(receipt_path, canonical_bytes(receipt))
        self._publish_state(
            transaction_identity=transaction_identity,
            ledger_path=ledger_path,
            receipt_path=receipt_path,
            draft_path=draft_path,
        )
        return receipt

    def recover(self, request: VoiceAcceptanceRequestV1) -> VoiceAcceptanceReceiptV1:
        """Idempotently replay a staged acceptance to its canonical commit point."""

        return self.accept(request)


__all__ = [
    "SimulatedAcceptanceCrash",
    "VoiceAcceptanceIntegrityError",
    "VoiceAtomicAcceptanceStoreV1",
    "finalize_acceptance_request_v1",
    "finalize_candidate_v1",
]
