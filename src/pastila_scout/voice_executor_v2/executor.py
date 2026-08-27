"""Fail-closed model-free deterministic executor adapter."""

from __future__ import annotations

from dataclasses import asdict
from typing import Protocol

from pastila_scout.expression_catalog_v2.eligibility import (
    BOUNDED_POOL_SCOPE_SPECS_V1,
)
from pastila_scout.expression_catalog_v2.eligibility import (
    _sealed as expression_sealed,
)
from pastila_scout.expression_catalog_v2.eligibility_models import (
    ExpressionSelectionKindV1,
)
from pastila_scout.expression_catalog_v2.persistence import (
    load_expression_catalog_overlay_v2,
)
from pastila_scout.voice_deterministic_v2.core import DeterministicVoiceValidationError
from pastila_scout.voice_deterministic_v2.models import (
    AcidCommentaryIRV1_1,
    ProductionAcidCommentaryIRV1_1,
)
from pastila_scout.voice_eligibility_v2.engine import _sealed as voice_sealed
from pastila_scout.voice_eligibility_v2.models import SelectionKindV1
from pastila_scout.voice_fact_atoms_v2.persistence import (
    bundle_payload_identity,
    canonical_identity,
)

from .models import (
    ZERO_IDENTITY,
    VoiceDeterministicCapabilityV2,
    VoiceDeterministicExecutionRequestV2,
    VoiceDeterministicTerminalResultV2,
    VoiceGeneratedResultV2,
    VoiceIntegrityFailureResultV2,
    VoiceProductionActivationPolicyV1,
    VoiceProofOnlyActivationAuthorityV1,
    VoiceSafelyAbstainedResultV2,
)

RENDERER_IDENTITY = "pastilaacida-voice:deterministic-renderer:v2"


def _seal(value, field: str) -> str:
    return canonical_identity(value.model_copy(update={field: ZERO_IDENTITY}))


def finalize_activation_policy_v1(
    policy: VoiceProductionActivationPolicyV1,
) -> VoiceProductionActivationPolicyV1:
    return policy.model_copy(
        update={"policy_identity": _seal(policy, "policy_identity")}
    )


ZERO_ACTIVATION_POLICY_V1 = finalize_activation_policy_v1(
    VoiceProductionActivationPolicyV1()
)


def finalize_request_v2(
    request: VoiceDeterministicExecutionRequestV2,
) -> VoiceDeterministicExecutionRequestV2:
    return request.model_copy(
        update={"request_identity": _seal(request, "request_identity")}
    )


def build_governed_execution_request_v2(
    *,
    story_binding,
    fact_atom_bundle,
    relationship_bindings=(),
    program_eligibility,
    mechanic_claim,
    program_selection,
    expression_eligibility=None,
    expression_selection=None,
    repetition_snapshot,
    activation_policy,
    ir,
) -> VoiceDeterministicExecutionRequestV2:
    """Construct a canonical request solely from governed production state."""

    if not isinstance(ir, ProductionAcidCommentaryIRV1_1):
        raise TypeError("governed production request requires production IR")
    expected_relationships = tuple(
        item.binding_identity for item in relationship_bindings
    )
    expression_receipt_identity = (
        expression_selection.receipt_identity if expression_selection else None
    )
    expected = {
        "semantic_draft_revision_identity": story_binding.semantic_draft_revision_identity,
        "event_id": story_binding.event_id,
        "fact_atom_bundle_identity": fact_atom_bundle.bundle_identity,
        "program_eligibility_identity": program_eligibility.result_identity,
        "mechanic_eligibility_claim_identity": mechanic_claim.claim_identity,
        "program_selection_receipt_identity": program_selection.receipt_identity,
        "repetition_snapshot_identity": repetition_snapshot.snapshot_identity,
        "activation_policy_identity": activation_policy.policy_identity,
        "renderer_identity": RENDERER_IDENTITY,
        "relationship_binding_identities": expected_relationships,
        "expression_selection_receipt_identity": expression_receipt_identity,
    }
    for field, value in expected.items():
        if getattr(ir, field) != value:
            raise ValueError(f"production IR {field} mismatch")
    return finalize_request_v2(
        VoiceDeterministicExecutionRequestV2(
            story_binding=story_binding,
            fact_atom_bundle=fact_atom_bundle,
            relationship_bindings=relationship_bindings,
            program_eligibility=program_eligibility,
            mechanic_claim=mechanic_claim,
            program_selection=program_selection,
            expression_eligibility=expression_eligibility,
            expression_selection=expression_selection,
            repetition_snapshot=repetition_snapshot,
            activation_policy=activation_policy,
            expected_renderer_identity=RENDERER_IDENTITY,
            ir=ir,
        )
    )


def _finalize_result(result):
    return result.model_copy(
        update={"result_identity": _seal(result, "result_identity")}
    )


class VoiceExecutorPortV2(Protocol):
    def inspect_capability(self) -> VoiceDeterministicCapabilityV2: ...

    def execute(
        self, request: VoiceDeterministicExecutionRequestV2
    ) -> VoiceDeterministicTerminalResultV2: ...


class _IntegrityError(ValueError):
    def __init__(self, code: str, identity: str):
        self.code = code
        self.identity = identity
        super().__init__(code)


class DeterministicVoiceExecutorV2:
    def __init__(
        self,
        *,
        activation_policy: VoiceProductionActivationPolicyV1,
        _proof_activation_authority: VoiceProofOnlyActivationAuthorityV1 | None = None,
    ):
        if activation_policy.policy_identity != _seal(
            activation_policy, "policy_identity"
        ):
            raise ValueError("activation policy identity mismatch")
        self._policy = activation_policy
        self._proof_authority = _proof_activation_authority
        overlay = load_expression_catalog_overlay_v2()
        self._known_surfaces = {
            (item.expression_id, item.surface_id): item
            for item in overlay.approved_surfaces
        }
        records = {item.expression_id: item for item in overlay.records}
        specs = {item.expression_id: item for item in BOUNDED_POOL_SCOPE_SPECS_V1}
        if any(
            (item.expression_identity, item.surface_identity)
            not in self._known_surfaces
            for item in activation_policy.entries
        ):
            raise ValueError(
                "activation policy references an unknown expression surface"
            )
        for item in activation_policy.entries:
            record = records.get(item.expression_identity)
            spec = specs.get(item.expression_identity)
            if record is None or record.adjudicated_scope is None or spec is None:
                raise ValueError("activation policy references an ungoverned expression")
            if (
                canonical_identity(asdict(spec)) != item.eligibility_spec_identity
                or record.adjudicated_scope.scope_identity
                != item.relationship_scope_identity
            ):
                raise ValueError("activation policy governance identity mismatch")
        self._active_surfaces = {
            (item.expression_identity, item.surface_identity)
            for item in activation_policy.entries
        }

    def inspect_capability(self) -> VoiceDeterministicCapabilityV2:
        return VoiceDeterministicCapabilityV2(
            renderer_identity=RENDERER_IDENTITY,
            activation_policy_identity=self._policy.policy_identity,
            proof_activation_authority_identity=(
                self._proof_authority.authority_identity
                if self._proof_authority is not None
                else None
            ),
        )

    def _validate(self, request: VoiceDeterministicExecutionRequestV2) -> None:
        if request.request_identity != _seal(request, "request_identity"):
            raise _IntegrityError("request_identity_mismatch", request.request_identity)
        if request.expected_renderer_identity != RENDERER_IDENTITY:
            raise _IntegrityError(
                "unknown_renderer_identity", request.expected_renderer_identity
            )
        if request.activation_policy != self._policy:
            raise _IntegrityError(
                "unknown_activation_policy_identity",
                request.activation_policy.policy_identity,
            )
        if isinstance(request.ir, ProductionAcidCommentaryIRV1_1):
            if request.proof_activation_authority is not None:
                raise _IntegrityError(
                    "proof_authority_on_production_request",
                    request.proof_activation_authority.authority_identity,
                )
        elif isinstance(request.ir, AcidCommentaryIRV1_1):
            authority = request.proof_activation_authority
            if self._proof_authority is None:
                from .proof_activation import (
                    FROZEN_PROOF_ONLY_ACTIVATION_AUTHORITY_V1,
                )

                expected_proof_authority = FROZEN_PROOF_ONLY_ACTIVATION_AUTHORITY_V1
            else:
                expected_proof_authority = self._proof_authority
            if authority != expected_proof_authority:
                raise _IntegrityError(
                    "proof_activation_not_authorized",
                    authority.authority_identity if authority else ZERO_IDENTITY,
                )
            entry = next(
                (
                    item
                    for item in authority.entries
                    if item.proof_id == request.ir.proof_id
                ),
                None,
            )
            if entry is None or (
                entry.source_record_id != request.ir.source_record_id
                or entry.realization_program_id != request.ir.realization_program_id
                or entry.realization_program_sha256
                != request.ir.realization_program_sha256
                or entry.expected_output_sha256 != request.ir.expected_output_sha256
                or entry.expected_abstention_reason
                != (
                    request.ir.abstention_reason.value
                    if request.ir.abstention_reason
                    else None
                )
            ):
                raise _IntegrityError(
                    "proof_identity_not_authorized", request.ir.proof_id
                )
        bundle = request.fact_atom_bundle
        if bundle.bundle_identity != bundle_payload_identity(bundle):
            raise _IntegrityError("stale_fact_atom_bundle", bundle.bundle_identity)
        binding = request.story_binding
        if (
            bundle.semantic_draft_revision_identity
            != binding.semantic_draft_revision_identity
            or bundle.event_id != binding.event_id
            or bundle.factual_summary_identity != binding.factual_summary_sha256
            or bundle.event_authority_identity != binding.event_authority_identity
            or bundle.background_authority_identity
            != binding.commentary_background_authority_identity
        ):
            raise _IntegrityError(
                "stale_story_authority", binding.semantic_draft_revision_identity
            )
        snapshot = request.repetition_snapshot
        if snapshot.snapshot_identity != voice_sealed(snapshot, "snapshot_identity"):
            raise _IntegrityError(
                "stale_repetition_snapshot", snapshot.snapshot_identity
            )
        eligibility = request.program_eligibility
        if eligibility.result_identity != voice_sealed(eligibility, "result_identity"):
            raise _IntegrityError(
                "stale_program_eligibility", eligibility.result_identity
            )
        if (
            eligibility.fact_atom_bundle_identity != bundle.bundle_identity
            or eligibility.repetition_snapshot_identity != snapshot.snapshot_identity
        ):
            raise _IntegrityError(
                "stale_program_eligibility", eligibility.result_identity
            )
        selection = request.program_selection
        if selection.receipt_identity != voice_sealed(selection, "receipt_identity"):
            raise _IntegrityError(
                "stale_program_selection_receipt", selection.receipt_identity
            )
        if isinstance(request.ir, ProductionAcidCommentaryIRV1_1):
            claim = request.mechanic_claim
            if claim is None or claim.claim_identity != voice_sealed(
                claim, "claim_identity"
            ):
                raise _IntegrityError(
                    "missing_or_stale_mechanic_claim",
                    request.ir.mechanic_eligibility_claim_identity,
                )
            if (
                claim.claim_identity != request.ir.mechanic_eligibility_claim_identity
                or claim.fact_atom_bundle_identity != bundle.bundle_identity
                or claim.mechanic_id is not request.ir.mechanic_id
                or tuple((item.role, item.atom_ids) for item in claim.atom_roles)
                != request.ir.atom_role_bindings
            ):
                raise _IntegrityError("stale_mechanic_claim", claim.claim_identity)
            ir_expected = {
                "semantic_draft_revision_identity": binding.semantic_draft_revision_identity,
                "event_id": binding.event_id,
                "fact_atom_bundle_identity": bundle.bundle_identity,
                "program_eligibility_identity": eligibility.result_identity,
                "program_selection_receipt_identity": selection.receipt_identity,
                "repetition_snapshot_identity": snapshot.snapshot_identity,
                "activation_policy_identity": self._policy.policy_identity,
                "renderer_identity": RENDERER_IDENTITY,
                "relationship_binding_identities": tuple(
                    item.binding_identity for item in request.relationship_bindings
                ),
                "expression_selection_receipt_identity": (
                    request.expression_selection.receipt_identity
                    if request.expression_selection is not None
                    else None
                ),
                "selected_program_candidate_identity": selection.selected_candidate_id,
            }
            if any(
                getattr(request.ir, field) != value
                for field, value in ir_expected.items()
            ):
                raise _IntegrityError(
                    "stale_production_ir", canonical_identity(request.ir)
                )
            atom_text = {atom.atom_id: atom.proposition for atom in bundle.atoms}
            if any(
                span.provenance_class.value == "AUTHORIZED_EVENT_FACT_ATOM"
                and atom_text.get(span.source_identity) != span.text
                for span in request.ir.spans
            ):
                raise _IntegrityError(
                    "mutated_factual_ir_span", canonical_identity(request.ir)
                )
        if (
            selection.fact_atom_bundle_identity != bundle.bundle_identity
            or selection.eligibility_result_identity != eligibility.result_identity
            or selection.repetition_snapshot_identity != snapshot.snapshot_identity
            or selection.shortlist_candidate_ids
            != tuple(item.candidate_id for item in eligibility.shortlist)
        ):
            raise _IntegrityError(
                "stale_program_selection_receipt", selection.receipt_identity
            )
        atom_ids = {atom.atom_id for atom in bundle.atoms}
        for relation in request.relationship_bindings:
            if relation.binding_identity != expression_sealed(
                relation, "binding_identity"
            ):
                raise _IntegrityError(
                    "stale_relationship_binding", relation.binding_identity
                )
            if relation.fact_atom_bundle_identity != bundle.bundle_identity or any(
                atom_id not in atom_ids
                for role in relation.atom_roles
                for atom_id in role.atom_ids
            ):
                raise _IntegrityError(
                    "stale_relationship_binding", relation.binding_identity
                )
        if request.expression_eligibility is not None:
            expression_result = request.expression_eligibility
            expression_selection = request.expression_selection
            assert expression_selection is not None
            if expression_result.result_identity != expression_sealed(
                expression_result, "result_identity"
            ):
                raise _IntegrityError(
                    "stale_expression_eligibility", expression_result.result_identity
                )
            if (
                expression_result.fact_atom_bundle_identity != bundle.bundle_identity
                or expression_result.program_eligibility_result_identity
                != eligibility.result_identity
                or expression_result.repetition_snapshot_identity
                != snapshot.snapshot_identity
            ):
                raise _IntegrityError(
                    "stale_expression_eligibility", expression_result.result_identity
                )
            if expression_selection.receipt_identity != expression_sealed(
                expression_selection, "receipt_identity"
            ):
                raise _IntegrityError(
                    "stale_expression_selection_receipt",
                    expression_selection.receipt_identity,
                )
            if (
                expression_selection.expression_eligibility_result_identity
                != expression_result.result_identity
                or expression_selection.fact_atom_bundle_identity
                != bundle.bundle_identity
                or expression_selection.repetition_snapshot_identity
                != snapshot.snapshot_identity
                or expression_selection.shortlist_candidate_ids
                != tuple(item.candidate_id for item in expression_result.shortlist)
            ):
                raise _IntegrityError(
                    "stale_expression_selection_receipt",
                    expression_selection.receipt_identity,
                )
            if (
                expression_selection.selection_kind
                is ExpressionSelectionKindV1.EXPRESSION
            ):
                candidate = next(
                    (
                        item
                        for item in expression_result.shortlist
                        if item.candidate_id
                        == expression_selection.selected_candidate_id
                    ),
                    None,
                )
                if candidate is None:
                    raise _IntegrityError(
                        "unknown_expression_identity",
                        expression_selection.receipt_identity,
                    )
                known_surface = self._known_surfaces.get(
                    (candidate.expression_id, candidate.surface_id)
                )
                if known_surface is None:
                    raise _IntegrityError(
                        "unknown_expression_or_surface_identity", candidate.candidate_id
                    )
                if (
                    candidate.expression_id,
                    candidate.surface_id,
                ) not in self._active_surfaces:
                    raise _IntegrityError(
                        "expression_surface_not_production_active",
                        candidate.candidate_id,
                    )
                if (
                    known_surface.exact_surface != candidate.exact_surface
                    or known_surface.surface_utf8_sha256
                    != candidate.surface_utf8_sha256
                ):
                    raise _IntegrityError(
                        "expression_surface_hash_mismatch", candidate.candidate_id
                    )
                if (
                    candidate.selected_program_candidate_id
                    != selection.selected_candidate_id
                ):
                    raise _IntegrityError(
                        "mismatched_expression_program_context", candidate.candidate_id
                    )

    def execute(self, request: VoiceDeterministicExecutionRequestV2):
        try:
            self._validate(request)
        except _IntegrityError as exc:
            return _finalize_result(
                VoiceIntegrityFailureResultV2(
                    renderer_identity=RENDERER_IDENTITY,
                    request_identity=request.request_identity,
                    failure_code=exc.code,
                    failed_identity=exc.identity,
                )
            )

        if request.program_selection.selection_kind is SelectionKindV1.NONE:
            return _finalize_result(
                VoiceSafelyAbstainedResultV2(
                    renderer_identity=RENDERER_IDENTITY,
                    request_identity=request.request_identity,
                    reason_code="owner_selected_no_commentary",
                    governed_identity=request.program_selection.receipt_identity,
                )
            )
        if request.expression_selection is not None and (
            request.expression_selection.selection_kind
            is ExpressionSelectionKindV1.EXPRESSION
        ):
            return _finalize_result(
                VoiceSafelyAbstainedResultV2(
                    renderer_identity=RENDERER_IDENTITY,
                    request_identity=request.request_identity,
                    reason_code="expression_not_production_enabled",
                    governed_identity=request.activation_policy.policy_identity,
                )
            )
        selected = next(
            item
            for item in request.program_eligibility.shortlist
            if item.candidate_id == request.program_selection.selected_candidate_id
        )
        if request.ir is None:
            return _finalize_result(
                VoiceSafelyAbstainedResultV2(
                    renderer_identity=RENDERER_IDENTITY,
                    request_identity=request.request_identity,
                    reason_code="no_governed_ir",
                    governed_identity=request.program_selection.receipt_identity,
                )
            )
        if request.ir.realization_program_id != selected.program_id:
            return _finalize_result(
                VoiceIntegrityFailureResultV2(
                    renderer_identity=RENDERER_IDENTITY,
                    request_identity=request.request_identity,
                    failure_code="mismatched_selected_program",
                    failed_identity=selected.candidate_id,
                )
            )
        try:
            if isinstance(request.ir, ProductionAcidCommentaryIRV1_1):
                # Production rendering is an explicitly separate authority
                # lineage.  Keep the non-production executor importable
                # without loading that binding.
                from pastila_scout.voice_deterministic_v2.production_renderer import (
                    render_production_deterministic_voice_v2,
                )

                rendered = render_production_deterministic_voice_v2(request.ir)
            else:
                # Historical P1-P8 compatibility is lazy and never enters the
                # installed reusable-program production path.
                from pastila_scout.voice_deterministic_v2.renderer import (
                    render_deterministic_voice_v2,
                )

                rendered = render_deterministic_voice_v2(request.ir)
        except DeterministicVoiceValidationError:
            return _finalize_result(
                VoiceIntegrityFailureResultV2(
                    renderer_identity=RENDERER_IDENTITY,
                    request_identity=request.request_identity,
                    failure_code="deterministic_ir_validation_failed",
                    failed_identity=canonical_identity(request.ir),
                )
            )
        if rendered.output_sha256 is None:
            return _finalize_result(
                VoiceSafelyAbstainedResultV2(
                    renderer_identity=RENDERER_IDENTITY,
                    request_identity=request.request_identity,
                    reason_code=f"deterministic_{rendered.abstention_reason.value.lower()}",
                    governed_identity=rendered.ir_identity,
                )
            )
        return _finalize_result(
            VoiceGeneratedResultV2(
                renderer_identity=RENDERER_IDENTITY,
                request_identity=request.request_identity,
                canonical_ir_identity=rendered.ir_identity,
                rendered_utf8=rendered.commentary_bytes,
                rendered_sha256=rendered.output_sha256,
                provenance=rendered.provenance,
                validation_identity=canonical_identity(
                    {"ir": rendered.ir_identity, "output": rendered.output_sha256}
                ),
            )
        )


class ProofOnlyDeterministicVoiceExecutorV2(DeterministicVoiceExecutorV2):
    """Executor available only to an explicitly governed frozen-proof harness."""

    def __init__(
        self,
        *,
        proof_activation_authority: VoiceProofOnlyActivationAuthorityV1,
    ):
        from .proof_activation import finalize_proof_activation_authority_v1

        if proof_activation_authority.authority_identity != (
            finalize_proof_activation_authority_v1(
                proof_activation_authority
            ).authority_identity
        ):
            raise ValueError("proof activation authority identity mismatch")
        super().__init__(
            activation_policy=ZERO_ACTIVATION_POLICY_V1,
            _proof_activation_authority=proof_activation_authority,
        )


__all__ = [
    "RENDERER_IDENTITY",
    "ZERO_ACTIVATION_POLICY_V1",
    "DeterministicVoiceExecutorV2",
    "ProofOnlyDeterministicVoiceExecutorV2",
    "VoiceExecutorPortV2",
    "build_governed_execution_request_v2",
    "finalize_activation_policy_v1",
    "finalize_request_v2",
]
