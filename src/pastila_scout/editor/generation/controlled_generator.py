"""Sequential provider-independent controlled generation orchestration."""

import hashlib
from itertools import pairwise

from pastila_scout.editor.generation.assembly import (
    DraftAssembler,
    TeleprompterFormatter,
    plan_cta,
)
from pastila_scout.editor.generation.manifest import GenerationManifest
from pastila_scout.editor.generation.models import (
    ApprovedFact,
    CallToActionDraft,
    CallToActionGenerationResult,
    ClosingGenerationContext,
    ClosingGenerationResult,
    ComponentAttemptTrace,
    ControlledGenerationResult,
    CTAPlacement,
    DraftStory,
    DraftTransition,
    EpisodeGenerationContext,
    GenerationComponentType,
    GenerationMode,
    GenerationPolicy,
    GenerationTrace,
    ManifestItemStatus,
    OpeningGenerationContext,
    OpeningGenerationResult,
    RetryReason,
    StoryGenerationContext,
    StoryGenerationResult,
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
from pastila_scout.editor.generation.state import EpisodeGenerationState
from pastila_scout.editor.generation.validation import (
    ValidationOutcome,
    validate_closing,
    validate_opening,
    validate_story,
    validate_transition,
)
from pastila_scout.expression_retrieval_v1.editor_adapter import (
    build_story_voice_palette_for_editor_v1,
    serialize_story_voice_palette_v1,
)


class ControlledGenerationError(RuntimeError):
    """Raised when a required component cannot be generated safely."""


class ControlledGenerator:
    """Generate components sequentially and assemble an immutable episode draft."""

    def __init__(self, provider, *, config, policy=None, prompt_builder=None):
        self.provider = provider
        self.config = config
        self.policy = policy or GenerationPolicy()
        self.prompt_builder = prompt_builder or PromptBuilder()

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
    ):
        order = commentary_blueprint.flow_order
        if order != editorial_blueprint.flow_order or order != voice_plan.flow_order:
            raise ControlledGenerationError("upstream deterministic orders disagree")
        global_context = EpisodeGenerationContext(
            episode_id=scout_input.report_id,
            episode_type="editorial_episode",
            episode_theme=editorial_blueprint.thesis.dominant_theme.value,
            optimized_story_order=order,
            episode_voice_profile=voice_plan.model_dump(
                mode="json", exclude={"stories"}
            ),
            teleprompter_profile=teleprompter_profile or TeleprompterProfile(),
            global_budgets={
                "callbacks": voice_plan.callback_budget,
                "vocatives": voice_plan.vocative_budget,
                "expressions": voice_plan.expression_budget.maximum_total,
            },
            callback_policy={"registered_only": True},
            repetition_policy=voice_plan.anti_repetition.model_dump(mode="json"),
            audience_relationship="intelligent_peer",
            language_generation_config=self.config,
        )
        cta_plan = plan_cta(
            commentary_blueprint.stories, static_content=static_cta_content
        )
        manifest = GenerationManifest.build(
            order,
            include_cta=cta_plan.placement is not CTAPlacement.OMITTED,
            maximum_attempts=self.policy.max_attempts_per_component,
        )
        state = EpisodeGenerationState()
        traces = []
        story_results = []
        event_map = {event.event_id: event for event in scout_input.ranked_events}
        editorial_map = {item.event_id: item for item in editorial_blueprint.segments}
        commentary_map = {item.event_id: item for item in commentary_blueprint.stories}
        voice_map = {item.event_id: item for item in voice_plan.stories}
        for position, story_id in enumerate(order, 1):
            event = event_map[story_id]
            story_context = _story_context(
                event,
                position,
                editorial_map[story_id],
                commentary_map[story_id],
                voice_map[story_id],
            )
            result, component_traces, status = self._component(
                item_id=f"story-{position:02d}",
                component_type=GenerationComponentType.STORY,
                target_id=str(story_id),
                episode_context=global_context,
                component_context=story_context,
                output_schema=StoryGenerationResult,
                validator=lambda value, c=story_context, s=state: validate_story(
                    value, c, s
                ),
                state=state,
            )
            traces.extend(component_traces)
            if status is ManifestItemStatus.FAILED:
                raise ControlledGenerationError(f"story {story_id} failed generation")
            state = state.accept_story(f"story-{position:02d}", result)
            story_results.append(result)
        transition_results = []
        transition_map = {
            item.from_event_id: item for item in editorial_blueprint.transitions
        }
        for position, (left, right) in enumerate(pairwise(order), 1):
            context = TransitionGenerationContext(
                from_story_id=left,
                to_story_id=right,
                previous_story_ending_summary=state.ending_summary(left),
                next_story_factual_summary=state.factual_summary(right),
                transition_plan=transition_map[left].model_dump(mode="json"),
                voice_profile=voice_map[left].model_dump(mode="json"),
                callback_context=state.available_callback_ids(
                    f"transition-{position:02d}-{position + 1:02d}"
                ),
                word_budget=50,
            )
            result, item_traces, status = self._component(
                item_id=f"transition-{position:02d}-{position + 1:02d}",
                component_type=GenerationComponentType.TRANSITION,
                target_id=f"{left}:{right}",
                episode_context=global_context,
                component_context=context,
                output_schema=TransitionGenerationResult,
                validator=lambda value, c=context, s=state: validate_transition(
                    value, c, s
                ),
                state=state,
            )
            traces.extend(item_traces)
            if status is ManifestItemStatus.FAILED:
                raise ControlledGenerationError("transition failed generation")
            state = state.accept_transition(
                f"transition-{position:02d}-{position + 1:02d}", result
            )
            transition_results.append(result)
        opening_context = OpeningGenerationContext(
            opening_plan=editorial_blueprint.opening.model_dump(mode="json"),
            accepted_story_ids=order,
            accepted_story_summaries=tuple(
                state.factual_summary(item) for item in order
            ),
            protected_payoffs=(),
            episode_voice_profile=global_context.episode_voice_profile,
            word_budget=100,
            runtime_budget=60,
        )
        opening, item_traces, status = self._component(
            item_id="opening",
            component_type=GenerationComponentType.OPENING,
            target_id="episode",
            episode_context=global_context,
            component_context=opening_context,
            output_schema=OpeningGenerationResult,
            validator=lambda value: validate_opening(value, opening_context),
            state=state,
        )
        traces.extend(item_traces)
        if status is ManifestItemStatus.FAILED:
            raise ControlledGenerationError("opening failed generation")
        state = state.accept_opening("opening", opening)
        closing_context = ClosingGenerationContext(
            closing_plan=editorial_blueprint.closing.model_dump(mode="json"),
            story_ending_summaries=tuple(state.ending_summary(item) for item in order),
            available_callback_anchors=state.available_callback_ids("closing"),
            episode_theme=global_context.episode_theme,
            emotional_arc=tuple(item.value for item in voice_plan.emotional_arc),
            cta_placement_plan=cta_plan.to_provider_context(),
            word_budget=100,
        )
        closing, item_traces, status = self._component(
            item_id="closing",
            component_type=GenerationComponentType.CLOSING,
            target_id="episode",
            episode_context=global_context,
            component_context=closing_context,
            output_schema=ClosingGenerationResult,
            validator=lambda value: validate_closing(value, closing_context, state),
            state=state,
        )
        traces.extend(item_traces)
        if status is ManifestItemStatus.FAILED:
            raise ControlledGenerationError("closing failed generation")
        state = state.accept_component(
            "closing", closing.warnings, closing.callback_executions
        )
        cta = None
        if cta_plan.placement is not CTAPlacement.OMITTED:
            provider_cta_context = cta_plan.to_provider_context()
            generated, item_traces, status = self._component(
                item_id="cta",
                component_type=GenerationComponentType.CALL_TO_ACTION,
                target_id="episode",
                episode_context=global_context,
                component_context=provider_cta_context,
                output_schema=CallToActionGenerationResult,
                validator=lambda value: ValidationOutcome(),
                state=state,
            )
            traces.extend(item_traces)
            if status is not ManifestItemStatus.FAILED:
                cta = CallToActionDraft(
                    placement=cta_plan.placement,
                    after_story_id=cta_plan.after_story_id,
                    bridge_text=generated.bridge_text,
                    static_content=cta_plan.static_content,
                )
                state = state.accept_component("cta", generated.warnings)
        draft_stories = tuple(
            DraftStory(
                story_id=item.story_id,
                factual_summary=item.factual_summary,
                commentary_blocks=item.commentary_blocks,
                ending=item.ending,
            )
            for item in story_results
        )
        draft_transitions = tuple(
            DraftTransition(
                from_story_id=item.from_story_id,
                to_story_id=item.to_story_id,
                text=item.text,
            )
            for item in transition_results
        )
        draft = DraftAssembler().assemble(
            episode_id=global_context.episode_id,
            story_order=order,
            opening=opening.text,
            stories=draft_stories,
            transitions=draft_transitions,
            closing=closing.text,
            cta=cta,
        )
        assembly_before = state.revision
        state = state.accept_component("assembly")
        traces.append(
            _local_trace(
                "assembly",
                GenerationComponentType.ASSEMBLY,
                draft.assembled_text,
                self.config,
                assembly_before,
                state.revision,
            )
        )
        formatted = TeleprompterFormatter().format(
            draft.assembled_text, global_context.teleprompter_profile
        )
        draft = draft.model_copy(update={"teleprompter_text": formatted})
        formatting_before = state.revision
        state = state.accept_component("teleprompter-formatting")
        traces.append(
            _local_trace(
                "teleprompter-formatting",
                GenerationComponentType.TELEPROMPTER_FORMATTING,
                formatted,
                self.config,
                formatting_before,
                state.revision,
            )
        )
        manifest = manifest.model_copy(
            update={
                "items": tuple(
                    item.model_copy(update={"status": ManifestItemStatus.COMPLETED})
                    for item in manifest.items
                )
            }
        )
        return ControlledGenerationResult(
            draft=draft,
            trace=GenerationTrace(attempts=tuple(traces)),
            manifest=manifest,
            final_state=state,
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
        state,
    ):
        traces = []
        failures = ()
        last_result = None
        for attempt in range(1, self.policy.max_attempts_per_component + 1):
            mode = (
                GenerationMode.STANDARD if attempt == 1 else GenerationMode.CONSTRAINED
            )
            if (
                attempt == self.policy.max_attempts_per_component
                and self.policy.minimal_safe_enabled
            ):
                mode = GenerationMode.MINIMAL_SAFE
            prompt = self.prompt_builder.build(
                component_type=component_type,
                episode_context=episode_context,
                component_context=component_context,
                state=state,
                output_schema=output_schema,
                mode=mode,
                failures=failures,
            )
            try:
                result = self._provider_call(prompt, output_schema)
            except ProviderStructuredOutputError as exc:
                outcome = ValidationOutcome(
                    errors=(str(exc),),
                    retry_reason=RetryReason.INVALID_SCHEMA,
                    fatal=True,
                )
                result = None
            except ProviderError as exc:
                traces.append(
                    _trace(
                        item_id,
                        component_type,
                        target_id,
                        attempt,
                        mode,
                        prompt,
                        self.provider,
                        self.config,
                        (str(exc),),
                        (),
                        RetryReason.PROVIDER_ERROR,
                        ManifestItemStatus.FAILED,
                        state.revision,
                        state.revision,
                    )
                )
                return None, tuple(traces), ManifestItemStatus.FAILED
            if result is not None:
                outcome = validator(result)
                last_result = result
            if outcome.accepted:
                traces.append(
                    _trace(
                        item_id,
                        component_type,
                        target_id,
                        attempt,
                        mode,
                        prompt,
                        self.provider,
                        self.config,
                        (),
                        outcome.warnings,
                        None,
                        ManifestItemStatus.COMPLETED,
                        state.revision,
                        state.revision + 1,
                    )
                )
                return result, tuple(traces), ManifestItemStatus.COMPLETED
            final = attempt == self.policy.max_attempts_per_component
            status = (
                ManifestItemStatus.FAILED
                if final and outcome.fatal
                else (
                    ManifestItemStatus.REQUIRES_REVIEW
                    if final
                    else ManifestItemStatus.RETRYING
                )
            )
            traces.append(
                _trace(
                    item_id,
                    component_type,
                    target_id,
                    attempt,
                    mode,
                    prompt,
                    self.provider,
                    self.config,
                    outcome.errors,
                    outcome.warnings,
                    outcome.retry_reason,
                    status,
                    state.revision,
                    (
                        state.revision
                        if status is not ManifestItemStatus.REQUIRES_REVIEW
                        else state.revision + 1
                    ),
                )
            )
            if final:
                return last_result, tuple(traces), status
            failures = outcome.errors
        raise AssertionError("unreachable generation attempt loop")

    def _provider_call(self, prompt, output_schema):
        # One transport retry does not consume an editorial generation attempt.
        try:
            return self.provider.generate_structured(
                prompt=prompt, output_schema=output_schema, config=self.config
            )
        except ProviderTimeoutError:
            return self.provider.generate_structured(
                prompt=prompt, output_schema=output_schema, config=self.config
            )


def _story_context(event, position, editorial, commentary, voice):
    palette = build_story_voice_palette_for_editor_v1(
        event=event,
        episode_position=position,
        commentary=commentary,
        voice=voice,
    )
    facts = (
        ApprovedFact(
            fact_id=f"event-{event.event_id}-title",
            field="canonical_title",
            value=event.canonical_title,
        ),
        ApprovedFact(
            fact_id=f"event-{event.event_id}-summary",
            field="canonical_summary",
            value=event.canonical_summary,
        ),
        ApprovedFact(
            fact_id=f"event-{event.event_id}-categories",
            field="categories",
            value=", ".join(event.categories),
        ),
    )
    return StoryGenerationContext(
        story_id=event.event_id,
        flow_position=position,
        approved_facts=facts,
        editorial_plan={
            "intent_id": f"editorial:{event.event_id}",
            **editorial.model_dump(mode="json"),
        },
        conversation_plan={
            "intent_id": f"conversation:{event.event_id}",
            **commentary.model_dump(mode="json"),
        },
        voice_plan={
            "intent_id": f"voice:{event.event_id}",
            **voice.model_dump(mode="json"),
        },
        optional_editorial_toolkit=serialize_story_voice_palette_v1(palette),
        word_budget=max(80, int(getattr(event, "final_score", 50) * 3)),
        runtime_budget=120,
        protected_targets=tuple(item.value for item in commentary.protected_targets),
        allowed_satire_targets=tuple(item.value for item in commentary.satire_targets),
        forbidden_claims=commentary.factual_summary.prohibited_unsupported_claims,
    )


def _trace(
    item_id,
    component,
    target,
    attempt,
    mode,
    prompt,
    provider,
    config,
    errors,
    warnings,
    reason,
    status,
    before,
    after,
):
    return ComponentAttemptTrace(
        manifest_item_id=item_id,
        component_type=component,
        target_id=target,
        attempt_number=attempt,
        generation_mode=mode,
        prompt_fingerprint=prompt.prompt_fingerprint,
        provider_identifier=provider.provider_identifier,
        model_identifier=config.model_identifier,
        validation_errors=errors,
        validation_warnings=warnings,
        retry_reason=reason,
        acceptance_status=status,
        state_revision_before=before,
        state_revision_after=after,
    )


def _local_trace(item_id, component, content, config, before, after):
    fingerprint = "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()
    return ComponentAttemptTrace(
        manifest_item_id=item_id,
        component_type=component,
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
        state_revision_before=before,
        state_revision_after=after,
    )
