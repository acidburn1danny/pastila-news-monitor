"""Lossless neutral carrier for the existing structured ranking task."""

import json

from pastila_scout.ai.provider import StructuredAIRequest


def serialize_ranking_task(task: StructuredAIRequest) -> str:
    """Serialize exact existing task fields without prompt or schema changes."""

    return json.dumps(
        {
            "name": task.name,
            "instructions": task.instructions,
            "input_json": task.input_json,
            "json_schema": task.json_schema,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


__all__ = ("serialize_ranking_task",)
