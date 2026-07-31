"""Cross-model validation for private commentary blueprints."""

from pastila_scout.editor.commentary_models import Sensitivity


class CommentaryValidationError(ValueError):
    """Raised when a commentary plan violates evidence or flow boundaries."""


def validate_commentary_blueprint(blueprint, scout_input, context, backup_ids):
    """Validate evidence, optimized order, transitions, and sensitivity policy."""
    if tuple(story.event_id for story in blueprint.stories) != blueprint.flow_order:
        raise CommentaryValidationError(
            "commentary stories must preserve optimized order"
        )
    event_map = {event.event_id: event for event in scout_input.ranked_events}
    for index, story in enumerate(blueprint.stories):
        if story.event_id in backup_ids or story.event_id in context.excluded_event_ids:
            raise CommentaryValidationError(
                "backup-only or excluded story in commentary"
            )
        event = event_map.get(story.event_id)
        if event is None:
            raise CommentaryValidationError("commentary event absent from Scout input")
        valid = {(p.source_id, p.url, p.title) for p in event.source_provenance}
        for ref in story.factual_summary.evidence_references:
            if (ref.source_id, ref.url, ref.title) not in valid:
                raise CommentaryValidationError("invalid commentary evidence reference")
        final = index == len(blueprint.stories) - 1
        if final != (story.transition is None):
            raise CommentaryValidationError(
                "transition cardinality does not match flow"
            )
        if (
            story.transition
            and story.transition.next_event_id != blueprint.flow_order[index + 1]
        ):
            raise CommentaryValidationError("transition does not match next story")
        if story.sensitivity not in (Sensitivity.ORDINARY, Sensitivity.ELEVATED) and (
            not story.empathy.explicit_acknowledgment_required
            or not story.punchline.prohibited_directions
        ):
            raise CommentaryValidationError("sensitive story lacks empathy safeguards")
