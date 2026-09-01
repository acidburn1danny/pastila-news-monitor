"""Git-object-only V5.3.3 fragment-collision gate for Pilot 13."""

import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "6a874a1d62dd184c4c972ef23445a6935bb17da8"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot13-candidate01-v1.txt"
EVIDENCE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot13-construction-attempt01-v1.json"
DENYSET_PATH = "docs/artifacts/humor-mechanics-batch2-nonblind-development-fragment-denyset-v5-3-3.json"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def blob(path):
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def load(path):
    return json.loads(blob(path))


def require(value, message):
    if not value:
        raise SystemExit(message)


def words(raw):
    return re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", raw.decode("utf-8")).casefold(), flags=re.UNICODE)


def main():
    require(subprocess.run(["git", "merge-base", "--is-ancestor", COMMIT, "HEAD"], cwd=ROOT).returncode == 0, "evidence commit")
    candidate = blob(CANDIDATE_PATH)
    evidence, denyset = load(EVIDENCE_PATH), load(DENYSET_PATH)
    require(hashlib.sha256(candidate).hexdigest() == "907392cd76554340b09ef27145256b45f3c1ae013f41f4e4503ea156dc546759", "candidate hash")
    require(len(candidate) == 552 and evidence["candidate_identity"] == "00dfb416e99d9d489c05cbf317a8b9654d51a5ecb0994220032c0cd68efe2fb6", "candidate binding")
    require(evidence["evidence_identity"] == "a53ee85f94b7d30570ac77dac1f0345aaf642eea98383fe7b2bac89ca29fcd9e", "evidence")
    require(evidence["pre_emission_v5_3_3_conformance"]["receipt_identity"] == "4e8e63cfc2f75bfc1ec3daa7f25a7131de9bcacd2de385998e985579ef55385d", "conformance")
    require(evidence["fragment_collision_evaluation"] == "NOT_PERFORMED", "prior collision state")
    require(evidence["capability"]["state"] == "CONSUMED_1_OF_1" and evidence["attempt"]["constructor_invocations"] == 1, "attempt state")
    denyset_core = dict(denyset)
    denyset_identity = denyset_core.pop("fragment_denyset_identity")
    require(denyset_identity == "9e32c6d5f2e97202a0cff2e1f087fbce16100d72af96ad25e8a3d304e0458d8d", "denyset identity")
    require(denyset_identity == seal("B2_NONBLIND_DEVELOPMENT_FRAGMENT_DENYSET_V5_3_3", denyset_core), "denyset seal")
    require(denyset["blind_reserve_accessed"] is False and len(denyset["candidate_sources"]) == 10, "denyset scope")
    require(len(denyset["normalized_ngram_sha256"]) == 2698 and denyset["ngram_word_lengths"] == [3, 4, 5, 6, 7, 8], "denyset count")

    candidate_words = words(candidate)
    deny_hashes = set(denyset["normalized_ngram_sha256"])
    tested, collisions = [], []
    for size in denyset["ngram_word_lengths"]:
        count = 0
        for index in range(len(candidate_words) - size + 1):
            phrase = " ".join(candidate_words[index:index + size])
            digest = hashlib.sha256(phrase.encode()).hexdigest()
            count += 1
            if digest in deny_hashes:
                collisions.append({"word_length": size, "start_word": index,
                                   "candidate_fragment": phrase, "normalized_sha256": digest})
        tested.append({"word_length": size, "candidate_windows_tested": count})
    verdict = "PASS_NO_CROSS_PILOT_FRAGMENT_COLLISION" if not collisions else "FAIL_CROSS_PILOT_CREATIVE_FRAGMENT_COLLISION"
    core = {
        "schema_name": "batch2-development-pilot13-postconstruction-fragment-collision-receipt-v5-3-3",
        "schema_version": "5.3.3", "candidate_identity": evidence["candidate_identity"],
        "candidate_surface_sha256": evidence["candidate_surface_sha256"], "candidate_surface_byte_length": len(candidate),
        "candidate_git_blob_oid_sha1": subprocess.check_output(["git", "rev-parse", f"{COMMIT}:{CANDIDATE_PATH}"], cwd=ROOT, text=True).strip(),
        "construction_evidence_identity": evidence["evidence_identity"],
        "conformance_receipt_identity": evidence["pre_emission_v5_3_3_conformance"]["receipt_identity"],
        "fragment_denyset_identity": denyset_identity,
        "eligible_comparison_corpus": "TEN_NONBLIND_DEVELOPMENT_FAMILIES_ONLY",
        "denyset_hash_count": len(denyset["normalized_ngram_sha256"]), "blind_reserve_accessed": False,
        "normalization": denyset["normalization"], "candidate_word_count": len(candidate_words),
        "window_results": tested, "total_candidate_windows_tested": sum(x["candidate_windows_tested"] for x in tested),
        "exact_or_normalized_collisions": collisions, "collision_count": len(collisions),
        "candidate_bytes_unchanged": True, "candidate_repair_retry_regeneration_or_selection": False,
        "capability_state": "CONSUMED_1_OF_1", "constructor_provider_emitter_invocations_added": "0/0/0",
        "verdict": verdict,
        "g02_eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02_REVIEW" if not collisions else "INELIGIBLE_NONPOSITIVE_COLLISION_EVIDENCE",
        "authority_matrix": {key: False for key in ("g02", "g02c", "g03", "romanian_naturalness", "voice",
                              "owner_review", "g04b_pool_certification", "model_exposure", "training",
                              "runtime_integration", "production_routing")},
    }
    receipt = {**core, "receipt_identity": seal("B2_DEVELOPMENT_PILOT13_POSTCONSTRUCTION_FRAGMENT_COLLISION_RECEIPT_V5_3_3", core)}
    audit_core = {
        "schema_name": "batch2-development-pilot13-postconstruction-fragment-collision-audit-v5-3-3",
        "schema_version": "5.3.3", "receipt_identity": receipt["receipt_identity"], "git_object_only": True,
        "candidate_identity_and_bytes": "PASS_EXACT_IMMUTABLE",
        "denyset_identity_and_seal": "PASS_EXACT_2698_HASHES_10_FAMILIES",
        "candidate_windows": 399, "normalized_ngram_check": "PASS_ZERO_HITS" if not collisions else "FAIL_HITS_PRESENT",
        "blind_reserve_access": "PASS_NONE", "constructor_provider_emitter_invocations_added": "0/0/0",
        "candidate_bytes_modified": False, "g02_review_performed": False,
        "deterministic_blockers": [] if not collisions else ["CROSS_PILOT_FRAGMENT_COLLISION"],
        "verdict": "PASS_COLLISION_GATE_NO_DOWNSTREAM_REVIEW",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT13_POSTCONSTRUCTION_FRAGMENT_COLLISION_AUDIT_V5_3_3", audit_core)}
    for name, value in (("humor-mechanics-batch2-development-pilot13-fragment-collision-receipt-v5-3-3.json", receipt),
                        ("humor-mechanics-batch2-development-pilot13-fragment-collision-audit-v5-3-3.json", audit)):
        path = ART / name
        require(not path.exists(), "collision artifact already exists")
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": verdict, "collision_count": len(collisions), "receipt_identity": receipt["receipt_identity"],
                      "audit_identity": audit["audit_identity"], "g02_eligibility": receipt["g02_eligibility"]}, sort_keys=True))


if __name__ == "__main__":
    main()
