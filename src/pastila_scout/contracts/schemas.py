"""JSON Schema generation for frozen v1 contracts."""

import json
from pathlib import Path

from pastila_scout.contracts.editor_output import EditorAgentOutputV1
from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.contracts.scout_editor import ScoutEditorInputV1
from pastila_scout.contracts.selection_profile import SelectionProfileV1

SCHEMA_MODELS = {
    "scout-editor-input-v1.schema.json": ScoutEditorInputV1,
    "editor-agent-output-v1.schema.json": EditorAgentOutputV1,
    "editor-selection-profile-v1.schema.json": SelectionProfileV1,
    "episode-context-v1.schema.json": EpisodeContextV1,
}


def write_json_schemas(output_directory: Path) -> tuple[Path, ...]:
    """Write deterministic UTF-8 JSON Schemas for all public contracts."""

    output_directory.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for filename, model in SCHEMA_MODELS.items():
        path = output_directory / filename
        path.write_text(
            json.dumps(
                model.model_json_schema(),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        paths.append(path)
    return tuple(paths)
