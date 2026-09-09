import hashlib
import json
import shutil
from pathlib import Path

import pytest

import pastila_scout.production_core_semantic_authority_v2 as semantic_v2
from pastila_scout.production_core_semantic_authority_v2 import (
    Unicode16SentenceAuthority,
    build_candidate_prompt_v2,
    unicode_scalar_count,
    validate_commentary,
    validate_factual_shape,
    validate_response_v2,
    validate_source_span_order,
)

ROOT = Path(".pastila-runtime/production-core-unicode-16-uax29-authority-v1")
TEST_SHA = "0aef84034ee1789eb71021454fac384e83080b05922272d63cf297f4bf08150e"


@pytest.fixture(scope="module")
def authority():
    return Unicode16SentenceAuthority.load(ROOT)


def test_authority_objects_are_single_read_snapshots(tmp_path, monkeypatch):
    copied = tmp_path / "authority"
    shutil.copytree(ROOT, copied)
    original_open = semantic_v2.os.open
    opens = []
    blocked_replacements = []

    def replacing_open(path, flags):
        descriptor = original_open(path, flags)
        opens.append(Path(path))
        replacement = Path(path).with_suffix(".substituted")
        replacement.write_bytes(b"substituted after descriptor snapshot")
        try:
            replacement.replace(path)
        except PermissionError:
            blocked_replacements.append(Path(path))
        return descriptor

    monkeypatch.setattr(semantic_v2.os, "open", replacing_open)
    loaded = Unicode16SentenceAuthority.load(copied)
    assert loaded.boundaries("One. Two.") == (0, 5, 9)
    assert len(opens) == 3
    assert len(blocked_replacements) in {0, 3}


def test_all_512_official_cases(authority):
    checked = 0
    for raw in (ROOT / "objects" / "sha256" / TEST_SHA).read_text("utf-8").splitlines():
        tokens = raw.split("#", 1)[0].strip().split()
        if not tokens:
            continue
        expected = []
        position = 0
        chars = []
        for token in tokens:
            if token == "÷":
                expected.append(position)
            elif token != "×":
                chars.append(chr(int(token, 16)))
                position += 1
        assert authority.boundaries("".join(chars)) == tuple(expected), raw
        checked += 1
    assert checked == 512


@pytest.mark.parametrize(
    ("text", "count"),
    [
        ("One. Two? Three!", 3),
        ("One. Two? Three! Four.", 4),
        ("One. Two? Three! Four. Five.", 5),
    ],
)
def test_commentary_allowed(authority, text, count):
    result = validate_commentary(text, authority)
    assert result == {
        "qsu_count": count,
        "target_conformant": count <= 3,
        "target_has_qualification_effect": False,
    }


def test_pattern_white_space_is_exact_and_empty_answers_fail(authority):
    assert authority.count_qsu(" \t\u200e\u2029") == 0
    assert authority.count_qsu("\u00a0") == 1
    with pytest.raises(ValueError, match="hard semantic ceiling"):
        validate_commentary(" \t\u200e", authority)


def test_six_fails(authority):
    with pytest.raises(ValueError):
        validate_commentary("One. Two. Three. Four. Five. Six.", authority)


def test_unicode_unit():
    assert unicode_scalar_count("é") == 1
    with pytest.raises(ValueError):
        unicode_scalar_count("e\u0301")


def test_source_order():
    validate_source_span_order(["src:2", "src:10"], ["src:2", "src:10", "src:1"])
    with pytest.raises(ValueError):
        validate_source_span_order(["src:10", "src:2"], ["src:2", "src:10"])


def test_factual_shape(authority):
    claims = [{"claim_index": 1}, {"claim_index": 2}]
    validate_factual_shape(
        shape="MATERIAL_PROPOSITIONS",
        text="One fact and another.",
        expected_material_propositions=2,
        claim_bindings=claims,
        sentence_authority=authority,
    )
    with pytest.raises(ValueError):
        validate_factual_shape(
            shape="CALLER_SELECTED",
            text="One.",
            expected_material_propositions=2,
            claim_bindings=claims,
            sentence_authority=authority,
        )
    with pytest.raises(ValueError, match="material-proposition authority"):
        validate_factual_shape(
            shape="MATERIAL_PROPOSITIONS",
            text="One.",
            expected_material_propositions=1,
            claim_bindings=[{"claim_index": 1}],
            sentence_authority=authority,
        )
    validate_factual_shape(
        shape="QUALIFICATION_SENTENCE_UNITS",
        text="One.",
        expected_material_propositions=1,
        claim_bindings=[{"claim_index": 1}],
        sentence_authority=authority,
    )


def _commentary(case, text):
    return json.dumps(
        {
            "schema": "pastila-core-v2-structured-qualification-response",
            "schema_version": 2,
            "case_id": case["case_id"],
            "request_identity": case["request_identity"],
            "output_type": "COMMENTARY",
            "outcome": "ANSWER",
            "text": text,
            "claim_bindings": [],
            "abstention_code": None,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()


def test_complete_validator_allows_five_and_rejects_six(authority):
    case = {
        "case_id": "case-1",
        "request_identity": "sha256:" + "a" * 64,
        "output_type": "COMMENTARY",
        "request": "Comment.",
        "authority_spans": [],
    }
    validate_response_v2(
        _commentary(case, "One. Two. Three. Four. Five."), case, authority
    )
    with pytest.raises(ValueError, match="hard semantic ceiling"):
        validate_response_v2(
            _commentary(case, "One. Two. Three. Four. Five. Six."), case, authority
        )


def test_candidate_visible_authority_is_complete_and_distinguishes_policy_classes():
    case = {
        "case_id": "case-1",
        "request_identity": "sha256:" + "a" * 64,
        "output_type": "COMMENTARY",
        "required_factual_shape": None,
        "expected_material_proposition_count": None,
        "required_commentary_components": ["contrast", "punchline"],
        "request": "Comment.",
        "authority_spans": [],
    }
    prompt = build_candidate_prompt_v2(case)
    required = [
        "diagnostic-only editorial target",
        "4-5 are permitted",
        "more than 5 fails",
        "1000 NFC Unicode scalar values",
        "Unicode 16.0.0 UAX #29 C3-1",
        "required only when INPUT explicitly requests",
        "6268 UTF-8 bytes",
        "6268 tokenizer tokens",
        "no score or failure effect",
        "^[a-z0-9][a-z0-9._-]{0,127}$",
        "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$",
        '"required_commentary_components":["contrast","punchline"]',
    ]
    assert all(item in prompt for item in required)


def test_generated_authorities_self_bind_and_preserve_ordinal8_v1():
    artifacts = Path("docs/artifacts")
    names = [
        "production-core-unicode-16-uax29-authority-v1.json",
        "core-v2-semantic-output-contract-v2.json",
        "core-v2-structured-qualification-response-v2.json",
        "production-core-qualification-corpus-v2.json",
        "production-core-qualification-assertions-v2.json",
        "production-core-qualification-rubric-v2.json",
        "production-core-execution-profile-v2.json",
        "production-core-model-qualification-framework-v2.json",
    ]
    identity_keys = [
        "authority_identity",
        "contract_identity",
        "contract_identity",
        "corpus_identity",
        "assertion_manifest_identity",
        "rubric_identity",
        "profile_identity",
        "framework_identity",
    ]
    for name, key in zip(names, identity_keys, strict=True):
        value = json.loads((artifacts / name).read_bytes())
        stored = value.pop(key)
        assert (
            stored
            == hashlib.sha256(
                json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
            ).hexdigest()
        )
    old = json.loads(
        (artifacts / "production-core-qualification-corpus-v1.json").read_bytes()
    )
    new = json.loads(
        (artifacts / "production-core-qualification-corpus-v2.json").read_bytes()
    )
    assert new["historical_corpus_identity"] == old["corpus_identity"] and new[
        "case_ids"
    ] == [x["case_id"] for x in old["cases"]]
    assertions = json.loads(
        (artifacts / "production-core-qualification-assertions-v2.json").read_bytes()
    )["assertions"]
    eos = [x for x in assertions if x["case_id"].startswith("pcq-eos-")]
    assert len(eos) == 20
    assert all(
        "MAXIMUM_5_QSU" in x["expected_semantics"]["completion_requirements"]
        and "maximum three sentences"
        not in x["expected_semantics"]["completion_requirements"]
        for x in eos
    )
    assert all(
        "EXPLICIT_COMPLETE_PUNCHLINE"
        not in x["expected_semantics"]["completion_requirements"]
        for x in eos[:10]
    )
    assert all(
        "EXPLICIT_COMPLETE_PUNCHLINE"
        in x["expected_semantics"]["completion_requirements"]
        for x in eos[10:]
    )
