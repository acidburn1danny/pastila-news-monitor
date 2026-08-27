"""Deterministic generation manifest and dependency readiness."""

from itertools import pairwise

from pydantic import Field

from pastila_scout.editor.generation.models import (
    FrozenModel,
    GenerationComponentType,
    GenerationMode,
    ManifestItemStatus,
)


class GenerationManifestItem(FrozenModel):
    item_id: str
    component_type: GenerationComponentType
    target_id: str
    sequence_index: int = Field(ge=0)
    dependency_ids: tuple[str, ...]
    generation_mode: GenerationMode
    maximum_attempts: int = Field(ge=1, le=3)
    status: ManifestItemStatus = ManifestItemStatus.PENDING
    optional: bool = False

    def derived_status(
        self, statuses: dict[str, ManifestItemStatus]
    ) -> ManifestItemStatus:
        values = tuple(
            statuses.get(item, ManifestItemStatus.PENDING)
            for item in self.dependency_ids
        )
        if any(value is ManifestItemStatus.FAILED for value in values):
            return (
                ManifestItemStatus.SKIPPED
                if self.optional
                else ManifestItemStatus.FAILED
            )
        if all(value is ManifestItemStatus.COMPLETED for value in values):
            return ManifestItemStatus.READY
        return ManifestItemStatus.PENDING


class GenerationManifest(FrozenModel):
    items: tuple[GenerationManifestItem, ...]

    @classmethod
    def build(
        cls, story_ids: tuple[int, ...], *, include_cta: bool, maximum_attempts: int
    ) -> GenerationManifest:
        items = []
        for index, story_id in enumerate(story_ids, 1):
            items.append(
                _item(
                    f"story-{index:02d}",
                    GenerationComponentType.STORY,
                    str(story_id),
                    len(items),
                    (),
                    maximum_attempts,
                )
            )
        story_items = tuple(item.item_id for item in items)
        transition_items = []
        for index, (left, right) in enumerate(pairwise(story_ids), 1):
            item_id = f"transition-{index:02d}-{index + 1:02d}"
            transition_items.append(item_id)
            items.append(
                _item(
                    item_id,
                    GenerationComponentType.TRANSITION,
                    f"{left}:{right}",
                    len(items),
                    (story_items[index - 1], story_items[index]),
                    maximum_attempts,
                )
            )
        items.append(
            _item(
                "opening",
                GenerationComponentType.OPENING,
                "episode",
                len(items),
                story_items,
                maximum_attempts,
            )
        )
        closing_dependencies = (*story_items, *transition_items, "opening")
        items.append(
            _item(
                "closing",
                GenerationComponentType.CLOSING,
                "episode",
                len(items),
                closing_dependencies,
                maximum_attempts,
            )
        )
        required = (*closing_dependencies, "closing")
        if include_cta:
            items.append(
                _item(
                    "cta",
                    GenerationComponentType.CALL_TO_ACTION,
                    "episode",
                    len(items),
                    ("closing",),
                    maximum_attempts,
                    optional=True,
                )
            )
            required = (*required, "cta")
        items.append(
            _item(
                "assembly",
                GenerationComponentType.ASSEMBLY,
                "episode",
                len(items),
                required,
                1,
            )
        )
        items.append(
            _item(
                "teleprompter-formatting",
                GenerationComponentType.TELEPROMPTER_FORMATTING,
                "episode",
                len(items),
                ("assembly",),
                1,
            )
        )
        return cls(items=tuple(items))

    @classmethod
    def build_semantic_v2(
        cls,
        story_ids: tuple[int, ...],
        *,
        include_transitions: bool,
        maximum_attempts: int,
    ) -> GenerationManifest:
        """Build the V2 Core-only graph without opening or closing nodes."""

        items = []
        story_items = []
        for index, story_id in enumerate(story_ids, 1):
            item_id = f"story-{index:02d}"
            story_items.append(item_id)
            items.append(
                _item(
                    item_id,
                    GenerationComponentType.STORY,
                    str(story_id),
                    len(items),
                    (),
                    maximum_attempts,
                )
            )
        transition_items = []
        if include_transitions:
            for index, (left, right) in enumerate(pairwise(story_ids), 1):
                item_id = f"transition-{index:02d}-{index + 1:02d}"
                transition_items.append(item_id)
                items.append(
                    _item(
                        item_id,
                        GenerationComponentType.TRANSITION,
                        f"{left}:{right}",
                        len(items),
                        (story_items[index - 1], story_items[index]),
                        maximum_attempts,
                        optional=True,
                    )
                )
        items.append(
            _item(
                "assembly",
                GenerationComponentType.ASSEMBLY,
                "episode",
                len(items),
                (*story_items, *transition_items),
                1,
            )
        )
        items.append(
            _item(
                "teleprompter-formatting",
                GenerationComponentType.TELEPROMPTER_FORMATTING,
                "episode",
                len(items),
                ("assembly",),
                1,
            )
        )
        return cls(items=tuple(items))


def _item(item_id, component, target, sequence, dependencies, attempts, optional=False):
    return GenerationManifestItem(
        item_id=item_id,
        component_type=component,
        target_id=target,
        sequence_index=sequence,
        dependency_ids=dependencies,
        generation_mode=GenerationMode.STANDARD,
        maximum_attempts=attempts,
        optional=optional,
    )
