"""Editor orchestration and owner-readable states for deterministic Voice V2."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from pastila_scout.expression_catalog_v2.eligibility import (
    finalize_expression_selection_receipt,
)
from pastila_scout.expression_catalog_v2.eligibility_models import (
    ExpressionEligibilityResultV1,
    ExpressionOwnerSelectionReceiptV1,
    ExpressionSelectionKindV1,
)
from pastila_scout.voice_eligibility_v2.engine import finalize_selection_receipt
from pastila_scout.voice_eligibility_v2.models import (
    SelectionKindV1,
    VoiceEligibilityResultV1,
    VoiceOwnerSelectionReceiptV1,
    VoiceRepetitionSnapshotV1,
)
from pastila_scout.voice_executor_v2 import VoiceExecutorPortV2
from pastila_scout.voice_executor_v2.models import (
    DeterministicTerminalKindV2,
    VoiceDeterministicExecutionRequestV2,
    VoiceDeterministicTerminalResultV2,
    VoiceProductionActivationPolicyV1,
)


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EditorDeterministicVoiceStateV2(StrEnum):
    NO_ELIGIBLE_PROGRAM = "no_eligible_program"
    PROGRAM_SELECTION_REQUIRED = "program_selection_required"
    NO_COMMENTARY_SELECTED = "no_commentary_selected"
    NO_ELIGIBLE_EXPRESSION = "no_eligible_expression"
    EXPRESSION_SELECTION_REQUIRED = "expression_selection_required"
    EXPRESSION_NONE_SELECTED = "expression_none_selected"
    PREVIEW_GENERATED = "preview_generated"
    SAFE_ABSTENTION = "safe_abstention"
    INTEGRITY_FAILURE = "integrity_failure"


class EditorVoiceChoiceV2(_Frozen):
    candidate_identity: str
    label: str
    selectable: bool = True
    reason: str | None = None


class EditorVoiceInteractionV2(_Frozen):
    state: EditorDeterministicVoiceStateV2
    title: str
    message: str
    choices: tuple[EditorVoiceChoiceV2, ...] = ()
    acceptance_enabled: bool = False
    diagnostic_code: str | None = None


class EditorDeterministicVoiceApplicationServiceV2:
    """Owns workflow orchestration; it never authors or repairs commentary."""

    def __init__(
        self,
        *,
        executor: VoiceExecutorPortV2,
        activation_policy: VoiceProductionActivationPolicyV1,
    ):
        capability = executor.inspect_capability()
        if capability.activation_policy_identity != activation_policy.policy_identity:
            raise ValueError("executor activation policy mismatch")
        self.executor = executor
        self.activation_policy = activation_policy

    def present_programs(
        self, result: VoiceEligibilityResultV1
    ) -> EditorVoiceInteractionV2:
        if not result.shortlist:
            return EditorVoiceInteractionV2(
                state=EditorDeterministicVoiceStateV2.NO_ELIGIBLE_PROGRAM,
                title="Comentariu acid: fără construcție eligibilă",
                message="Nu există momentan o construcție editorială sigură.",
            )
        return EditorVoiceInteractionV2(
            state=EditorDeterministicVoiceStateV2.PROGRAM_SELECTION_REQUIRED,
            title="Alege stilul comentariului",
            message="Selectează o construcție sau Fără comentariu.",
            choices=tuple(
                EditorVoiceChoiceV2(
                    candidate_identity=item.candidate_id,
                    label=_PROGRAM_LABELS.get(
                        item.program_id, "Construcție editorială"
                    ),
                )
                for item in result.shortlist
            )
            + (
                EditorVoiceChoiceV2(candidate_identity="NONE", label="Fără comentariu"),
            ),
        )

    @staticmethod
    def present_owner_none_commentary() -> EditorVoiceInteractionV2:
        return EditorVoiceInteractionV2(
            state=EditorDeterministicVoiceStateV2.NO_COMMENTARY_SELECTED,
            title="Comentariu acid: omis",
            message="Ai ales Fără comentariu. Nu se consumă istoricul de repetiție.",
        )

    @staticmethod
    def present_owner_none_expression() -> EditorVoiceInteractionV2:
        return EditorVoiceInteractionV2(
            state=EditorDeterministicVoiceStateV2.EXPRESSION_NONE_SELECTED,
            title="Expresie opțională: omisă",
            message="Comentariul poate fi previzualizat fără expresie.",
        )

    @staticmethod
    def present_integrity_failure(
        *, diagnostic_code: str, refresh_required: bool = True
    ) -> EditorVoiceInteractionV2:
        message = "Verificarea de integritate a eșuat."
        if refresh_required:
            message += " Apasă Re-evaluează și creează o previzualizare nouă."
        return EditorVoiceInteractionV2(
            state=EditorDeterministicVoiceStateV2.INTEGRITY_FAILURE,
            title="Comentariul este blocat",
            message=message,
            diagnostic_code=diagnostic_code,
        )

    @staticmethod
    def select_program(
        *,
        result: VoiceEligibilityResultV1,
        snapshot: VoiceRepetitionSnapshotV1,
        candidate_identity: str | None,
        owner_identity: str,
        selected_at: datetime,
    ) -> VoiceOwnerSelectionReceiptV1:
        receipt = VoiceOwnerSelectionReceiptV1(
            fact_atom_bundle_identity=result.fact_atom_bundle_identity,
            eligibility_result_identity=result.result_identity,
            repetition_snapshot_identity=snapshot.snapshot_identity,
            shortlist_candidate_ids=tuple(
                item.candidate_id for item in result.shortlist
            ),
            selection_kind=(
                SelectionKindV1.NONE
                if candidate_identity is None
                else SelectionKindV1.PROGRAM
            ),
            selected_candidate_id=candidate_identity,
            selector_identity=owner_identity,
            selected_at=selected_at,
            receipt_identity="sha256:" + "0" * 64,
        )
        return finalize_selection_receipt(receipt, result=result, snapshot=snapshot)

    def present_expressions(
        self, result: ExpressionEligibilityResultV1
    ) -> EditorVoiceInteractionV2:
        enabled = {
            (item.expression_identity, item.surface_identity)
            for item in self.activation_policy.entries
        }
        choices = tuple(
            EditorVoiceChoiceV2(
                candidate_identity=item.candidate_id,
                label=item.exact_surface,
            )
            for item in result.shortlist
            if (item.expression_id, item.surface_id) in enabled
        )
        if not choices:
            return EditorVoiceInteractionV2(
                state=EditorDeterministicVoiceStateV2.NO_ELIGIBLE_EXPRESSION,
                title="Expresie opțională: niciuna eligibilă",
                message="Comentariul poate continua fără expresie.",
                choices=(
                    EditorVoiceChoiceV2(
                        candidate_identity="NONE", label="Fără expresie"
                    ),
                ),
            )
        return EditorVoiceInteractionV2(
            state=EditorDeterministicVoiceStateV2.EXPRESSION_SELECTION_REQUIRED,
            title="Alege o expresie opțională",
            message="Sunt afișate numai expresiile eligibile și active.",
            choices=choices
            + (EditorVoiceChoiceV2(candidate_identity="NONE", label="Fără expresie"),),
        )

    @staticmethod
    def select_expression(
        *,
        result: ExpressionEligibilityResultV1,
        snapshot: VoiceRepetitionSnapshotV1,
        candidate_identity: str | None,
        owner_identity: str,
        selected_at: datetime,
    ) -> ExpressionOwnerSelectionReceiptV1:
        receipt = ExpressionOwnerSelectionReceiptV1(
            fact_atom_bundle_identity=result.fact_atom_bundle_identity,
            expression_eligibility_result_identity=result.result_identity,
            repetition_snapshot_identity=snapshot.snapshot_identity,
            shortlist_candidate_ids=tuple(
                item.candidate_id for item in result.shortlist
            ),
            selection_kind=(
                ExpressionSelectionKindV1.NONE
                if candidate_identity is None
                else ExpressionSelectionKindV1.EXPRESSION
            ),
            selected_candidate_id=candidate_identity,
            selector_identity=owner_identity,
            selected_at=selected_at,
        )
        return finalize_expression_selection_receipt(
            receipt, result=result, snapshot=snapshot
        )

    def preview(
        self, request: VoiceDeterministicExecutionRequestV2
    ) -> tuple[VoiceDeterministicTerminalResultV2, EditorVoiceInteractionV2]:
        result = self.executor.execute(request)
        if result.kind is DeterministicTerminalKindV2.GENERATED:
            state = EditorVoiceInteractionV2(
                state=EditorDeterministicVoiceStateV2.PREVIEW_GENERATED,
                title="Previzualizare comentariu acid",
                message=result.rendered_utf8.decode("utf-8"),
                acceptance_enabled=True,
            )
        elif result.kind is DeterministicTerminalKindV2.SAFELY_ABSTAINED:
            state = EditorVoiceInteractionV2(
                state=EditorDeterministicVoiceStateV2.SAFE_ABSTENTION,
                title="Comentariu omis în siguranță",
                message="Construcția selectată nu poate fi realizată în condiții sigure.",
                diagnostic_code=result.reason_code,
            )
        else:
            state = EditorVoiceInteractionV2(
                state=EditorDeterministicVoiceStateV2.INTEGRITY_FAILURE,
                title="Comentariul trebuie reevaluat",
                message="Datele s-au schimbat sau verificarea de integritate a eșuat.",
                diagnostic_code=result.failure_code,
            )
        return result, state


_PROGRAM_LABELS = {
    "FII_BOUNDED_INTAKE_DIALOGUE_V1": "Dialog de recepție",
    "FII_BOUNDED_SERVICE_WORKFLOW_V1": "Flux de serviciu",
    "FII_CLOSED_OPTION_MENU_V1": "Meniu cu opțiuni",
    "FII_FICTIONAL_SERVICE_ADVERTISEMENT_V1": "Reclamă fictivă",
    "NEL_ACCUMULATION_SCALE_VISUALIZATION_V1": "Scara acumulării",
    "NEL_CATEGORY_THRESHOLD_RECLASSIFICATION_V1": "Schimbare de categorie",
    "NEL_DELAYED_QUANTITY_REVEAL_V1": "Dezvăluire numerică",
    "NEL_TWO_AXIS_QUANTITY_CONTRAST_V1": "Contrast între două mărimi",
    "USF_ABSURD_ALTERNATIVES_WITHOUT_SELECTION_V1": "Alternative absurd-fictive",
    "USF_DISTINCT_DOMAIN_ANALOGY_DETOUR_V1": "Analogie din alt domeniu",
    "USF_ISOLATED_SCENE_AND_EXACT_RETURN_V1": "Secvență fictivă delimitată",
    "USF_KNOWN_UNKNOWN_LEDGER_V1": "Ce știm / ce nu știm",
}


__all__ = [
    "EditorDeterministicVoiceApplicationServiceV2",
    "EditorDeterministicVoiceStateV2",
    "EditorVoiceChoiceV2",
    "EditorVoiceInteractionV2",
]
