"""Local contract checks for the clean four-scenario Part 5 restart."""

from __future__ import annotations

from scripts.validate_openai_controlled_revision_e2e import (
    OPT_IN,
    PART5_RESTART_OPT_IN,
    PART5C_OPT_IN,
    PART5D_OPT_IN,
    PART5E_OPT_IN,
    PART5F_OPT_IN,
    PART5G_OPT_IN,
    PART5H_OPT_IN,
    PART5K_OPT_IN,
    SCENARIOS,
    acceptance_specification,
    build_invocation,
    configuration,
    main,
)


def test_clean_restart_scenarios_and_invocations_are_unique() -> None:
    assert tuple(item.identifier for item in SCENARIOS) == (
        "E2E-01",
        "E2E-02",
        "E2E-03",
        "E2E-04",
    )
    assert len({item.source.episode_id for item in SCENARIOS}) == 4
    invocations = tuple(
        build_invocation(scenario, index) for index, scenario in enumerate(SCENARIOS, 1)
    )
    assert len({item.invocation_fingerprint for item in invocations}) == 4
    assert all(item.request.revision_targets for item in invocations)
    assert all(
        item.request.expected_output_contract.output_contract_fingerprint
        for item in invocations
    )


def test_scenario_component_identifiers_do_not_overlap() -> None:
    identifiers = [
        story.story_id for scenario in SCENARIOS for story in scenario.source.stories
    ]
    assert len(identifiers) == len(set(identifiers))


def test_substantial_rewrite_fixture_has_required_contract_coverage() -> None:
    scenario = SCENARIOS[1]
    specification = acceptance_specification(scenario)
    assert scenario.target_references == ("story:101",)
    assert scenario.substantial_rewrite
    assert len(specification.required_entities) >= 2
    assert specification.required_dates
    assert specification.required_times
    assert len(specification.required_numeric_values) >= 4
    targeted_source = scenario.source.stories[0].text.casefold()
    for value in (
        *specification.required_entities,
        *specification.required_dates,
        *specification.required_times,
        *specification.required_numeric_values,
    ):
        assert value.casefold() in targeted_source


def test_protected_structure_scenario_authorizes_only_a_subset() -> None:
    scenario = SCENARIOS[2]
    all_components = 2 + len(scenario.source.stories) + len(scenario.source.transitions)
    assert len(scenario.target_references) > 1
    assert len(scenario.target_references) < all_components
    assert "story:201" not in scenario.target_references
    assert "transition:201:202" not in scenario.target_references


def test_source_authority_predicates_are_applicable_only_to_e2e04() -> None:
    assert all(
        not acceptance_specification(item).source_authority_applicable
        for item in SCENARIOS[:3]
    )
    specification = acceptance_specification(SCENARIOS[3])
    assert specification.source_authority_applicable
    assert specification.embedded_instruction_markers
    assert specification.malicious_values


def test_runtime_policy_is_one_attempt_without_fallback() -> None:
    provider_configuration = configuration("synthetic-model")
    assert provider_configuration.retry_policy.maximum_attempts == 1
    assert provider_configuration.model_identifier == "synthetic-model"


def test_clean_restart_opt_in_is_distinct() -> None:
    assert (
        len(
            {
                OPT_IN,
                PART5C_OPT_IN,
                PART5D_OPT_IN,
                PART5E_OPT_IN,
                PART5F_OPT_IN,
                PART5G_OPT_IN,
                PART5H_OPT_IN,
                PART5K_OPT_IN,
                PART5_RESTART_OPT_IN,
            }
        )
        == 9
    )


def test_dry_run_legacy_part5_flag_does_not_trigger_restart(
    monkeypatch, capsys
) -> None:
    monkeypatch.setenv(OPT_IN, "1")
    monkeypatch.delenv(PART5_RESTART_OPT_IN, raising=False)
    for name in (
        PART5C_OPT_IN,
        PART5D_OPT_IN,
        PART5E_OPT_IN,
        PART5F_OPT_IN,
        PART5G_OPT_IN,
        PART5H_OPT_IN,
        PART5K_OPT_IN,
    ):
        monkeypatch.delenv(name, raising=False)
    assert main() == 0
    output = capsys.readouterr().out
    assert "Scenarios built: 4" in output
    assert "Unique valid invocations: YES" in output
    assert "Live requests: 0" in output
    assert "SDK requests: 0" in output
