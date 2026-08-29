"""Request-bound terminal semantic completeness admission for V2 ledgers."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .immutable_source_span_reference_v1 import ImmutableUtf8SourceV1, SourceRoleV1
from .stage_p_construction_obligation_contract_v2 import ConstructionObligationLedgerV2
from .stage_p_role_coherence_contract_v1 import EntryType, Modality


CASE01_CANDIDATE_SHA256 = "52a54bad5c68d16bd326c9dac8c544b5c4b0a45b9129262a0da139167362682b"
CASE01_AUTHORITY_SHA256 = "e2add20c2ac06fdc90a2f7e1960d5672b8e91a9f7a82b895203dfb43f7f9d196"
ADMISSION_VERSION = "REQUEST_BOUND_SEMANTIC_COMPLETENESS_V1"


class SemanticCompletenessFailureV1(ValueError):
    """A schema-terminal ledger is not semantically admissible."""


@dataclass(frozen=True, slots=True)
class CoverageGapJustificationV1:
    start_utf8: int
    end_utf8: int
    reason_code: str


@dataclass(frozen=True, slots=True)
class UnresolvedJustificationV1:
    start_utf8: int
    end_utf8: int
    reason_code: str
    competing_interpretations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class QualificationObligationV1:
    start_utf8: int
    end_utf8: int
    required_modality: Modality


@dataclass(frozen=True, slots=True)
class SemanticCompletenessPolicyV1:
    candidate_sha256: str
    authority_sha256: str
    candidate_bytes: int
    justified_gaps: tuple[CoverageGapJustificationV1, ...]
    unresolved_justifications: tuple[UnresolvedJustificationV1, ...]
    qualifications: tuple[QualificationObligationV1, ...]
    creative_target_analysis_required: bool
    factual_authority_analysis_required: bool
    identity: str

    @classmethod
    def bind(
        cls, *, candidate: ImmutableUtf8SourceV1,
        factual_authority: ImmutableUtf8SourceV1,
        justified_gaps: tuple[CoverageGapJustificationV1, ...] = (),
        unresolved_justifications: tuple[UnresolvedJustificationV1, ...] = (),
    ) -> "SemanticCompletenessPolicyV1":
        if candidate.role is not SourceRoleV1.CANDIDATE:
            raise ValueError("SEMANTIC_COMPLETENESS_CANDIDATE_ROLE_INVALID")
        if factual_authority.role is not SourceRoleV1.FACTUAL_AUTHORITY:
            raise ValueError("SEMANTIC_COMPLETENESS_AUTHORITY_ROLE_INVALID")
        qualifications = _qualification_obligations(candidate.data)
        case01 = (candidate.sha256 == CASE01_CANDIDATE_SHA256 and
                  factual_authority.sha256 == CASE01_AUTHORITY_SHA256)
        value = {
            "version": ADMISSION_VERSION,
            "candidate_sha256": candidate.sha256,
            "authority_sha256": factual_authority.sha256,
            "candidate_bytes": len(candidate.data),
            "justified_gaps": [gap.__dict__ if hasattr(gap, "__dict__") else
                               {"start_utf8": gap.start_utf8, "end_utf8": gap.end_utf8,
                                "reason_code": gap.reason_code} for gap in justified_gaps],
            "unresolved_justifications": [
                {"start_utf8": item.start_utf8, "end_utf8": item.end_utf8,
                 "reason_code": item.reason_code,
                 "competing_interpretations": item.competing_interpretations}
                for item in unresolved_justifications],
            "qualifications": [
                {"start_utf8": item.start_utf8, "end_utf8": item.end_utf8,
                 "required_modality": item.required_modality.value}
                for item in qualifications],
            "creative_target_analysis_required": case01,
            "factual_authority_analysis_required": case01,
        }
        identity = hashlib.sha256((json.dumps(
            value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()).hexdigest()
        return cls(candidate.sha256, factual_authority.sha256, len(candidate.data),
                   justified_gaps, unresolved_justifications, qualifications,
                   case01, case01, identity)


@dataclass(frozen=True, slots=True)
class SemanticCompletenessAdmissionV1:
    policy: SemanticCompletenessPolicyV1

    def validate_terminal(self, raw_json: str) -> ConstructionObligationLedgerV2:
        try:
            ledger = ConstructionObligationLedgerV2.model_validate_json(raw_json, strict=True)
        except Exception as exc:
            raise SemanticCompletenessFailureV1(
                "SEMANTIC_COMPLETENESS_SCHEMA_INVALID") from exc
        self._validate(ledger)
        return ledger

    def _validate(self, ledger: ConstructionObligationLedgerV2) -> None:
        references = [record.candidate_span_ref
                      for record in ledger.construction_role_audit.construction_records]
        references.extend(entry.candidate_span_ref for entry in ledger.entries)
        references.extend(audit.vehicle_span_ref for audit in ledger.creative_target_audits)
        for reference in references:
            if reference.source_sha256 != self.policy.candidate_sha256:
                self._fail("SEMANTIC_COMPLETENESS_CANDIDATE_IDENTITY_MISMATCH")

        expected = set(range(self.policy.candidate_bytes))
        covered: set[int] = set()
        for reference in references:
            covered.update(range(reference.start_utf8, reference.end_utf8))
        justified: set[int] = set()
        for gap in self.policy.justified_gaps:
            if (not gap.reason_code or gap.start_utf8 < 0 or
                    gap.end_utf8 <= gap.start_utf8 or gap.end_utf8 > self.policy.candidate_bytes):
                self._fail("SEMANTIC_COMPLETENESS_GAP_JUSTIFICATION_INVALID")
            justified.update(range(gap.start_utf8, gap.end_utf8))
        if covered | justified != expected or covered & justified:
            self._fail("SEMANTIC_COMPLETENESS_CANDIDATE_COVERAGE_INCOMPLETE")

        fingerprints: set[str] = set()
        for entry in ledger.entries:
            value = entry.model_dump(mode="json")
            for key in ("entry_id", "independence_group"):
                value.pop(key)
            fingerprint = json.dumps(value, ensure_ascii=True, sort_keys=True,
                                     separators=(",", ":"))
            if fingerprint in fingerprints:
                self._fail("SEMANTIC_COMPLETENESS_DUPLICATE_ENTRY")
            fingerprints.add(fingerprint)

        receipt = ledger.coverage_receipt
        required_receipts = (
            receipt.embedded_propositions_checked, receipt.creative_scope_checked,
            receipt.overlapping_spans_reconciled, receipt.integrated_creative_hosts_checked,
            receipt.factual_return_tests_completed, receipt.creative_targets_enumerated,
            receipt.target_classes_reviewed, receipt.target_to_ledger_reconciled,
            receipt.construction_roles_reviewed, receipt.construction_to_ledger_reconciled)
        if receipt.candidate_reviewed_as_whole and not all(required_receipts):
            self._fail("SEMANTIC_COMPLETENESS_WHOLE_REVIEW_INCONSISTENT")
        if not receipt.candidate_reviewed_as_whole:
            self._fail("SEMANTIC_COMPLETENESS_WHOLE_REVIEW_REQUIRED")
        if not ledger.construction_role_audit.construction_records:
            self._fail("SEMANTIC_COMPLETENESS_CONSTRUCTION_ANALYSIS_REQUIRED")
        if self.policy.creative_target_analysis_required and not ledger.creative_target_audits:
            self._fail("SEMANTIC_COMPLETENESS_CREATIVE_TARGET_ANALYSIS_REQUIRED")
        if (self.policy.factual_authority_analysis_required and
                not any(entry.authority_support_ref is not None for entry in ledger.entries)):
            self._fail("SEMANTIC_COMPLETENESS_FACTUAL_AUTHORITY_ANALYSIS_REQUIRED")

        unresolved = [entry.candidate_span_ref for entry in ledger.entries
                      if entry.entry_type is EntryType.UNRESOLVED_SCOPE]
        unresolved.extend(record.candidate_span_ref
                          for record in ledger.construction_role_audit.construction_records
                          if record.construction_role.value == "UNRESOLVED")
        for reference in unresolved:
            matches = [item for item in self.policy.unresolved_justifications
                       if (item.start_utf8, item.end_utf8) ==
                       (reference.start_utf8, reference.end_utf8)]
            if len(matches) != 1:
                self._fail("SEMANTIC_COMPLETENESS_UNRESOLVED_JUSTIFICATION_REQUIRED")
            item = matches[0]
            if (not item.reason_code or len(item.competing_interpretations) < 2 or
                    len(set(item.competing_interpretations)) != len(item.competing_interpretations) or
                    any(not interpretation.strip() for interpretation in item.competing_interpretations)):
                self._fail("SEMANTIC_COMPLETENESS_UNRESOLVED_JUSTIFICATION_INVALID")

        for obligation in self.policy.qualifications:
            matching = [entry for entry in ledger.entries
                        if entry.entry_type is EntryType.REAL_WORLD_COMMITMENT and
                        entry.candidate_span_ref.start_utf8 <= obligation.start_utf8 and
                        entry.candidate_span_ref.end_utf8 >= obligation.end_utf8 and
                        entry.candidate_modality is obligation.required_modality]
            if not matching:
                self._fail("SEMANTIC_COMPLETENESS_QUALIFICATION_MODALITY_REQUIRED")

    @staticmethod
    def _fail(reason: str) -> None:
        raise SemanticCompletenessFailureV1(reason)


def _qualification_obligations(candidate: bytes) -> tuple[QualificationObligationV1, ...]:
    text = candidate.decode("utf-8", errors="strict")
    obligations = []
    for cue, modality in (("pare că", Modality.POSSIBLE),):
        offset = 0
        while True:
            index = text.find(cue, offset)
            if index < 0:
                break
            start = len(text[:index].encode("utf-8"))
            end = start + len(cue.encode("utf-8"))
            obligations.append(QualificationObligationV1(start, end, modality))
            offset = index + len(cue)
    return tuple(obligations)


__all__ = (
    "ADMISSION_VERSION", "CoverageGapJustificationV1",
    "QualificationObligationV1", "SemanticCompletenessAdmissionV1",
    "SemanticCompletenessFailureV1", "SemanticCompletenessPolicyV1",
    "UnresolvedJustificationV1",
)
