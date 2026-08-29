import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generated_suffix_callback_v1 import RequestBoundGeneratedSuffixCallbackV1


def test_prompt_is_validated_once_and_only_generated_suffix_is_projected():
    observed = []
    callback = RequestBoundGeneratedSuffixCallbackV1(
        request_identity="request-a", prompt_token_ids=(10, 11, 12),
        project=lambda suffix: observed.append(tuple(suffix)) or (7,))
    callback.validate_prompt_once(request_identity="request-a", prompt_token_ids=(10, 11, 12))
    assert callback.project_generated_suffix(request_identity="request-a", generated_token_ids=()) == (7,)
    callback.project_generated_suffix(request_identity="request-a", generated_token_ids=(20,))
    assert observed == [(), (20,)]


@pytest.mark.parametrize("mutation", [(), (20, 22), (19, 21)])
def test_backtrack_prefix_mutation_and_stale_callback_fail_closed(mutation):
    callback = RequestBoundGeneratedSuffixCallbackV1(
        request_identity="request-a", prompt_token_ids=(10,), project=lambda suffix: suffix)
    callback.project_generated_suffix(request_identity="request-a", generated_token_ids=(20, 21))
    with pytest.raises(ValueError, match="NONINCREMENTAL_OR_MUTATED"):
        callback.project_generated_suffix(request_identity="request-a", generated_token_ids=mutation)
    callback.close()
    with pytest.raises(ValueError, match="STALE_CALLBACK"):
        callback.project_generated_suffix(request_identity="request-a", generated_token_ids=(20, 21, 22))


def test_prompt_substitution_cross_request_and_invalid_ids_fail_closed():
    callback = RequestBoundGeneratedSuffixCallbackV1(
        request_identity="request-a", prompt_token_ids=(10,), project=lambda suffix: suffix)
    with pytest.raises(ValueError, match="PROMPT_SUBSTITUTION"):
        callback.validate_prompt_once(request_identity="request-a", prompt_token_ids=(11,))
    with pytest.raises(ValueError, match="CROSS_REQUEST"):
        callback.project_generated_suffix(request_identity="request-b", generated_token_ids=())
    with pytest.raises(ValueError, match="TOKENS_INVALID"):
        callback.project_generated_suffix(request_identity="request-a", generated_token_ids=(-1,))
