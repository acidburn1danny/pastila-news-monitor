"""Stateful installed-Tk adapter over the governed Voice V2 services."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from pastila_scout.editor_voice_deterministic_v2 import (
    EditorDeterministicVoiceApplicationServiceV2,
    EditorDeterministicVoiceStateV2,
    EditorVoiceInteractionV2,
)
from pastila_scout.expression_catalog_v2.eligibility_models import (
    ExpressionEligibilityResultV1,
    ExpressionOwnerSelectionReceiptV1,
)
from pastila_scout.voice_deterministic_v2.models import (
    ProvenanceClassV1,
    RenderedProvenanceSpanV1,
)
from pastila_scout.voice_eligibility_v2.models import (
    VoiceEligibilityResultV1,
    VoiceOwnerSelectionReceiptV1,
    VoiceRepetitionSnapshotV1,
)
from pastila_scout.voice_executor_v2.models import (
    DeterministicBackendKindV2,
    DeterministicTerminalKindV2,
    VoiceDeterministicExecutionRequestV2,
    VoiceDeterministicTerminalResultV2,
    VoiceGeneratedResultV2,
    VoiceSafelyAbstainedResultV2,
)
from pastila_scout.voice_fact_atoms_v2.persistence import canonical_identity
from pastila_scout.voice_governed_realization_v1 import (
    PROGRAM_ID as GOVERNED_REALIZATION_PROGRAM_ID,
)
from pastila_scout.voice_governed_context_v2 import VoiceGovernedContextV2
from pastila_scout.voice_governed_realization_v1 import (
    REALIZER_IDENTITY,
)
from pastila_scout.voice_repetition_v2 import VoiceAtomicAcceptanceStoreV1
from pastila_scout.voice_repetition_v2.models import VoiceAcceptanceRequestV1

from .voice_adjudication_actions import VoiceDesktopAdjudicationActionV1
from .voice_adjudication_presentation import present_voice_adjudication_v1
from .voice_v2_interaction import VoiceDesktopActionInputV2, VoiceDesktopPresentationV2


VoiceDesktopGovernedContextV2 = VoiceGovernedContextV2


class VoiceDesktopContextRegistryV2:
    """Process-local bridge populated only by governed persisted-story loaders."""

    def __init__(self, persisted_loader=None, bootstrap=None) -> None:
        self._contexts: dict[int, VoiceDesktopGovernedContextV2] = {}
        self._persisted_loader = persisted_loader
        self._bootstrap = bootstrap
        self._bootstrap_results = {}

    def publish(self, context: VoiceDesktopGovernedContextV2) -> None:
        self._contexts[context.event_id] = context

    def discard(self, event_id: int) -> None:
        self._contexts.pop(event_id, None)

    def load(self, event_id: int) -> VoiceDesktopGovernedContextV2 | None:
        if self._bootstrap is not None:
            result = self._bootstrap.reevaluate(event_id)
            self._bootstrap_results[event_id] = result
            self._contexts.pop(event_id, None)
            if result.status.value not in {
                "eligibility_available",
                "safe_no_program",
            }:
                return None
        context = self._contexts.get(event_id)
        if context is None and self._persisted_loader is not None:
            context = self._persisted_loader.load(event_id)
        return context

    def bootstrap_result(self, event_id: int):
        return self._bootstrap_results.get(event_id)

    def register_persisted_story(self, loader, event_id: int) -> bool:
        """Publish only a context reconstructed through a governed story pointer."""

        context = loader.load(event_id)
        if context is None:
            self.discard(event_id)
            return False
        self.publish(context)
        return True


class VoiceDesktopWorkflowCoordinatorV2:
    """Keeps only transient UI state; all governed state comes from callbacks."""

    def __init__(
        self,
        *,
        application: EditorDeterministicVoiceApplicationServiceV2,
        load_context: Callable[[int], VoiceDesktopGovernedContextV2 | None],
        owner_identity: str,
        load_bootstrap_result=None,
        adjudication_coordinator=None,
        daily_use_automation: bool = False,
        governed_realizer=None,
        governed_realizer_required: bool = False,
    ):
        self.application = application
        self.load_context = load_context
        self.owner_identity = owner_identity
        self.load_bootstrap_result = load_bootstrap_result
        self.adjudication_coordinator = adjudication_coordinator
        self.daily_use_automation = daily_use_automation
        self.governed_realizer = governed_realizer
        self.governed_realizer_required = governed_realizer_required
        self.context: VoiceDesktopGovernedContextV2 | None = None
        self.program_receipt: VoiceOwnerSelectionReceiptV1 | None = None
        self.expression_result: ExpressionEligibilityResultV1 | None = None
        self.expression_receipt: ExpressionOwnerSelectionReceiptV1 | None = None
        self.preview_result: VoiceDeterministicTerminalResultV2 | None = None

    def dispatch(self, value) -> VoiceDesktopPresentationV2:
        if type(value) is VoiceDesktopAdjudicationActionV1:
            if self.adjudication_coordinator is None:
                return self._integrity(value.event_id, "adjudication_unavailable")
            try:
                self.adjudication_coordinator.dispatch(value)
            except ValueError:
                return self._integrity(value.event_id, "adjudication_action_rejected")
            return self._refresh(value.event_id)
        if type(value) is not VoiceDesktopActionInputV2:
            raise TypeError("invalid Voice Desktop action")
        if value.action in {"load", "refresh"}:
            return self._refresh(
                value.event_id, automate=value.action == "refresh"
            )
        if self.context is None or self.context.event_id != value.event_id:
            return self._integrity(value.event_id, "stale_story_authority")
        if value.action == "select_program":
            return self._select_program(value.candidate_identity)
        if value.action == "select_expression":
            return self._select_expression(value.candidate_identity)
        if value.action == "preview":
            return self._preview()
        if value.action == "reject":
            self.preview_result = None
            return self._current(
                "Previzualizarea a fost respinsă. Istoricul nu s-a schimbat."
            )
        if value.action == "accept":
            return self._accept()
        raise ValueError("unknown Voice Desktop action")

    def _refresh(
        self, event_id: int, *, automate: bool = True
    ) -> VoiceDesktopPresentationV2:
        self.context = self.load_context(event_id)
        self.program_receipt = None
        self.expression_result = None
        self.expression_receipt = None
        self.preview_result = None
        if self.context is None:
            bootstrap = (
                None
                if self.load_bootstrap_result is None
                else self.load_bootstrap_result(event_id)
            )
            if bootstrap is not None:
                labels = {
                    "adjudication_required": (
                        "Comentariu acid: adjudicare necesară",
                        "Confirmă faptele înainte de stabilirea construcției editoriale.",
                    ),
                    "fact_adjudication_incomplete": (
                        "Comentariu acid: adjudicare în curs",
                        "Adjudicarea faptelor este incompletă și poate fi continuată.",
                    ),
                    "mechanic_adjudication_required": (
                        "Comentariu acid: confirmare mecanism necesară",
                        "Faptele sunt finalizate; confirmă relația editorială.",
                    ),
                    "stale": (
                        "Comentariu acid: reevaluare necesară",
                        "Autoritatea din amonte s-a schimbat; deciziile vechi nu sunt reutilizate.",
                    ),
                    "integrity_failure": (
                        "Comentariu acid: eroare de integritate",
                        "Starea guvernată nu poate fi reconstruită în siguranță.",
                    ),
                }
                title, message = labels.get(
                    bootstrap.status.value, labels["integrity_failure"]
                )
                interaction = EditorVoiceInteractionV2(
                    state=EditorDeterministicVoiceStateV2.INTEGRITY_FAILURE,
                    title=title,
                    message=message,
                )
                return VoiceDesktopPresentationV2(
                    event_id=event_id,
                    interaction=interaction,
                    refresh_enabled=True,
                    adjudication=self._adjudication_presentation(event_id),
                )
            interaction = EditorVoiceInteractionV2(
                state=EditorDeterministicVoiceStateV2.NO_ELIGIBLE_PROGRAM,
                title="Comentariu acid: fără construcție eligibilă",
                message="Materialul nu are încă o construcție editorială sigură.",
            )
            return VoiceDesktopPresentationV2(
                event_id=event_id, interaction=interaction, refresh_enabled=True
            )
        if self.context.accepted_commentary_text is not None:
            return self._current(
                "Comentariul acid este deja generat și acceptat.",
                interaction=EditorVoiceInteractionV2(
                    state=EditorDeterministicVoiceStateV2.PREVIEW_GENERATED,
                    title="Comentariu acid: generat",
                    message="Comentariul acid este deja generat și acceptat.",
                ),
                preview_text=self.context.accepted_commentary_text,
            )
        if self.daily_use_automation and automate:
            return self._run_daily_use_automation()
        interaction = self.application.present_programs(
            self.context.program_eligibility
        )
        return VoiceDesktopPresentationV2(
            event_id=event_id,
            interaction=interaction,
            program_choices=tuple(
                (item.candidate_identity, item.label) for item in interaction.choices
            ),
        )

    def _run_daily_use_automation(self) -> VoiceDesktopPresentationV2:
        """Select, render, and accept one governed deterministic path."""

        assert self.context is not None
        programs = self.application.present_programs(self.context.program_eligibility)
        if not programs.choices:
            return self._current(
                "Nu există momentan o construcție editorială sigură.",
                interaction=self.application.present_programs(
                    self.context.program_eligibility
                ),
            )
        selected = self._select_program(programs.choices[0].candidate_identity)
        if self.program_receipt is None or self.expression_result is None:
            return selected
        selected = self._select_expression(None)
        if self.expression_receipt is None:
            return selected
        preview = self._preview()
        if (
            self.preview_result is None
            or self.preview_result.kind is not DeterministicTerminalKindV2.GENERATED
        ):
            return preview
        rendered = self.preview_result.rendered_utf8.decode("utf-8")
        accepted = self._accept()
        if accepted.interaction.diagnostic_code:
            return accepted
        return self._current(
            "Comentariul acid a fost generat și acceptat automat.",
            interaction=EditorVoiceInteractionV2(
                state=EditorDeterministicVoiceStateV2.PREVIEW_GENERATED,
                title="Comentariu acid: generat",
                message="Comentariul acid a fost generat și acceptat automat.",
            ),
            preview_text=rendered,
        )

    def _adjudication_presentation(self, event_id: int):
        if self.adjudication_coordinator is None:
            return None
        state = self.adjudication_coordinator.service.store.load(event_id)
        return None if state is None else present_voice_adjudication_v1(state)

    def _select_program(self, candidate: str | None) -> VoiceDesktopPresentationV2:
        assert self.context is not None
        try:
            self.program_receipt = self.application.select_program(
                result=self.context.program_eligibility,
                snapshot=self.context.repetition_snapshot,
                candidate_identity=candidate,
                owner_identity=self.owner_identity,
                selected_at=datetime.now(UTC),
            )
        except ValueError:
            return self._integrity(self.context.event_id, "stale_program_eligibility")
        if self.context.persist_program_selection is not None:
            try:
                self.context = self.context.persist_program_selection(
                    self.program_receipt
                )
            except ValueError:
                return self._integrity(
                    self.context.event_id, "program_persistence_failed"
                )
        self.preview_result = None
        if candidate is None:
            self.expression_result = None
            self.expression_receipt = None
            return self._current(
                self.application.present_owner_none_commentary().message,
                interaction=self.application.present_owner_none_commentary(),
            )
        try:
            self.expression_result = self.context.expression_eligibility_for_program(
                self.program_receipt
            )
        except ValueError:
            return self._integrity(
                self.context.event_id, "stale_expression_eligibility"
            )
        interaction = self.application.present_expressions(self.expression_result)
        return self._current(
            interaction.message,
            interaction=interaction,
            expression_choices=tuple(
                (item.candidate_identity, item.label) for item in interaction.choices
            ),
        )

    def _select_expression(self, candidate: str | None) -> VoiceDesktopPresentationV2:
        assert self.context is not None
        if self.program_receipt is None or self.expression_result is None:
            return self._integrity(self.context.event_id, "stale_program_receipt")
        try:
            self.expression_receipt = self.application.select_expression(
                result=self.expression_result,
                snapshot=self.context.repetition_snapshot,
                candidate_identity=candidate,
                owner_identity=self.owner_identity,
                selected_at=datetime.now(UTC),
            )
        except ValueError:
            return self._integrity(self.context.event_id, "stale_expression_receipt")
        if self.context.persist_expression_selection is not None:
            try:
                self.context = self.context.persist_expression_selection(
                    self.expression_result, self.expression_receipt
                )
            except ValueError:
                return self._integrity(
                    self.context.event_id, "expression_persistence_failed"
                )
        self.preview_result = None
        return self._current(
            self.application.present_owner_none_expression().message,
            interaction=self.application.present_owner_none_expression(),
            preview_enabled=True,
        )

    def _preview(self) -> VoiceDesktopPresentationV2:
        assert self.context is not None
        if self.program_receipt is None or self.expression_receipt is None:
            return self._integrity(self.context.event_id, "selection_receipt_missing")
        try:
            request = self.context.execution_request(
                self.program_receipt, self.expression_receipt
            )
            selected = next(
                (
                    item
                    for item in request.program_eligibility.shortlist
                    if item.candidate_id
                    == request.program_selection.selected_candidate_id
                ),
                None,
            )
            if (
                selected is not None
                and selected.program_id == GOVERNED_REALIZATION_PROGRAM_ID
                and (
                    self.governed_realizer is not None
                    or self.governed_realizer_required
                )
            ):
                if self.governed_realizer is None:
                    result = VoiceSafelyAbstainedResultV2(
                        renderer_identity=REALIZER_IDENTITY,
                        request_identity=request.request_identity,
                        reason_code="governed_local_model_unavailable",
                        governed_identity=request.request_identity,
                    )
                    result = result.model_copy(
                        update={
                            "result_identity": canonical_identity(
                                result.model_copy(
                                    update={
                                        "result_identity": "sha256:" + "0" * 64
                                    }
                                )
                            )
                        }
                    )
                else:
                    result = self._governed_model_preview(request, selected.program_id)
                if result.kind is DeterministicTerminalKindV2.GENERATED:
                    interaction = EditorVoiceInteractionV2(
                        state=EditorDeterministicVoiceStateV2.PREVIEW_GENERATED,
                        title="Previzualizare comentariu acid",
                        message=result.rendered_utf8.decode("utf-8"),
                        acceptance_enabled=True,
                    )
                else:
                    interaction = EditorVoiceInteractionV2(
                        state=EditorDeterministicVoiceStateV2.SAFE_ABSTENTION,
                        title="Comentariu omis în siguranță",
                        message="Modelul local nu a produs un comentariu nonfactual valid.",
                        diagnostic_code=result.reason_code,
                    )
            else:
                result, interaction = self.application.preview(request)
            if self.context.persist_preview is not None:
                self.context = self.context.persist_preview(request, result)
        except ValueError:
            return self._integrity(
                self.context.event_id, "renderer_schema_hash_mismatch"
            )
        self.preview_result = result
        return self._current(
            interaction.message,
            interaction=interaction,
            preview_text=(
                interaction.message
                if result.kind is DeterministicTerminalKindV2.GENERATED
                else ""
            ),
            preview_enabled=True,
            accept_enabled=interaction.acceptance_enabled,
            reject_enabled=True,
        )

    def _governed_model_preview(self, request, program_id):
        outcome = self.governed_realizer.realize(
            program_id=program_id, factual_summary=self.context.factual_summary
        )
        receipt_identity = (
            outcome.receipt.receipt_identity
            if outcome.receipt is not None
            else canonical_identity(
                {
                    "realizer": REALIZER_IDENTITY,
                    "request": request.request_identity,
                    "reason": outcome.reason_code,
                }
            )
        )
        if outcome.model_calls == 0:
            result = VoiceSafelyAbstainedResultV2(
                renderer_identity=REALIZER_IDENTITY,
                request_identity=request.request_identity,
                reason_code=outcome.reason_code or "governed_realizer_abstained",
                governed_identity=receipt_identity,
            )
            return result.model_copy(
                update={
                    "result_identity": canonical_identity(
                        result.model_copy(
                            update={"result_identity": "sha256:" + "0" * 64}
                        )
                    )
                }
            )
        common = {
            "backend_kind": DeterministicBackendKindV2.GOVERNED_MODEL_REALIZER,
            "renderer_identity": REALIZER_IDENTITY,
            "request_identity": request.request_identity,
            "model_calls": outcome.model_calls,
            "provider_calls": outcome.provider_calls,
            "model_loads": outcome.model_loads,
            "model_identity": (
                outcome.receipt.model_identity
                if outcome.receipt is not None
                else "pastila-editor-core-v1.2-experimental"
            ),
            "realization_receipt_identity": receipt_identity,
            "realization_receipt": outcome.receipt,
        }
        if outcome.commentary is None:
            result = VoiceSafelyAbstainedResultV2(
                **common,
                reason_code=outcome.reason_code or "governed_realizer_abstained",
                governed_identity=receipt_identity,
            )
        else:
            encoded = outcome.commentary.encode("utf-8")
            output_sha = __import__("hashlib").sha256(encoded).hexdigest()
            provenance = (
                RenderedProvenanceSpanV1(
                    start=0,
                    end=len(encoded),
                    provenance_class=ProvenanceClassV1.NONFACTUAL_COMIC_SURFACE,
                    source_identity=receipt_identity,
                ),
            )
            result = VoiceGeneratedResultV2(
                **common,
                canonical_ir_identity=receipt_identity.removeprefix("sha256:"),
                rendered_utf8=encoded,
                rendered_sha256=output_sha,
                provenance=provenance,
                validation_identity=canonical_identity(
                    {
                        "receipt": receipt_identity,
                        "output": output_sha,
                        "factual_summary": self.context.factual_summary,
                    }
                ),
            )
        return result.model_copy(
            update={
                "result_identity": canonical_identity(
                    result.model_copy(
                        update={"result_identity": "sha256:" + "0" * 64}
                    )
                )
            }
        )

    def _accept(self) -> VoiceDesktopPresentationV2:
        assert self.context is not None
        if (
            self.preview_result is None
            or self.preview_result.kind is not DeterministicTerminalKindV2.GENERATED
        ):
            return self._integrity(self.context.event_id, "stale_preview")
        try:
            request = self.context.acceptance_request(self.preview_result)
            self.context.acceptance_store.accept(request)
        except ValueError:
            return self._integrity(self.context.event_id, "atomic_acceptance_rejected")
        self.preview_result = None
        return self._current("Comentariul determinist a fost acceptat.")

    def _current(
        self,
        message: str,
        *,
        interaction: EditorVoiceInteractionV2 | None = None,
        expression_choices: tuple[tuple[str, str], ...] = (),
        preview_text: str = "",
        preview_enabled: bool = False,
        accept_enabled: bool = False,
        reject_enabled: bool = False,
    ) -> VoiceDesktopPresentationV2:
        assert self.context is not None
        base = interaction or EditorVoiceInteractionV2(
            state=EditorDeterministicVoiceStateV2.PROGRAM_SELECTION_REQUIRED,
            title="Comentariu acid",
            message=message,
        )
        program_interaction = self.application.present_programs(
            self.context.program_eligibility
        )
        if not expression_choices and self.expression_result is not None:
            expression_interaction = self.application.present_expressions(
                self.expression_result
            )
            expression_choices = tuple(
                (item.candidate_identity, item.label)
                for item in expression_interaction.choices
            )
        return VoiceDesktopPresentationV2(
            event_id=self.context.event_id,
            interaction=base,
            program_choices=tuple(
                (item.candidate_identity, item.label)
                for item in program_interaction.choices
            ),
            selected_program_identity=(
                None
                if self.program_receipt is None
                else self.program_receipt.selected_candidate_id
            ),
            program_selection_finalized=self.program_receipt is not None,
            expression_choices=expression_choices,
            selected_expression_identity=(
                None
                if self.expression_receipt is None
                else self.expression_receipt.selected_candidate_id
            ),
            expression_selection_finalized=self.expression_receipt is not None,
            preview_text=preview_text,
            preview_enabled=preview_enabled,
            accept_enabled=accept_enabled,
            reject_enabled=reject_enabled,
        )

    def _integrity(self, event_id: int, code: str) -> VoiceDesktopPresentationV2:
        self.preview_result = None
        return VoiceDesktopPresentationV2(
            event_id=event_id,
            interaction=self.application.present_integrity_failure(
                diagnostic_code=code
            ),
            refresh_enabled=True,
        )


__all__ = [
    "VoiceDesktopContextRegistryV2",
    "VoiceDesktopGovernedContextV2",
    "VoiceDesktopWorkflowCoordinatorV2",
]
