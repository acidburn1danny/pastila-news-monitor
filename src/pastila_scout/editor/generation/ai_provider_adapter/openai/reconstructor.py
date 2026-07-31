"""Deterministic reconstruction of authoritative EpisodeDraft state."""

from __future__ import annotations

from dataclasses import dataclass

from pastila_scout.editor.generation.models import EpisodeDraft, derive_assembled_text
from pastila_scout.editor.generation.revision import ControlledRevisionInvocation

from .models import (
    OpenAIControlledRevisionProviderOutput,
    OpenAIRevisedCallToActionComponent,
    OpenAIRevisedStoryComponent,
    OpenAIRevisedTextComponent,
)


@dataclass(frozen=True, slots=True)
class OpenAIReconstructionError(Exception):
    """Content-free deterministic provider-patch rejection."""

    diagnostic_code: str
    validation_stage: str = "authorization_mapping"


class OpenAIControlledRevisionReconstructor:
    """Apply an authorized provider patch to the immutable source draft."""

    def reconstruct(
        self,
        invocation: ControlledRevisionInvocation,
        provider_output: OpenAIControlledRevisionProviderOutput,
    ) -> EpisodeDraft:
        source = invocation.request.source_draft
        expected = {
            _target_reference(target) for target in invocation.request.revision_targets
        }
        returned = {
            component.component_reference
            for component in provider_output.revised_components
        }
        if returned - expected:
            known = _source_references(source)
            code = (
                "openai_provider_output_reference_unauthorized"
                if (returned - expected) <= known
                else "openai_provider_output_reference_unknown"
            )
            raise OpenAIReconstructionError(code)
        if expected - returned:
            raise OpenAIReconstructionError(
                "openai_provider_output_required_component_missing"
            )

        opening = source.opening
        stories = list(source.stories)
        transitions = list(source.transitions)
        closing = source.closing
        cta = source.cta
        story_positions = {item.story_id: index for index, item in enumerate(stories)}
        transition_positions = {
            (item.from_story_id, item.to_story_id): index
            for index, item in enumerate(transitions)
        }
        for component in provider_output.revised_components:
            reference = component.component_reference
            if isinstance(component, OpenAIRevisedTextComponent):
                if component.component_type == "opening":
                    opening = component.revised_text
                elif component.component_type == "closing":
                    closing = component.revised_text
                else:
                    source_id, target_id = _transition_ids(reference)
                    position = transition_positions.get((source_id, target_id))
                    if position is None:
                        raise OpenAIReconstructionError(
                            "openai_provider_output_reference_unknown"
                        )
                    transitions[position] = transitions[position].model_copy(
                        update={"text": component.revised_text}
                    )
            elif isinstance(component, OpenAIRevisedStoryComponent):
                story_id = int(reference.split(":", 1)[1])
                position = story_positions.get(story_id)
                if position is None:
                    raise OpenAIReconstructionError(
                        "openai_provider_output_reference_unknown"
                    )
                source_story = stories[position]
                if len(component.commentary_block_texts) != len(
                    source_story.commentary_blocks
                ):
                    raise OpenAIReconstructionError(
                        "openai_domain_reconstruction_invalid"
                    )
                blocks = tuple(
                    block.model_copy(update={"text": text})
                    for block, text in zip(
                        source_story.commentary_blocks,
                        component.commentary_block_texts,
                        strict=True,
                    )
                )
                stories[position] = source_story.model_copy(
                    update={
                        "factual_summary": component.factual_summary,
                        "commentary_blocks": blocks,
                        "ending": component.ending,
                    }
                )
            elif isinstance(component, OpenAIRevisedCallToActionComponent):
                if cta is None:
                    raise OpenAIReconstructionError(
                        "openai_provider_output_reference_unknown"
                    )
                cta = cta.model_copy(update={"bridge_text": component.bridge_text})

        story_tuple = tuple(stories)
        transition_tuple = tuple(transitions)
        assembled = derive_assembled_text(
            opening=opening,
            stories=story_tuple,
            transitions=transition_tuple,
            closing=closing,
            cta=cta,
        )
        return EpisodeDraft(
            episode_id=source.episode_id,
            opening=opening,
            stories=story_tuple,
            transitions=transition_tuple,
            closing=closing,
            cta=cta,
            assembled_text=assembled,
            teleprompter_text=assembled,
        )


def _target_reference(target) -> str:
    return target.canonical_reference


def _transition_ids(reference: str) -> tuple[int, int]:
    _, source, target = reference.split(":")
    return int(source), int(target)


def _source_references(source: EpisodeDraft) -> set[str]:
    references = {"opening", "closing"}
    references.update(f"story:{item.story_id}" for item in source.stories)
    references.update(
        f"transition:{item.from_story_id}:{item.to_story_id}"
        for item in source.transitions
    )
    if source.cta is not None:
        references.add("call_to_action")
    return references
