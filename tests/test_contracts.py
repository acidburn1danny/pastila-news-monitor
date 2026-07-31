"""Validation, compatibility, identity, and I/O tests for Milestone 6B."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pastila_scout.cli import main
from pastila_scout.contracts import (
    EditorAgentOutputV1,
    EpisodeContextV1,
    ScoutEditorInputV1,
    SelectionProfileV1,
    validate_editor_output_against_input,
)
from pastila_scout.contracts.identity import (
    assign_scout_input_identity,
    scout_input_identity,
    verify_scout_input_identity,
)
from pastila_scout.contracts.io import ContractFileError, load_contract, write_contract
from pastila_scout.contracts.samples import (
    sample_editor_output,
    sample_editor_partial_output,
    sample_episode_context,
    sample_scout_input,
    sample_selection_profile,
    write_sample_contracts,
)
from pastila_scout.contracts.schemas import SCHEMA_MODELS, write_json_schemas


def revalidate(model: object, changes: dict[str, object]) -> object:
    data = model.model_dump(mode="json")  # type: ignore[attr-defined]
    data.update(changes)
    return type(model).model_validate_json(json.dumps(data, ensure_ascii=False))


def proposal_data(output: EditorAgentOutputV1) -> dict[str, object]:
    assert output.episode_proposal is not None
    return output.episode_proposal.model_dump(mode="json")


def test_all_public_samples_are_strict_round_trip_contracts(tmp_path: Path) -> None:
    paths = write_sample_contracts(tmp_path)

    contracts = [load_contract(path) for path in paths]

    assert isinstance(contracts[0], ScoutEditorInputV1)
    assert isinstance(contracts[1], ScoutEditorInputV1)
    assert isinstance(contracts[2], SelectionProfileV1)
    assert isinstance(contracts[3], EpisodeContextV1)
    assert isinstance(contracts[4], EditorAgentOutputV1)
    assert isinstance(contracts[5], EditorAgentOutputV1)
    for contract, path in zip(contracts, paths, strict=True):
        exported = tmp_path / "round-trip" / path.name
        write_contract(contract, exported)
        assert exported.read_bytes() == path.read_bytes()


def test_models_are_immutable_and_reject_unknown_fields() -> None:
    context = sample_episode_context()
    with pytest.raises(ValidationError):
        context.target_story_count = 2  # type: ignore[misc]

    data = context.model_dump(mode="json")
    data["surprise"] = True
    with pytest.raises(ValidationError, match="Extra inputs"):
        EpisodeContextV1.model_validate_json(json.dumps(data))


def test_extensions_are_explicit_and_unknown_extensions_are_preserved() -> None:
    data = sample_episode_context().model_dump(mode="json")
    data["extensions"] = {"vendor.example": {"future": "value"}}

    context = EpisodeContextV1.model_validate_json(json.dumps(data))

    assert context.extensions["vendor.example"] == {"future": "value"}


def test_selection_profile_validates_category_count_order() -> None:
    data = sample_selection_profile().model_dump(mode="json")
    data["category_constraints"]["Politica"].update(  # type: ignore[index]
        {"minimum": 2, "preferred": 1, "maximum": 3}
    )

    with pytest.raises(ValidationError, match="minimum <= preferred <= maximum"):
        SelectionProfileV1.model_validate_json(json.dumps(data))


def test_episode_context_rejects_conflicting_episode_state() -> None:
    context = sample_episode_context()
    data = context.model_dump(mode="json")
    data["mandatory_event_ids"] = [201]

    with pytest.raises(ValidationError, match="recently avoided"):
        EpisodeContextV1.model_validate_json(json.dumps(data))


def test_editorial_notes_are_bounded_and_non_empty() -> None:
    output = sample_editor_output()
    data = proposal_data(output)
    data["editorial_notes"] = ["   "]

    with pytest.raises(ValidationError):
        type(output.episode_proposal).model_validate_json(json.dumps(data))

    data["editorial_notes"] = ["x" * 201]
    with pytest.raises(ValidationError):
        type(output.episode_proposal).model_validate_json(json.dumps(data))

    data["editorial_notes"] = [f"note {index}" for index in range(21)]
    with pytest.raises(ValidationError):
        type(output.episode_proposal).model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    "transition",
    ["continuation", "contrast", "comic_relief", "custom:quiet-reset"],
)
def test_episode_flow_accepts_frozen_transition_vocabulary(transition: str) -> None:
    output = sample_editor_output()
    data = proposal_data(output)
    data["episode_flow"][0]["expected_transition_type"] = transition  # type: ignore[index]

    validated = type(output.episode_proposal).model_validate_json(json.dumps(data))

    assert validated.episode_flow[0].expected_transition_type == transition


def test_episode_flow_rejects_invalid_custom_transition() -> None:
    output = sample_editor_output()
    data = proposal_data(output)
    data["episode_flow"][0]["expected_transition_type"] = "custom:Too Broad"  # type: ignore[index]

    with pytest.raises(ValidationError, match="transition"):
        type(output.episode_proposal).model_validate_json(json.dumps(data))


def test_editorial_confidence_is_not_a_scout_score_or_alias() -> None:
    output = sample_editor_output()
    data = proposal_data(output)
    story = data["selected_stories"][0]  # type: ignore[index]
    story["editorial_confidence"] = 101
    with pytest.raises(ValidationError):
        type(output.episode_proposal).model_validate_json(json.dumps(data))

    story["editorial_confidence"] = 90
    story["selection_confidence"] = 90
    with pytest.raises(ValidationError, match="Extra inputs"):
        type(output.episode_proposal).model_validate_json(json.dumps(data))


def test_runtime_must_equal_selected_treatment_lengths() -> None:
    output = sample_editor_output()
    data = proposal_data(output)
    data["estimated_total_runtime"]["value"] = 181  # type: ignore[index]

    with pytest.raises(ValidationError, match="estimated runtime"):
        type(output.episode_proposal).model_validate_json(json.dumps(data))


def test_backup_replacement_must_reference_selected_story() -> None:
    output = sample_editor_output()
    data = proposal_data(output)
    story = dict(data["selected_stories"][0])  # type: ignore[index]
    story.pop("episode_role")
    story.pop("transition_reason")
    story["position"] = 1
    story["event_id"] = 77
    story["replacement_for"] = 999
    data["backup_stories"] = [story]
    summary = data["rejection_summary"]  # type: ignore[assignment]
    summary["total_candidates"] = 2
    summary["backups"] = 1

    with pytest.raises(ValidationError, match="replacement_for"):
        type(output.episode_proposal).model_validate_json(json.dumps(data))


def test_scout_identity_is_stable_and_order_independent_for_object_keys() -> None:
    source = sample_scout_input()
    reversed_data = dict(reversed(source.model_dump(mode="json").items()))

    assert scout_input_identity(source) == scout_input_identity(reversed_data)
    verify_scout_input_identity(source)


def test_scout_identity_detects_tampering() -> None:
    source = sample_scout_input()
    tampered_event = source.ranked_events[0].model_copy(
        update={"canonical_title": "Titlu schimbat"}
    )
    tampered = source.model_copy(update={"ranked_events": (tampered_event,)})

    with pytest.raises(ValueError, match="identity"):
        verify_scout_input_identity(tampered)


def test_deterministic_only_scout_input_is_supported() -> None:
    source = sample_scout_input()
    event = source.ranked_events[0]
    deterministic_event = event.model_copy(
        update={
            "ai_editorial_score": None,
            "score_basis": "deterministic_only",
        }
    )
    data = source.model_dump(mode="python")
    data["ranking_parameters"]["ai_enabled"] = False
    data["ranked_events"] = (deterministic_event,)
    validated = assign_scout_input_identity(data)

    assert validated.ranked_events[0].ai_editorial_score is None
    assert validated.ranking_parameters.ai_enabled is False


def test_editor_output_cross_validation_preserves_inherited_scores() -> None:
    source = sample_scout_input()
    output = sample_editor_output(source)
    validate_editor_output_against_input(output, source)
    assert output.episode_proposal is not None
    proposal = output.episode_proposal
    story = proposal.selected_stories[0]
    changed_scores = story.inherited_scout_scores.model_copy(
        update={"final_score": 99.0}
    )
    changed_story = story.model_copy(update={"inherited_scout_scores": changed_scores})
    changed_proposal = proposal.model_copy(
        update={"selected_stories": (changed_story,)}
    )
    changed_output = output.model_copy(update={"episode_proposal": changed_proposal})

    with pytest.raises(ValueError, match="inherited Scout scores"):
        validate_editor_output_against_input(changed_output, source)


def test_editor_output_cross_validates_profile_and_episode_context() -> None:
    source = sample_scout_input()
    output = sample_editor_output(source)
    profile = sample_selection_profile()
    context = sample_episode_context()

    validate_editor_output_against_input(
        output,
        source,
        selection_profile=profile,
        episode_context=context,
    )

    excluded_data = context.model_dump(mode="json")
    excluded_data["excluded_event_ids"] = [44]
    excluded_context = EpisodeContextV1.model_validate_json(json.dumps(excluded_data))
    with pytest.raises(ValueError, match="excluded events"):
        validate_editor_output_against_input(
            output, source, selection_profile=profile, episode_context=excluded_context
        )


def test_partial_success_sample_is_distinct_and_valid() -> None:
    output = sample_editor_partial_output()

    assert output.status == "partial_success"
    assert output.episode_proposal is not None
    assert output.episode_proposal.warnings[0].recoverable is True


def test_safe_loader_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text(
        '{"contract_version":"episode-context-v1","x":1,"x":2}', encoding="utf-8"
    )

    with pytest.raises(ContractFileError, match="duplicate JSON key"):
        load_contract(path)


def test_safe_loader_rejects_non_utf8_and_unknown_versions(tmp_path: Path) -> None:
    binary = tmp_path / "binary.json"
    binary.write_bytes(b"\xff\xfe")
    with pytest.raises(ContractFileError, match="UTF-8"):
        load_contract(binary)

    unknown = tmp_path / "unknown.json"
    unknown.write_text('{"contract_version":"scout-editor-input-v2"}', encoding="utf-8")
    with pytest.raises(ContractFileError, match="unsupported contract_version"):
        load_contract(unknown)


def test_safe_io_rejects_remote_and_windows_device_paths() -> None:
    with pytest.raises(ContractFileError, match="local filesystem"):
        load_contract(Path("https://example.com/contract.json"))
    with pytest.raises(ContractFileError, match="device paths"):
        write_contract(sample_episode_context(), Path("NUL.json"))


def test_utf8_canonical_export_is_atomic_and_readable(tmp_path: Path) -> None:
    output = tmp_path / "nested" / "contract.json"
    write_contract(sample_episode_context(), output)

    assert "român" in output.read_text(encoding="utf-8")
    assert not list(output.parent.glob("*.tmp"))


def test_committed_schema_generation_is_deterministic(tmp_path: Path) -> None:
    generated = write_json_schemas(tmp_path)

    assert len(generated) == len(SCHEMA_MODELS) == 4
    for path in generated:
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema["additionalProperties"] is False
        assert path.read_bytes() == (Path("contracts/schemas") / path.name).read_bytes()


def test_cli_contract_validation_export_and_artifact_generation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    samples = write_sample_contracts(tmp_path / "inputs")
    scout, _, profile, context, editor, _ = samples

    assert main(["validate-contract", str(scout)]) == 0
    assert (
        main(
            [
                "validate-contract",
                str(editor),
                "--source-input",
                str(scout),
                "--selection-profile",
                str(profile),
                "--episode-context",
                str(context),
            ]
        )
        == 0
    )
    exported = tmp_path / "exported.json"
    assert main(["export-contract", str(scout), "--output", str(exported)]) == 0
    artifacts = tmp_path / "artifacts"
    assert (
        main(["generate-contract-artifacts", "--output-directory", str(artifacts)]) == 0
    )

    output = capsys.readouterr().out
    assert "Contract valid: scout-editor-input-v1" in output
    assert "Source linkage: valid" in output
    assert "Selection profile linkage: valid" in output
    assert "Episode context linkage: valid" in output
    assert exported.read_bytes() == scout.read_bytes()
    assert len(list((artifacts / "schemas").glob("*.json"))) == 4
    assert len(list((artifacts / "samples").glob("*.json"))) == 6


def test_contract_package_has_no_forbidden_runtime_imports() -> None:
    contract_files = Path("src/pastila_scout/contracts").glob("*.py")
    contents = "\n".join(path.read_text(encoding="utf-8") for path in contract_files)

    assert "pastila_scout.database" not in contents
    assert "pastila_scout.ai" not in contents
    assert "pastila_scout.core.event_ranking" not in contents
