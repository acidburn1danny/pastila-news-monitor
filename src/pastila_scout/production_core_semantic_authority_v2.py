"""Prospective Core V2 semantic authority; historical V1 remains untouched."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

UNICODE_AUTHORITY_IDENTITY = (
    "baa7f72966196d6eada227d094033cff647eef2b35366f98876aa17f392aeebf"
)
SENTENCE_PROPERTY_SHA256 = (
    "20aab5eca3842c7a27cc6756d74488a4a5f744c8dca2948ec1128f26a60d1f79"
)
SENTENCE_TEST_SHA256 = (
    "0aef84034ee1789eb71021454fac384e83080b05922272d63cf297f4bf08150e"
)
UAX29_SHA256 = "4579c185bd45feac761de590d874aca71788e339b35179318a4c43412fd4f9e4"
COMMENTARY_TARGET_QSU, COMMENTARY_MAX_QSU = 3, 5
COMMENTARY_MAX_SCALARS, FACTUAL_MAX_SCALARS = 1000, 650
TOP_FIELDS = (
    "schema",
    "schema_version",
    "case_id",
    "request_identity",
    "output_type",
    "outcome",
    "text",
    "claim_bindings",
    "abstention_code",
)
ABSTENTION_CODES = {
    "INSUFFICIENT_AUTHORITY",
    "CONFLICTING_AUTHORITY",
    "AMBIGUOUS_SCOPE",
    "UNRESOLVED_REFERENCE",
    "INSTRUCTION_AUTHORITY_CONFLICT",
    "CANNOT_SATISFY_OUTPUT_CONTRACT",
    "SAFETY_ENVELOPE_EXCEEDED",
}
CASE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
REQUEST_IDENTITY = re.compile(r"^sha256:[0-9a-f]{64}$")
SOURCE_SPAN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SHA256_SPAN_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
PATTERN_WHITE_SPACE = frozenset(
    "\u0009\u000a\u000b\u000c\u000d\u0020\u0085\u200e\u200f\u2028\u2029"
)
SYSTEM_INSTRUCTION_V2 = (
    "Return exactly one compact NFC UTF-8 JSON object followed immediately by EOF, with keys exactly in this order: schema,schema_version,case_id,request_identity,output_type,outcome,text,claim_bindings,abstention_code. "
    "schema='pastila-core-v2-structured-qualification-response' and schema_version=2; case_id, request_identity, output_type, required_factual_shape, expected_material_proposition_count, required_commentary_components, request, and ordered authority_spans are supplied in INPUT and must not be substituted. case_id matches ^[a-z0-9][a-z0-9._-]{0,127}$; request_identity matches ^sha256:[0-9a-f]{64}$. Use only FACTUAL or COMMENTARY and ANSWER or ABSTAIN. "
    "For COMMENTARY+ANSWER: one non-empty block, no factual claims, claim_bindings=[], abstention_code=null; 3 QUALIFICATION_SENTENCE_UNITs is a diagnostic-only editorial target with no score or failure effect, 4-5 are permitted, and more than 5 fails; 1000 NFC Unicode scalar values is a separate hard maximum. Setup, development, observation, contrast, and punchline are permitted and become required only when INPUT explicitly requests them. "
    "A QUALIFICATION_SENTENCE_UNIT is a non-empty segment from unmodified Unicode 16.0.0 UAX #29 C3-1 default sentence boundaries after NFC normalization; Pattern_White_Space is ignored only at segment edges; EOF terminates the final non-empty segment; no locale, tailoring, alternate Unicode version, or abbreviation list is permitted. "
    "For FACTUAL+ANSWER: one non-empty block, no bullets/headings, at most 650 NFC Unicode scalar values, zero unsupported/changed facts, and every material proposition source-bound. INPUT required_factual_shape is exactly MATERIAL_PROPOSITIONS (2-3 material propositions) or QUALIFICATION_SENTENCE_UNITS (1-2 QSU), is not caller-selectable, and must be obeyed. A material proposition is the smallest independently truth-evaluable factual assertion whose truth, qualification, or authority binding can differ independently; qualifiers remain with what they qualify; stylistic connective or repetition adds none. "
    "claim_bindings contains 1-3 objects ordered by material-proposition occurrence with keys claim_index,source_span_ids; indexes are integers contiguous from 1. Each source_span_ids has 1-8 unique opaque ASCII IDs and at most 24 unique references globally, in strictly increasing order of INPUT authority_spans. Every ID is 1-128 characters and matches ^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$; IDs are case-sensitive and any sha256: ID must match ^sha256:[0-9a-f]{64}$. "
    "For ABSTAIN: text=null, claim_bindings=[], and abstention_code is exactly one of INSUFFICIENT_AUTHORITY,CONFLICTING_AUTHORITY,AMBIGUOUS_SCOPE,UNRESOLVED_REFERENCE,INSTRUCTION_AUTHORITY_CONFLICT,CANNOT_SATISFY_OUTPUT_CONTRACT,SAFETY_ENVELOPE_EXCEEDED. For ANSWER abstention_code=null. "
    "No extra/missing/duplicate fields, BOM, external whitespace, final newline, Markdown, fences, second object, bool/float/NaN/Infinity integer substitution, coercion, repair, truncation, retry, redraw, or continuation. Technical safety limits are separate: 6268 UTF-8 bytes and 6268 tokenizer tokens; overflow fails closed without changing semantic quality rules."
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot_authority_object(root: Path, path: Path, expected: str) -> bytes:
    if path.is_symlink() or not path.resolve(strict=True).is_relative_to(root):
        raise ValueError("Unicode authority closure mismatch")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError("Unicode authority object is not regular")
        chunks = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        snapshot = b"".join(chunks)
    finally:
        os.close(descriptor)
    if hashlib.sha256(snapshot).hexdigest() != expected:
        raise ValueError("Unicode authority closure mismatch")
    return snapshot


@dataclass(frozen=True)
class Unicode16SentenceAuthority:
    properties: tuple[str, ...]

    @classmethod
    def load(cls, supplied_root: Path) -> Unicode16SentenceAuthority:
        if supplied_root.is_symlink():
            raise ValueError("authority root symlink prohibited")
        root = supplied_root.resolve(strict=True)
        objects = root / "objects" / "sha256"
        paths = [
            objects / value
            for value in (SENTENCE_PROPERTY_SHA256, SENTENCE_TEST_SHA256, UAX29_SHA256)
        ]
        snapshots = tuple(
            _snapshot_authority_object(root, path, expected)
            for expected, path in zip(
                (SENTENCE_PROPERTY_SHA256, SENTENCE_TEST_SHA256, UAX29_SHA256),
                paths,
                strict=True,
            )
        )
        try:
            prop, tests, uax = (snapshot.decode("utf-8") for snapshot in snapshots)
        except UnicodeDecodeError as exc:
            raise ValueError("Unicode authority encoding mismatch") from exc
        if (
            not prop.startswith("# SentenceBreakProperty-16.0.0.txt\n")
            or not tests.startswith("# SentenceBreakTest-16.0.0.txt\n")
            or "Unicode 16.0.0" not in uax
            or "Revision 45" not in uax
        ):
            raise ValueError("Unicode authority version mismatch")
        values = ["Other"] * 0x110000
        occupied = bytearray(0x110000)
        rows = 0
        allowed = {
            "CR",
            "LF",
            "Extend",
            "Sep",
            "Format",
            "Sp",
            "Lower",
            "Upper",
            "OLetter",
            "Numeric",
            "ATerm",
            "STerm",
            "Close",
            "SContinue",
        }
        for raw in prop.splitlines():
            data = raw.split("#", 1)[0].strip()
            if not data:
                continue
            match = re.fullmatch(
                r"([0-9A-F]{4,6})(?:\.\.([0-9A-F]{4,6}))?\s*;\s*([A-Za-z]+)", data
            )
            if match is None or match.group(3) not in allowed:
                raise ValueError("malformed property authority")
            start, end = (
                int(match.group(1), 16),
                int(match.group(2) or match.group(1), 16),
            )
            if end > 0x10FFFF or any(occupied[start : end + 1]):
                raise ValueError("property overlap")
            occupied[start : end + 1] = b"\1" * (end - start + 1)
            values[start : end + 1] = [match.group(3)] * (end - start + 1)
            rows += 1
        if rows != 2898:
            raise ValueError("property cardinality mismatch")
        return cls(tuple(values))

    def boundaries(self, text: str) -> tuple[int, ...]:
        if any(0xD800 <= ord(c) <= 0xDFFF for c in text):
            raise ValueError("UAX input must contain Unicode scalar values")
        p = [self.properties[ord(c)] for c in text]
        para = {"Sep", "CR", "LF"}
        sat = {"STerm", "ATerm"}
        ignored = {"Extend", "Format"}
        effective = p[:]
        sig = []
        previous_significant = None
        for j, x in enumerate(p):
            if x in ignored and (
                previous_significant is None or effective[previous_significant] in para
            ):
                effective[j] = "Other"
                sig.append(j)
                previous_significant = j
            elif x not in ignored:
                sig.append(j)
                previous_significant = j

        def sides(i: int):
            return (
                [effective[j] for j in sig if j < i],
                [effective[j] for j in sig if j >= i],
            )

        def anchor(left: list[str], spaces: bool = True):
            k = len(left) - 1
            if spaces:
                while k >= 0 and left[k] == "Sp":
                    k -= 1
            while k >= 0 and left[k] == "Close":
                k -= 1
            return k

        out = [0]
        for i in range(1, len(text)):
            if p[i - 1] == "CR" and p[i] == "LF":
                continue
            if p[i - 1] in para:
                out.append(i)
                continue
            if p[i] in ignored:
                continue
            left, right = sides(i)
            if not left or not right:
                continue
            if left[-1] == "ATerm" and right[0] == "Numeric":
                continue
            if (
                len(left) >= 2
                and left[-1] == "ATerm"
                and left[-2] in {"Upper", "Lower"}
                and right[0] == "Upper"
            ):
                continue
            k = anchor(left)
            if k >= 0 and left[k] == "ATerm":
                found = False
                for x in right:
                    if x == "Lower":
                        found = True
                        break
                    if x in {"OLetter", "Upper", "Lower", *para, *sat}:
                        break
                if found:
                    continue
            if k >= 0 and left[k] in sat and right[0] in {"SContinue", *sat}:
                continue
            k9 = anchor(left, False)
            if k9 >= 0 and left[k9] in sat and right[0] in {"Close", "Sp", *para}:
                continue
            if k >= 0 and left[k] in sat and right[0] in {"Sp", *para}:
                continue
            candidate = left[:]
            if candidate and candidate[-1] in para:
                candidate.pop()
            k11 = anchor(candidate)
            if k11 >= 0 and candidate[k11] in sat:
                out.append(i)
        out.append(len(text))
        return tuple(dict.fromkeys(out))

    def count_qsu(self, text: str) -> int:
        normalized = unicodedata.normalize("NFC", text)
        b = self.boundaries(normalized)
        return sum(
            any(character not in PATTERN_WHITE_SPACE for character in normalized[a:z])
            for a, z in pairwise(b)
        )


def unicode_scalar_count(text: str) -> int:
    if unicodedata.normalize("NFC", text) != text or any(
        0xD800 <= ord(c) <= 0xDFFF for c in text
    ):
        raise ValueError("text must be NFC scalar text")
    return len(text)


def validate_commentary(
    text: str, authority: Unicode16SentenceAuthority
) -> dict[str, object]:
    count = authority.count_qsu(text)
    if (
        not any(character not in PATTERN_WHITE_SPACE for character in text)
        or unicode_scalar_count(text) > COMMENTARY_MAX_SCALARS
        or count < 1
        or count > COMMENTARY_MAX_QSU
    ):
        raise ValueError("commentary hard semantic ceiling exceeded")
    return {
        "qsu_count": count,
        "target_conformant": count <= COMMENTARY_TARGET_QSU,
        "target_has_qualification_effect": False,
    }


def validate_source_span_order(
    source_ids: Sequence[str], authority_ids: Sequence[str]
) -> None:
    if len(authority_ids) != len(set(authority_ids)):
        raise ValueError("duplicate request authority ID")
    positions = {x: i for i, x in enumerate(authority_ids)}
    if (
        not 1 <= len(source_ids) <= 8
        or len(source_ids) != len(set(source_ids))
        or any(x not in positions for x in source_ids)
        or any(SOURCE_SPAN_ID.fullmatch(x) is None for x in source_ids)
        or any(
            x.startswith("sha256:") and SHA256_SPAN_ID.fullmatch(x) is None
            for x in source_ids
        )
    ):
        raise ValueError("invalid source-span binding")
    indices = [positions[x] for x in source_ids]
    if indices != sorted(indices):
        raise ValueError("source-span order mismatch")


def validate_factual_shape(
    *,
    shape: str,
    text: str,
    expected_material_propositions: int,
    claim_bindings: Sequence[Mapping[str, object]],
    sentence_authority: Unicode16SentenceAuthority,
) -> None:
    if shape not in {"MATERIAL_PROPOSITIONS", "QUALIFICATION_SENTENCE_UNITS"}:
        raise ValueError("required_factual_shape invalid")
    if not any(character not in PATTERN_WHITE_SPACE for character in text) or (
        unicode_scalar_count(text) > FACTUAL_MAX_SCALARS
    ):
        raise ValueError("factual semantic structure invalid")
    if (
        shape == "MATERIAL_PROPOSITIONS"
        and not 2 <= expected_material_propositions <= 3
    ):
        raise ValueError("material-proposition authority invalid")
    if not 1 <= expected_material_propositions <= 3:
        raise ValueError("expected proposition authority invalid")
    if [x.get("claim_index") for x in claim_bindings] != list(
        range(1, expected_material_propositions + 1)
    ):
        raise ValueError("material-proposition claim mapping invalid")
    if (
        shape == "QUALIFICATION_SENTENCE_UNITS"
        and not 1 <= sentence_authority.count_qsu(text) <= 2
    ):
        raise ValueError("factual QSU shape invalid")


def build_candidate_prompt_v2(case: Mapping[str, object]) -> str:
    exact = {
        "case_id": case["case_id"],
        "request_identity": case["request_identity"],
        "output_type": case["output_type"],
        "required_factual_shape": case.get("required_factual_shape"),
        "expected_material_proposition_count": case.get(
            "expected_material_proposition_count"
        ),
        "required_commentary_components": case.get(
            "required_commentary_components", []
        ),
        "request": case["request"],
        "authority_spans": case["authority_spans"],
    }
    return (
        SYSTEM_INSTRUCTION_V2
        + "\nINPUT="
        + json.dumps(exact, ensure_ascii=False, separators=(",", ":"))
    )


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def validate_response_v2(
    raw: bytes,
    case: Mapping[str, object],
    authority: Unicode16SentenceAuthority,
) -> dict[str, object]:
    if len(raw) > 6268 or raw.startswith(b"\xef\xbb\xbf") or raw.endswith(b"\n"):
        raise ValueError("technical framing or byte ceiling")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("constant")),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("invalid JSON") from exc
    if not isinstance(value, dict) or tuple(value) != TOP_FIELDS:
        raise ValueError("top-level schema/order")
    if (
        value["schema"] != "pastila-core-v2-structured-qualification-response"
        or type(value["schema_version"]) is not int
        or value["schema_version"] != 2
    ):
        raise ValueError("schema authority")
    if (
        not isinstance(value["case_id"], str)
        or CASE_ID.fullmatch(value["case_id"]) is None
    ):
        raise ValueError("case_id grammar")
    if (
        not isinstance(value["request_identity"], str)
        or REQUEST_IDENTITY.fullmatch(value["request_identity"]) is None
    ):
        raise ValueError("request identity grammar")
    if (
        value["case_id"] != case["case_id"]
        or value["request_identity"] != case["request_identity"]
        or value["output_type"] != case["output_type"]
    ):
        raise ValueError("request binding")
    if value["output_type"] not in {"FACTUAL", "COMMENTARY"} or value[
        "outcome"
    ] not in {"ANSWER", "ABSTAIN"}:
        raise ValueError("branch enum")
    claims = value["claim_bindings"]
    if not isinstance(claims, list) or len(claims) > 3:
        raise ValueError("claims")
    authority_ids = [span["span_id"] for span in case["authority_spans"]]
    all_ids = []
    for index, claim in enumerate(claims, 1):
        if (
            not isinstance(claim, dict)
            or tuple(claim) != ("claim_index", "source_span_ids")
            or type(claim["claim_index"]) is not int
            or claim["claim_index"] != index
        ):
            raise ValueError("claim schema/order")
        ids = claim["source_span_ids"]
        if not isinstance(ids, list) or any(not isinstance(x, str) for x in ids):
            raise ValueError("source IDs")
        validate_source_span_order(ids, authority_ids)
        all_ids.extend(ids)
    if len(all_ids) > 24 or len(all_ids) != len(set(all_ids)):
        raise ValueError("aggregate source IDs")
    if value["outcome"] == "ABSTAIN":
        if (
            value["text"] is not None
            or claims
            or value["abstention_code"] not in ABSTENTION_CODES
        ):
            raise ValueError("abstain invariant")
    else:
        text = value["text"]
        if (
            not isinstance(text, str)
            or not text
            or value["abstention_code"] is not None
        ):
            raise ValueError("answer invariant")
        if value["output_type"] == "COMMENTARY":
            if claims:
                raise ValueError("commentary claims")
            validate_commentary(text, authority)
        else:
            expected_material_propositions = case.get(
                "expected_material_proposition_count"
            )
            if type(expected_material_propositions) is not int:
                raise ValueError("frozen proposition authority required")
            validate_factual_shape(
                shape=str(case.get("required_factual_shape")),
                text=text,
                expected_material_propositions=expected_material_propositions,
                claim_bindings=claims,
                sentence_authority=authority,
            )
    normalized = _normalize(value)
    encoded = json.dumps(
        normalized, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode()
    if encoded != raw:
        raise ValueError("noncanonical or trailing output")
    return value


def _normalize(value: object) -> object:
    if isinstance(value, str):
        if any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise ValueError("invalid Unicode")
        return unicodedata.normalize("NFC", value)
    if value is None or type(value) is int:
        return value
    if isinstance(value, list):
        return [_normalize(x) for x in value]
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    raise ValueError("noncontractual JSON type")
