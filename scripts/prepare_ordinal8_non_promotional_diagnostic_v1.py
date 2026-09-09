"""Materialize the 12 structurally valid ordinal-8 packets for blind diagnosis."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath

CASES = ("pcq-eos-001", "pcq-eos-010")
ROLES = {
    "ADJUDICATOR_A": (
        "adjudicator-a-v8",
        "EVALUATOR-A-01",
        "e30913d2a150ff6c3c5d621550c94e9559175921ca9dae49bfbe2bbabc911497",
    ),
    "ADJUDICATOR_B": (
        "adjudicator-b-v8",
        "EVALUATOR-B-03",
        "d6ea703be99aaf08e2228b7a28327412dd15dd16622ede67296f3001ceb33153",
    ),
}
GENERATION = "bbcfa148c1eaf58b5dda2f2f87297b7a573f660020c0d6af3e849cfed137a8b5"
CORPUS = "5933f6ddb450a00566cb42a7dabd908975687360e5d9f16766d55b1dff7899b6"
RUBRIC = "3bff615d5412abbde10a3ab85d45b82a0e019be196ea21914303d1e6b284353b"
SOURCE_PACKET_REGISTRY = (
    "26772b5ae3e7ffe853e75b79b9d37ef7649ad183917afa2a0170f79e2b2d1639"
)
DIAGNOSTIC_REGISTRY = "87104f9ef345177ca9b310e9d726a6430a034b9bfb5b187a5e7ec54c1cca3e51"
PUBLIC_COMMIT = "890aae1904183ec22ab2620f78dfdb02672b4806"
PUBLIC_TREE = "7f458f4bdc6df3b6e3cab2018eaa97e1937874"
AUDIT_IDENTITY = "c749b7d08a43dc1358a6da781265dec98dcec0dcf6bd0dfc193aa7501be6d9b1"
RUBRIC_ARTIFACT_SHA256 = (
    "ecf187216cca9d18f72b2471bc3027d94100b4795af4833aa481e45ff10e9b0c"
)
REGISTRY_ARTIFACT_SHA256 = (
    "2ea556ad4d3a6f28aa02fc49dd7f2647be4ff63f775dbf3baaae2cd25fcf677e"
)
VERDICTS = ("PASS", "FAIL", "INDETERMINATE")


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strict_load(data: bytes) -> dict:
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError(f"duplicate JSON key: {key}")
            out[key] = value
        return out

    value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs)
    if not isinstance(value, dict) or canonical(value) != data:
        raise ValueError("packet is not one canonical JSON object")
    return value


def collect(source: Path) -> list[tuple[Path, dict, bytes]]:
    selected = []
    for path in source.rglob("*.blind.json"):
        if path.is_symlink() or any(
            parent.is_symlink() for parent in path.parents if parent != source.parent
        ):
            raise ValueError(f"symlinked packet path rejected: {path}")
        resolved = path.resolve(strict=True)
        if source not in resolved.parents:
            raise ValueError(f"packet containment invalid: {path}")
        raw = path.read_bytes()
        packet = strict_load(raw)
        validation = packet.get("candidate_output_validation")
        if validation != {
            "status": "PASS",
            "failure_code": None,
            "failure_detail": None,
        }:
            continue
        relative = path.relative_to(source)
        parts = PurePosixPath(relative.as_posix()).parts
        if (
            len(parts) != 4
            or parts[0] not in {"materialization-A", "materialization-B"}
            or parts[1] not in {"repetition-1", "repetition-2", "repetition-3"}
            or parts[2] != "CANDIDATE-A"
        ):
            raise ValueError(f"unexpected valid-packet path: {relative}")
        core = dict(packet)
        identity = core.pop("packet_identity", None)
        case_id = packet.get("case", {}).get("case_id")
        if (
            identity != digest(canonical(core))
            or case_id not in CASES
            or packet.get("candidate_alias") != "CANDIDATE-A"
            or packet.get("qualification_generation_sha256") != GENERATION
            or packet.get("corpus_sha256") != CORPUS
            or packet.get("rubric_sha256") != RUBRIC
            or packet.get("adjudicator_registry_identity") != SOURCE_PACKET_REGISTRY
        ):
            raise ValueError(f"valid packet authority mismatch: {relative}")
        selected.append((relative, packet, raw))
    selected.sort(key=lambda row: row[0].as_posix().encode("ascii"))
    if len(selected) != 12:
        raise ValueError(f"expected exactly 12 valid packets, got {len(selected)}")
    for case_id in CASES:
        rows = [row for row in selected if row[1]["case"]["case_id"] == case_id]
        coordinates = {(r[0].parts[0], r[0].parts[1]) for r in rows}
        expected = {
            (m, f"repetition-{n}")
            for m in ("materialization-A", "materialization-B")
            for n in range(1, 4)
        }
        if len(rows) != 6 or coordinates != expected:
            raise ValueError(f"incomplete six-repetition family: {case_id}")
        if len({r[1]["candidate_output_sha256"] for r in rows}) != 1:
            raise ValueError(f"non-deterministic output family: {case_id}")
    return selected


def manifest(
    role: str,
    evaluator_id: str,
    key_sha: str,
    rows: list[tuple[Path, dict, bytes]],
    supporting_files: list[dict[str, str]],
) -> dict:
    families = []
    inventory = []
    for case_id in CASES:
        family_rows = [row for row in rows if row[1]["case"]["case_id"] == case_id]
        members = []
        for relative, packet, raw in family_rows:
            target_path = f"packets/{relative.as_posix()}"
            item = {
                "path": target_path,
                "sha256": digest(raw),
                "packet_identity": packet["packet_identity"],
                "execution_receipt_identity": packet["execution_receipt_identity"],
                "materialization": relative.parts[0],
                "repetition": relative.parts[1],
            }
            members.append(item)
            inventory.append({"path": target_path, "sha256": digest(raw)})
        families.append(
            {
                "case_id": case_id,
                "candidate_alias": "CANDIDATE-A",
                "request_identity": family_rows[0][1]["case"]["request_identity"],
                "candidate_output_sha256": family_rows[0][1]["candidate_output_sha256"],
                "repetition_count": 6,
                "members": members,
            }
        )
    inventory.sort(key=lambda row: row["path"].encode("ascii"))
    core = {
        "schema": "pastila-production-core-ordinal8-non-promotional-diagnostic-package",
        "schema_version": 1,
        "purpose": "NON_PROMOTIONAL_DIAGNOSTIC",
        "adjudicator_role": role,
        "adjudicator_id": evaluator_id,
        "adjudicator_public_key_sha256": key_sha,
        "public_execution_authority": {
            "commit": PUBLIC_COMMIT,
            "tree": PUBLIC_TREE,
            "ordinal8_audit_identity": AUDIT_IDENTITY,
        },
        "qualification_generation_sha256": GENERATION,
        "corpus_sha256": CORPUS,
        "rubric_sha256": RUBRIC,
        "source_packet_adjudicator_registry_identity": SOURCE_PACKET_REGISTRY,
        "diagnostic_adjudicator_registry_identity": DIAGNOSTIC_REGISTRY,
        "packet_count": 12,
        "family_count": 2,
        "repetitions_per_family": 6,
        "families": families,
        "packet_inventory_sha256": digest(canonical(inventory)),
        "supporting_files": supporting_files,
        "constraints": {
            "hard_gate_result_unchanged": True,
            "hard_gate_compensation_permitted": False,
            "candidate_qualification_effect": False,
            "candidate_promotion_effect": False,
            "retry_or_redraw_permitted": False,
            "new_run_authorized": False,
            "structurally_invalid_outputs_included": False,
        },
    }
    return {**core, "package_identity": digest(canonical(core))}


def decision_message(
    role: str,
    evaluator_id: str,
    key_sha: str,
    relative: Path,
    packet: dict,
    verdict: str,
) -> bytes:
    value = {
        "schema": "pastila-production-core-ordinal8-non-promotional-diagnostic-decision",
        "schema_version": 1,
        "purpose": "NON_PROMOTIONAL_DIAGNOSTIC",
        "diagnostic_adjudicator_registry_identity": DIAGNOSTIC_REGISTRY,
        "qualification_generation_sha256": GENERATION,
        "corpus_sha256": CORPUS,
        "rubric_sha256": RUBRIC,
        "case_id": packet["case"]["case_id"],
        "request_identity": packet["case"]["request_identity"],
        "assertion_sha256": digest(canonical(packet["assertion"])),
        "rubric_artifact_sha256": RUBRIC_ARTIFACT_SHA256,
        "candidate_alias": packet["candidate_alias"],
        "candidate_output_sha256": packet["candidate_output_sha256"],
        "packet_identity": packet["packet_identity"],
        "execution_receipt_identity": packet["execution_receipt_identity"],
        "source_packet_adjudicator_registry_identity": SOURCE_PACKET_REGISTRY,
        "materialization": relative.parts[0],
        "repetition": relative.parts[1],
        "adjudicator_id": evaluator_id,
        "adjudicator_role": role,
        "adjudicator_key_sha256": key_sha,
        "verdict": verdict,
        "hard_gate_result_unchanged": True,
        "hard_gate_compensation_permitted": False,
        "candidate_qualification_effect": False,
        "candidate_promotion_effect": False,
        "retry_or_redraw_permitted": False,
        "new_run_authorized": False,
    }
    return canonical(value)


INSTRUCTIONS = b"""ORDINAL 8 NON_PROMOTIONAL DIAGNOSTIC - OFFLINE ONLY\r
\r
1. Verify the ZIP SHA-256 supplied separately, then extract into a new directory.\r
2. Do not reveal candidate identity and do not obtain the other adjudicator's decisions.\r
3. Review rubric.json and each packet's case, candidate_output, and assertion.\r
4. For every one of the 12 packet coordinates, choose exactly one prebuilt message:\r
   PASS.decision.json, FAIL.decision.json, or INDETERMINATE.decision.json.\r
5. Copy the 12 chosen files to a new selected-decisions directory, preserving paths.\r
6. For each selected message run offline:\r
   openssl pkeyutl -sign -inkey ed25519-private.pem -rawin -in <decision.json> -out <decision.json.sig>\r
7. Return exactly the 12 selected .decision.json files and their 12 .sig files.\r
8. Never return or copy ed25519-private.pem. Do not edit or reserialize decision files.\r
\r
This diagnostic cannot compensate the failed hard gate, promote a candidate, authorize retry/redraw, or authorize a new run.\r
"""


def deterministic_zip(package: Path, archive: Path) -> None:
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as target:
        files = sorted(
            (item for item in package.rglob("*") if item.is_file()),
            key=lambda item: (
                item.relative_to(package.parent).as_posix().encode("ascii")
            ),
        )
        for path in files:
            name = path.relative_to(package.parent).as_posix()
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o100644 << 16
            target.writestr(info, path.read_bytes())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--role", choices=tuple(ROLES), action="append")
    parser.add_argument("--rubric", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    args = parser.parse_args()
    if args.runtime_root.is_symlink():
        raise ValueError("runtime root symlink rejected")
    root = args.runtime_root.resolve(strict=True)
    output = args.output.resolve(strict=False)
    if output.exists() or root == output or root in output.parents:
        raise ValueError("output must be a new sibling outside the source tree")
    role_rows = {}
    for role, (folder, _, _) in ROLES.items():
        lexical_source = root / folder
        if lexical_source.is_symlink():
            raise ValueError("source symlink rejected")
        source = lexical_source.resolve(strict=True)
        if root not in source.parents:
            raise ValueError("source containment invalid")
        role_rows[role] = collect(source)
    a = role_rows["ADJUDICATOR_A"]
    b = role_rows["ADJUDICATOR_B"]
    if [(x[0].as_posix(), x[2]) for x in a] != [(x[0].as_posix(), x[2]) for x in b]:
        raise ValueError("A/B source packet bytes differ")
    selected_roles = tuple(args.role or ROLES)
    rubric_bytes = args.rubric.read_bytes()
    registry_bytes = args.registry.read_bytes()
    if digest(rubric_bytes) != RUBRIC_ARTIFACT_SHA256:
        raise ValueError("rubric artifact identity mismatch")
    if digest(registry_bytes) != REGISTRY_ARTIFACT_SHA256:
        raise ValueError("diagnostic registry artifact identity mismatch")
    output.mkdir(parents=False)
    for role in selected_roles:
        folder, evaluator_id, key_sha = ROLES[role]
        package = output / role
        packet_root = package / "packets"
        package.mkdir()
        rows = role_rows[role]
        for relative, _, raw in rows:
            target = packet_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        (package / "rubric.json").write_bytes(rubric_bytes)
        (package / "diagnostic-registry.json").write_bytes(registry_bytes)
        (package / "SIGNING-INSTRUCTIONS.txt").write_bytes(INSTRUCTIONS)
        decision_inventory = []
        for relative, packet, _ in rows:
            coordinate = Path(
                relative.parts[0], relative.parts[1], packet["case"]["case_id"]
            )
            for verdict in VERDICTS:
                message = decision_message(
                    role, evaluator_id, key_sha, relative, packet, verdict
                )
                decision_path = (
                    package
                    / "decision-messages"
                    / coordinate
                    / f"{verdict}.decision.json"
                )
                decision_path.parent.mkdir(parents=True, exist_ok=True)
                decision_path.write_bytes(message)
                decision_inventory.append(
                    {
                        "path": decision_path.relative_to(package).as_posix(),
                        "sha256": digest(message),
                    }
                )
        decision_inventory.sort(key=lambda row: row["path"].encode("ascii"))
        supporting_files = [
            {"path": "rubric.json", "sha256": digest(rubric_bytes)},
            {"path": "diagnostic-registry.json", "sha256": digest(registry_bytes)},
            {"path": "SIGNING-INSTRUCTIONS.txt", "sha256": digest(INSTRUCTIONS)},
            {
                "path": "decision-messages.inventory.json",
                "sha256": digest(canonical(decision_inventory)),
            },
        ]
        (package / "decision-messages.inventory.json").write_bytes(
            canonical(decision_inventory)
        )
        value = manifest(role, evaluator_id, key_sha, rows, supporting_files)
        (package / "manifest.json").write_bytes(canonical(value))
        deterministic_zip(package, output / f"{role}.NON_PROMOTIONAL_DIAGNOSTIC.zip")
    print(
        canonical(
            {
                role: {
                    "manifest_sha256": digest(
                        (output / role / "manifest.json").read_bytes()
                    ),
                    "package_identity": json.loads(
                        (output / role / "manifest.json").read_bytes()
                    )["package_identity"],
                    "archive_sha256": digest(
                        (output / f"{role}.NON_PROMOTIONAL_DIAGNOSTIC.zip").read_bytes()
                    ),
                }
                for role in selected_roles
            }
        ).decode("utf-8")
    )


if __name__ == "__main__":
    main()
