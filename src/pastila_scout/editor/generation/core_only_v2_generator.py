"""Core-only Semantic Draft V2 generation without legacy story partitioning."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from itertools import pairwise

from pastila_scout.editor.generation.assembly import TeleprompterFormatter
from pastila_scout.editor.generation.controlled_generator import (
    ControlledGenerationError,
    _event_approved_facts,
)
from pastila_scout.editor.generation.manifest import GenerationManifest
from pastila_scout.editor.generation.models import (
    ComponentAttemptTrace,
    GenerationComponentType,
    GenerationMode,
    GenerationPolicy,
    GenerationTrace,
    ManifestItemStatus,
    RetryReason,
    TeleprompterProfile,
    TransitionGenerationContext,
    TransitionGenerationResult,
)
from pastila_scout.editor.generation.prompt import PromptBuilder
from pastila_scout.editor.generation.provider import (
    ProviderError,
    ProviderStructuredOutputError,
    ProviderTimeoutError,
)
from pastila_scout.editor.generation.semantic_draft_v2 import (
    AcidCommentaryExecutionProvenanceV2,
    AcidCommentaryGenerationContextV2,
    AcidCommentaryGenerationResultV2,
    AcidCommentaryV2,
    AuthorityDensityV2,
    ControlledSemanticGenerationResultV2,
    CrossStoryTransitionV2,
    FactualNucleusBindingV2,
    FactualSummaryV2,
    PastilaEditorSemanticDraftV2,
    SemanticDraftModeV2,
    SemanticGenerationStateV2,
    SemanticStoryV2,
)
from pastila_scout.editor.generation.state import EpisodeGenerationState
from pastila_scout.editor.generation.validation import (
    validate_transition,
    validate_v1_2_numeric_factual_consistency,
)
from pastila_scout.editor_generation_authority_v1.canonical import (
    canonical_value,
    semantic_fingerprint,
)

_SENTENCE = re.compile(r"[^.!?\n]+(?:[.!?]+|$)", re.UNICODE)
_TOKEN = re.compile(r"\d+(?:[.,]\d+)*|[^\W\d_]+", re.UNICODE)
_AUTHORITY_PREFIX = re.compile(
    r"^(?:Sursa|Titlu|Rezumat|Publicat|Statut extras):\s*", re.IGNORECASE
)
_NON_FACTUAL_AUTHORITY_PREFIXES = ("sursa:", "statut extras:")


@dataclass(frozen=True, slots=True)
class _AuthorityUnit:
    identity: str
    text: str
    tokens: frozenset[str]


class CoreOnlyV2Generator:
    """Project governed facts and generate only the separate commentary layer."""

    def __init__(
        self,
        provider,
        *,
        config,
        policy=None,
        prompt_builder=None,
        transitions_enabled=True,
    ):
        self.provider = provider
        self.config = config
        self.policy = policy or GenerationPolicy()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.transitions_enabled = bool(transitions_enabled)

    def generate(
        self,
        *,
        scout_input,
        selection_profile,
        episode_context,
        flow_result,
        editorial_blueprint,
        commentary_blueprint,
        voice_plan,
        static_cta_content="",
        teleprompter_profile=None,
    ) -> ControlledSemanticGenerationResultV2:
        del selection_profile, flow_result, static_cta_content
        order = commentary_blueprint.flow_order
        if order != editorial_blueprint.flow_order or order != voice_plan.flow_order:
            raise ControlledGenerationError("upstream deterministic orders disagree")
        event_map = {item.event_id: item for item in scout_input.ranked_events}
        commentary_map = {
            item.event_id: item for item in commentary_blueprint.stories
        }
        if set(order) - set(event_map) or set(order) - set(commentary_map):
            raise ControlledGenerationError("V2 factual event context is incomplete")

        # A model-generated transition can introduce a factual paraphrase.  Under
        # the approved commentary-only authority it is therefore never invoked.
        include_transitions = False
        manifest = GenerationManifest.build_semantic_v2(
            order,
            include_transitions=include_transitions,
            maximum_attempts=self.policy.max_attempts_per_component,
        )
        episode_prompt_context = {
            "episode_id": scout_input.report_id,
            "mode": SemanticDraftModeV2.CORE_PLUS_VOICE.value,
            "optimized_story_order": order,
        }
        traces: list[ComponentAttemptTrace] = []
        stories: list[SemanticStoryV2] = []
        prompt_receipts: list[str] = []
        authority_references: list[str] = []

        for position, event_id in enumerate(order, 1):
            event = event_map[event_id]
            facts = _event_approved_facts(event)
            factual_summary = _factual_summary(
                event.canonical_summary,
                event=event,
                facts=facts,
                provider_identifier="none",
                model_identifier="governed-scout-factual-summary-v1",
                authoring_owner="governed_scout_projection_v1",
            )
            context = AcidCommentaryGenerationContextV2(
                story_id=event_id,
                flow_position=position,
                immutable_factual_summary=factual_summary.text,
                commentary_plan=commentary_map[event_id].model_dump(mode="json"),
            )
            result, component_traces, status, prompt_fingerprint = self._component(
                item_id=f"story-{position:02d}",
                component_type=GenerationComponentType.STORY,
                target_id=str(event_id),
                episode_context=episode_prompt_context,
                component_context=context,
                output_schema=AcidCommentaryGenerationResultV2,
                validator=lambda value, summary=factual_summary, f=facts: _acid_commentary(
                    value.text,
                    factual_summary=summary.text,
                    authority_surfaces=tuple(item.value for item in f),
                    provider_identifier=self.provider.provider_identifier,
                    model_identifier=self.config.model_identifier,
                ),
                state_revision=len(stories),
            )
            traces.extend(component_traces)
            if status is not ManifestItemStatus.COMPLETED:
                failure_reasons = tuple(
                    error
                    for trace in component_traces
                    for error in trace.validation_errors
                )
                raise ControlledGenerationError(
                    f"V2 nonfactual commentary {event_id} failed generation: "
                    + " | ".join(failure_reasons)
                )
            commentary = result
            stories.append(
                SemanticStoryV2(
                    event_id=event_id,
                    position=position,
                    factual_summary=factual_summary,
                    acid_commentary=commentary,
                    acid_commentary_status="present",
                )
            )
            prompt_receipts.append(prompt_fingerprint)
            authority_references.append(factual_summary.authority_bundle_identity)

        transitions: list[CrossStoryTransitionV2] = []

        draft = PastilaEditorSemanticDraftV2.assemble(
            episode_id=scout_input.report_id,
            mode=SemanticDraftModeV2.CORE_PLUS_VOICE,
            stories=tuple(stories),
            transitions=tuple(transitions),
            provenance_references=tuple(dict.fromkeys(authority_references)),
            generation_receipts=tuple(prompt_receipts),
        )
        assembly_revision = len(stories) + len(transitions)
        traces.append(
            _local_trace(
                "assembly",
                GenerationComponentType.ASSEMBLY,
                draft.assembled_text,
                self.config,
                assembly_revision,
            )
        )
        formatted = TeleprompterFormatter().format(
            draft.assembled_text, teleprompter_profile or TeleprompterProfile()
        )
        draft = draft.model_copy(update={"teleprompter_text": formatted})
        traces.append(
            _local_trace(
                "teleprompter-formatting",
                GenerationComponentType.TELEPROMPTER_FORMATTING,
                formatted,
                self.config,
                assembly_revision + 1,
            )
        )
        completed_ids = {
            *(f"story-{index:02d}" for index in range(1, len(stories) + 1)),
            "assembly",
            "teleprompter-formatting",
        }
        accepted_transition_targets = {
            f"{item.from_event_id}:{item.to_event_id}" for item in transitions
        }
        manifest = manifest.model_copy(
            update={
                "items": tuple(
                    item.model_copy(
                        update={
                            "status": (
                                ManifestItemStatus.COMPLETED
                                if item.item_id in completed_ids
                                or item.target_id in accepted_transition_targets
                                else ManifestItemStatus.SKIPPED
                            )
                        }
                    )
                    for item in manifest.items
                )
            }
        )
        final_revision = assembly_revision + 2
        return ControlledSemanticGenerationResultV2(
            draft=draft,
            trace=GenerationTrace(attempts=tuple(traces)),
            manifest=manifest,
            final_state=SemanticGenerationStateV2(
                revision=final_revision,
                accepted_event_ids=order,
            ),
        )

    def _component(
        self,
        *,
        item_id,
        component_type,
        target_id,
        episode_context,
        component_context,
        output_schema,
        validator,
        state_revision,
    ):
        traces = []
        failures = ()
        last_prompt = ""
        for attempt in range(1, self.policy.max_attempts_per_component + 1):
            mode = GenerationMode.STANDARD
            if attempt > 1:
                mode = GenerationMode.CONSTRAINED
            if (
                attempt == self.policy.max_attempts_per_component
                and self.policy.minimal_safe_enabled
            ):
                mode = GenerationMode.MINIMAL_SAFE
            prompt = self.prompt_builder.build(
                component_type=component_type,
                episode_context=episode_context,
                component_context=component_context,
                state=SemanticGenerationStateV2(
                    revision=state_revision, accepted_event_ids=()
                ),
                output_schema=output_schema,
                mode=mode,
                failures=failures,
            )
            last_prompt = prompt.prompt_fingerprint
            try:
                generated = self._provider_call(prompt, output_schema)
                value = validator(generated)
                errors = ()
            except (ProviderStructuredOutputError, ValueError) as exc:
                value = None
                errors = (str(exc),)
            except ProviderError as exc:
                traces.append(
                    _provider_trace(
                        item_id,
                        component_type,
                        target_id,
                        attempt,
                        mode,
                        prompt.prompt_fingerprint,
                        self.provider.provider_identifier,
                        self.config.model_identifier,
                        (str(exc),),
                        ManifestItemStatus.FAILED,
                        state_revision,
                    )
                )
                return None, tuple(traces), ManifestItemStatus.FAILED, last_prompt
            if not errors:
                traces.append(
                    _provider_trace(
                        item_id,
                        component_type,
                        target_id,
                        attempt,
                        mode,
                        prompt.prompt_fingerprint,
                        self.provider.provider_identifier,
                        self.config.model_identifier,
                        (),
                        ManifestItemStatus.COMPLETED,
                        state_revision,
                    )
                )
                return value, tuple(traces), ManifestItemStatus.COMPLETED, last_prompt
            final = attempt == self.policy.max_attempts_per_component
            status = ManifestItemStatus.FAILED if final else ManifestItemStatus.RETRYING
            traces.append(
                _provider_trace(
                    item_id,
                    component_type,
                    target_id,
                    attempt,
                    mode,
                    prompt.prompt_fingerprint,
                    self.provider.provider_identifier,
                    self.config.model_identifier,
                    errors,
                    status,
                    state_revision,
                )
            )
            failures = errors
        return None, tuple(traces), ManifestItemStatus.FAILED, last_prompt

    def _provider_call(self, prompt, output_schema):
        try:
            return self.provider.generate_structured(
                prompt=prompt, output_schema=output_schema, config=self.config
            )
        except ProviderTimeoutError:
            return self.provider.generate_structured(
                prompt=prompt, output_schema=output_schema, config=self.config
            )


def _factual_summary(
    prose,
    *,
    event,
    facts,
    provider_identifier,
    model_identifier,
    authoring_owner="core_v1_2",
) -> FactualSummaryV2:
    if type(prose) is not str or not prose or prose != prose.strip():
        raise ValueError("V2 factual summary must preserve clean Core prose exactly")
    sentences = _sentences(prose)
    if authoring_owner != "governed_scout_projection_v1" and len(sentences) not in (1, 2):
        raise ValueError("V2 factual summary must contain one or two sentences")
    if authoring_owner != "governed_scout_projection_v1" and prose[-1] not in ".!?":
        raise ValueError("V2 factual summary must end naturally")
    numeric_errors = (
        ()
        if authoring_owner == "governed_scout_projection_v1"
        else validate_v1_2_numeric_factual_consistency(
            prose, tuple(item.value for item in facts)
        )
    )
    if numeric_errors:
        raise ValueError(" | ".join(numeric_errors))

    units = _authority_units(facts)
    bindings = tuple(
        FactualNucleusBindingV2(
            nucleus_id=f"event-{event.event_id}-sentence-{index}",
            sentence_number=index,
            authority_fact_ids=_best_authority_units(sentence, units),
        )
        for index, sentence in enumerate(sentences, 1)
    )
    first = set(bindings[0].authority_fact_ids)
    if len(bindings) == 2 and not set(bindings[1].authority_fact_ids).difference(first):
        raise ValueError(
            "second sentence lacks additional supported nonredundant factual value"
        )
    density = _authority_density(units, sentence_count=len(sentences))
    authority_identity = semantic_fingerprint(
        canonical_value(
            event.event_authority_bundle
            if event.event_authority_bundle is not None
            else tuple(item.model_dump(mode="json") for item in facts)
        )
    )
    receipt = semantic_fingerprint(
        canonical_value(
            {
                "event_id": event.event_id,
                "authority": authority_identity,
                "text": prose,
                "bindings": tuple(item.model_dump(mode="json") for item in bindings),
            }
        )
    )
    return FactualSummaryV2(
        text=prose,
        authority_bundle_identity=authority_identity,
        authority_density=density,
        nucleus_bindings=bindings,
        authoring_owner=authoring_owner,
        model_identifier=model_identifier,
        provider=provider_identifier,
        validation_receipt=receipt,
    )


def _acid_commentary(
    prose,
    *,
    factual_summary,
    authority_surfaces,
    provider_identifier,
    model_identifier,
) -> AcidCommentaryV2:
    """Accept only bounded nonfactual prose; uncertainty fails closed."""

    if type(prose) is not str or not prose or prose != prose.strip():
        raise ValueError("commentary must be clean nonempty prose")
    if any(character.isdigit() for character in prose):
        raise ValueError("commentary contains a prohibited factual numeric surface")
    if any(mark in prose for mark in ('"', "„", "”", "«", "»")):
        raise ValueError("commentary contains a prohibited quotation surface")

    commentary_tokens = _tokens(prose)
    factual_tokens = set(_tokens("\n".join((factual_summary, *authority_surfaces))))
    # Three shared content tokens are enough to create a plausible factual
    # paraphrase.  Reject rather than guessing whether the sentence is satire.
    shared = tuple(dict.fromkeys(token for token in commentary_tokens if token in factual_tokens))
    if len(shared) >= 3:
        raise ValueError("commentary overlaps factual authority and may paraphrase it")

    factual_markers = {
        "anuntat", "confirmat", "declarat", "publicat", "raportat", "potrivit",
        "spune", "sustine", "afirma", "avut", "produs", "cauzat",
    }
    if set(commentary_tokens) & factual_markers:
        raise ValueError("commentary contains a prohibited factual-assertion marker")

    boundary = semantic_fingerprint(
        canonical_value(
            {
                "immutable_factual_summary": factual_summary,
                "commentary": prose,
                "shared_authority_tokens": shared,
                "rule": "NONFACTUAL_COMMENTARY_ONLY_NO_FACTUAL_CLAIMS_OR_PARAPHRASES",
            }
        )
    )
    provenance_identity = semantic_fingerprint(
        canonical_value((provider_identifier, model_identifier, boundary))
    )
    return AcidCommentaryV2(
        text=prose,
        factual_boundary_receipt=boundary,
        execution_provenance=AcidCommentaryExecutionProvenanceV2(
            backend_kind="model",
            backend_identity=model_identifier,
            character_provenance_identity=provenance_identity,
            acceptance_transaction_identity=boundary,
            model_calls=1,
            provider_calls=1,
            model_loads=1,
        ),
    )


def _transition(result, context, *, supported_surfaces):
    if type(result) is not TransitionGenerationResult:
        raise ValueError("V2 transition result is invalid")
    if result.text != result.text.strip() or result.text[-1] not in ".!?":
        raise ValueError("V2 transition must be finite prose")
    outcome = validate_transition(result, context, EpisodeGenerationState())
    numeric = validate_v1_2_numeric_factual_consistency(
        result.text, supported_surfaces
    )
    errors = (*outcome.errors, *numeric)
    if errors:
        raise ValueError(" | ".join(errors))
    return result


def _authority_units(facts) -> tuple[_AuthorityUnit, ...]:
    units = []
    seen = set()
    for fact in facts:
        pieces = []
        for line in fact.value.splitlines():
            normalized_line = line.strip()
            if not normalized_line or normalized_line.casefold().startswith(
                _NON_FACTUAL_AUTHORITY_PREFIXES
            ):
                continue
            pieces.extend(_sentences(_AUTHORITY_PREFIX.sub("", normalized_line)))
        if not pieces:
            pieces = [fact.value]
        for index, piece in enumerate(pieces, 1):
            normalized = _normalize(piece)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            units.append(
                _AuthorityUnit(
                    identity=f"{fact.fact_id}:unit-{index}",
                    text=piece,
                    tokens=frozenset(_tokens(piece)),
                )
            )
    if not units:
        raise ValueError("V2 factual authority has no usable units")
    return tuple(units)


def _best_authority_units(sentence, units) -> tuple[str, ...]:
    sentence_tokens = frozenset(_tokens(sentence))
    scores = tuple((len(sentence_tokens & unit.tokens), unit) for unit in units)
    best = max(score for score, _ in scores)
    minimum = min(2, len(sentence_tokens))
    if best < minimum:
        raise ValueError("factual sentence has no deterministic authority support")
    return tuple(unit.identity for score, unit in scores if score == best)


def _authority_density(units, *, sentence_count):
    if len(units) == 1 and len(units[0].tokens) <= 20:
        return AuthorityDensityV2.THIN
    if sentence_count == 2:
        return AuthorityDensityV2.COMPLEMENTARY
    return AuthorityDensityV2.STANDARD


def _sentences(value):
    return tuple(item.strip() for item in _SENTENCE.findall(value) if item.strip())


def _tokens(value):
    return tuple(
        token
        for token in (_normalize(item) for item in _TOKEN.findall(value))
        if len(token) >= 3 or token[:1].isdigit()
    )


def _normalize(value):
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(item for item in decomposed if not unicodedata.combining(item))


def _pairwise(values):
    return tuple(pairwise(values))


def _provider_trace(
    item_id,
    component_type,
    target_id,
    attempt,
    mode,
    prompt_fingerprint,
    provider_identifier,
    model_identifier,
    errors,
    status,
    revision,
):
    return ComponentAttemptTrace(
        manifest_item_id=item_id,
        component_type=component_type,
        target_id=target_id,
        attempt_number=attempt,
        generation_mode=mode,
        prompt_fingerprint=prompt_fingerprint,
        provider_identifier=provider_identifier,
        model_identifier=model_identifier,
        validation_errors=errors,
        validation_warnings=(),
        retry_reason=RetryReason.INVALID_SCHEMA if errors else None,
        acceptance_status=status,
        state_revision_before=revision,
        state_revision_after=revision + (status is ManifestItemStatus.COMPLETED),
    )


def _local_trace(item_id, component_type, text, config, revision):
    fingerprint = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    return ComponentAttemptTrace(
        manifest_item_id=item_id,
        component_type=component_type,
        target_id="episode",
        attempt_number=1,
        generation_mode=GenerationMode.STANDARD,
        prompt_fingerprint=fingerprint,
        provider_identifier="deterministic-local",
        model_identifier=config.model_identifier,
        validation_errors=(),
        validation_warnings=(),
        retry_reason=None,
        acceptance_status=ManifestItemStatus.COMPLETED,
        state_revision_before=revision,
        state_revision_after=revision + 1,
    )


__all__ = ["CoreOnlyV2Generator"]
