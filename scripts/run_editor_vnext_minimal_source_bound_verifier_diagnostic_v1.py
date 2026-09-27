"""Fixture-only diagnostic for the minimal VNext source-bound verifier."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

VERDICTS = {"PASS_PROVEN", "FAIL_PROVEN", "UNPROVEN"}
QUALIFICATION_GROUPS = (
    ("ar fi", "s-ar fi", "potrivit", "conform"),
    ("estimat", "estimare", "aproximativ", "circa"),
    ("posibil", "posibilitate", "propus", "propunere"),
)
STATUS_GROUPS = (
    ("provizoriu", "preliminar"),
    ("anchetat", "investigat", "cercetat"),
    ("trimis în judecată", "deferit justiției"),
    ("condamnat definitiv", "hotărâre definitivă"),
)
FINALITY = ("confirmat", "definitiv", "stabilit", "dovedit")
ENTITY_STOP = {"Sursa", "Sursele", "Potrivit", "Conform", "După", "În", "La", "Un", "O"}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def norm(text: str) -> str:
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c)).split())


NUMBER = re.compile(r"(?<![\w])\d{1,3}(?:[ .]\d{3})+(?:,\d+)?|(?<![\w])\d+(?:,\d+)?(?:\s*%)?(?![\w])")


def canonical_numbers(text: str) -> set[str]:
    values: set[str] = set()
    for match in NUMBER.finditer(text):
        raw = match.group(0).strip()
        percent = raw.endswith("%")
        raw = raw.removesuffix("%").strip().replace(" ", "")
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", raw):
            raw = raw.replace(".", "")
        raw = raw.replace(",", ".")
        whole, dot, fraction = raw.partition(".")
        value = str(int(whole)) + (dot + fraction.rstrip("0") if dot and fraction.rstrip("0") else "")
        values.add(("percent:" if percent else "number:") + value)
    return values


def source_entities(text: str) -> set[str]:
    candidates = set()
    for phrase in re.findall(r"\b(?:[A-ZĂÂÎȘȚ][\wĂÂÎȘȚăâîșț-]+)(?:\s+[A-ZĂÂÎȘȚ][\wĂÂÎȘȚăâîșț-]+)+", text):
        candidates.add(norm(phrase))
    for token in re.findall(r"\b[A-ZĂÂÎȘȚ][A-ZĂÂÎȘȚ0-9-]{2,}\b", text):
        candidates.add(norm(token))
    return candidates


def output_entities(text: str) -> set[str]:
    return source_entities(text) - {norm(x) for x in ENTITY_STOP}


def present_groups(text: str, groups: tuple[tuple[str, ...], ...]) -> list[tuple[str, ...]]:
    value = norm(text)
    return [group for group in groups if any(norm(marker) in value for marker in group)]


def verify(source: str, raw_output: str, case_id: str) -> dict:
    findings: list[dict] = []
    try:
        parsed = json.loads(raw_output, object_pairs_hook=lambda pairs: pairs)
        if not isinstance(parsed, list) or len({k for k, _ in parsed}) != len(parsed):
            raise ValueError("duplicate keys")
        obj = dict(parsed)
        if set(obj) != {"case_id", "text"} or obj.get("case_id") != case_id or not isinstance(obj.get("text"), str) or not obj["text"].strip():
            raise ValueError("schema/case binding")
        text = obj["text"].strip()
    except Exception as exc:
        findings.append({"code": "STRUCTURE_INVALID", "phase": "STRUCTURE", "detail": str(exc)})
        return receipt(case_id, "FAIL_PROVEN", findings, raw_output)

    source_nums, output_nums = canonical_numbers(source), canonical_numbers(text)
    for item in sorted(output_nums - source_nums):
        findings.append({"code": "UNBOUND_NUMBER", "phase": "NUMERIC_BINDING", "canonical_value": item})

    allowed_entities = source_entities(source)
    for item in sorted(output_entities(text) - allowed_entities):
        findings.append({"code": "NOVEL_ENTITY", "phase": "ENTITY_BINDING", "canonical_value": item})

    source_q = present_groups(source, QUALIFICATION_GROUPS)
    output_q = present_groups(text, QUALIFICATION_GROUPS)
    source_s = present_groups(source, STATUS_GROUPS)
    output_s = present_groups(text, STATUS_GROUPS)
    if source_q and not output_q:
        findings.append({"code": "QUALIFICATION_NOT_PROVEN", "phase": "ANCHOR_PRESERVATION"})
    if source_s and not output_s:
        findings.append({"code": "STATUS_NOT_PROVEN", "phase": "ANCHOR_PRESERVATION"})
    if source_q and any(norm(x) in norm(text) for x in FINALITY) and not output_q:
        findings.append({"code": "QUALIFICATION_UPGRADE", "phase": "ANCHOR_PRESERVATION"})

    # Silence is not proof: without a source-bound anchor this deliberately
    # small verifier cannot establish semantic faithfulness.
    if not (source_nums or allowed_entities or source_q or source_s):
        findings.append({"code": "NO_PROVABLE_SOURCE_ANCHOR", "phase": "SOURCE_BINDING"})

    hard = {"UNBOUND_NUMBER", "NOVEL_ENTITY", "QUALIFICATION_UPGRADE"}
    verdict = "FAIL_PROVEN" if any(x["code"] in hard for x in findings) else ("UNPROVEN" if findings else "PASS_PROVEN")
    return receipt(case_id, verdict, findings, raw_output)


def receipt(case_id: str, verdict: str, findings: list[dict], raw_output: str) -> dict:
    assert verdict in VERDICTS
    # Minimal finding evidence: identity plus bounded facts, never the rejected payload.
    core = {"case_id": case_id, "verdict": verdict, "findings": findings, "output_sha256": digest(raw_output.encode()), "payload_persisted": False}
    core["receipt_identity"] = digest(canonical(core))
    return core


def fallback(source: str) -> dict:
    sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+", source.strip()) if x.strip()]
    if 1 <= len(sentences) <= 3:
        return {"route": "SOURCE_PRESERVING_FALLBACK", "text": " ".join(sentences)}
    return {"route": "ABSTAIN", "text": None}


def run(fixtures: dict) -> dict:
    rows = []
    for item in fixtures["cases"]:
        result = verify(item["source"], item["output"], item["case_id"])
        route = {"PASS_PROVEN": "ACCEPT", "FAIL_PROVEN": fallback(item["source"])["route"], "UNPROVEN": fallback(item["source"])["route"]}[result["verdict"]]
        rows.append({"case_id": item["case_id"], "class": item["class"], "expected": item["expected"], "actual": result["verdict"], "route": route, "receipt": result})
    matrix = {name: {"rows": 0, "correct": 0} for name in ("TRUE_MODEL_FAILURE", "VERIFIER_FALSE_REJECTION", "UNPROVEN")}
    for row in rows:
        cell = matrix[row["class"]]; cell["rows"] += 1; cell["correct"] += row["actual"] == row["expected"]
    false_positive = [x["case_id"] for x in rows if x["expected"] == "PASS_PROVEN" and x["actual"] == "FAIL_PROVEN"]
    false_negative = [x["case_id"] for x in rows if x["expected"] == "FAIL_PROVEN" and x["actual"] != "FAIL_PROVEN"]
    core = {"schema": "editor-vnext-minimal-source-bound-verifier-result", "schema_version": 1, "status": "PASS" if all(x["expected"] == x["actual"] for x in rows) else "BLOCKED", "rows": rows, "matrix": matrix, "false_positive_findings": false_positive, "false_negative_findings": false_negative, "legacy_dependency_count": 0, "model_loaded": False, "inference_performed": False, "training_performed": False}
    core["result_identity"] = digest(canonical(core))
    return core


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--fixtures", type=Path, required=True); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise ValueError("output must be new")
    fixtures = json.loads(args.fixtures.read_text(encoding="utf-8"))
    result = run(fixtures); args.output.mkdir(parents=True); (args.output / "result.json").write_bytes(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
    print(json.dumps({k: result[k] for k in ("status", "matrix", "false_positive_findings", "false_negative_findings", "legacy_dependency_count", "result_identity")}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__": main()
