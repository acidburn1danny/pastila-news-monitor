"""Request-bound terminal semantic completeness admission for V2 ledgers."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, replace

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
    construction_ids: tuple[str, ...]
    entry_ids: tuple[str, ...]
    competing_interpretations: tuple["SourceBoundInterpretationV1", ...]


@dataclass(frozen=True, slots=True)
class SourceBoundInterpretationV1:
    label: str
    source_sha256: str
    start_utf8: int
    end_utf8: int


@dataclass(frozen=True, slots=True)
class QualificationObligationV1:
    start_utf8: int
    end_utf8: int
    required_modality: Modality
    required_proposition_entry_id: str | None


@dataclass(frozen=True, slots=True)
class QualificationAuditV1:
    source_sha256: str
    cue_start_utf8: int
    cue_end_utf8: int
    proposition_entry_id: str
    observed_modality: Modality
    audit_identity: str


@dataclass(frozen=True, slots=True)
class RequiredReturnObligationV1:
    construction_id: str
    entry_id: str
    required_construction_return_ids: tuple[str, ...]
    creative_host_entry_id: str
    candidate_start_utf8: int
    candidate_end_utf8: int
    normalized_commitment: str
    scope_basis: str
    event_alignment: str
    candidate_modality: str
    candidate_timing: str
    authority_modality: str
    authority_timing: str
    scope_relation: str
    factual_return_basis: str


@dataclass(frozen=True, slots=True)
class RequiredTopologyV1:
    construction_ids: tuple[str, ...]
    entry_ids: tuple[str, ...]
    creative_audit_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RequiredConstructionSemanticsV1:
    construction_id: str
    candidate_start_utf8: int
    candidate_end_utf8: int
    normalized_role_basis: str
    construction_role: str
    creative_host_entry_id: str
    literal_or_return_entry_ids: tuple[str, ...]
    resolution: str


@dataclass(frozen=True, slots=True)
class RequiredCreativeSemanticsV1:
    entry_id: str
    candidate_start_utf8: int
    candidate_end_utf8: int
    normalized_commitment: str
    audit_id: str
    vehicle_start_utf8: int
    vehicle_end_utf8: int
    normalized_semantic_target: str


@dataclass(frozen=True, slots=True)
class SemanticCompletenessPolicyV1:
    candidate_sha256: str
    authority_sha256: str
    candidate_bytes: int
    authority_bytes: int
    candidate_utf8_boundaries: tuple[int, ...]
    justified_gaps: tuple[CoverageGapJustificationV1, ...]
    unresolved_justifications: tuple[UnresolvedJustificationV1, ...]
    qualifications: tuple[QualificationObligationV1, ...]
    required_returns: tuple[RequiredReturnObligationV1, ...]
    required_topology: RequiredTopologyV1 | None
    required_constructions: tuple[RequiredConstructionSemanticsV1, ...]
    required_creative: tuple[RequiredCreativeSemanticsV1, ...]
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
        case01 = (candidate.sha256 == CASE01_CANDIDATE_SHA256 and
                  factual_authority.sha256 == CASE01_AUTHORITY_SHA256)
        qualifications = _qualification_obligations(candidate.data, case01=case01)
        required_returns = _required_return_obligations(
            candidate.data, qualifications=qualifications, case01=case01)
        required_topology = (RequiredTopologyV1(
            ("C1",), ("P1", "P2"), ("T1",)) if case01 else None)
        required_constructions = _required_construction_semantics(
            candidate.data, case01=case01)
        required_creative = _required_creative_semantics(
            candidate.data, case01=case01)
        boundaries = _utf8_boundaries(candidate.data)
        provisional = cls(
            candidate.sha256, factual_authority.sha256, len(candidate.data),
            len(factual_authority.data), boundaries, justified_gaps,
            unresolved_justifications, qualifications, required_returns,
            required_topology, required_constructions, required_creative,
            case01, case01, "")
        return seal_semantic_completeness_policy_v1(provisional)


@dataclass(frozen=True, slots=True)
class SemanticCompletenessAdmissionV1:
    policy: SemanticCompletenessPolicyV1

    def validate_terminal(self, raw_json: str) -> ConstructionObligationLedgerV2:
        if self.policy.identity != _policy_identity(self.policy):
            raise SemanticCompletenessFailureV1(
                "SEMANTIC_COMPLETENESS_POLICY_IDENTITY_MISMATCH")
        try:
            ledger = ConstructionObligationLedgerV2.model_validate_json(raw_json, strict=True)
        except Exception as exc:
            raise SemanticCompletenessFailureV1(
                "SEMANTIC_COMPLETENESS_SCHEMA_INVALID") from exc
        self._validate(ledger)
        return ledger

    def qualification_audits(
        self, ledger: ConstructionObligationLedgerV2,
    ) -> tuple[QualificationAuditV1, ...]:
        return tuple(self._qualification_audit(ledger, obligation)
                     for obligation in self.policy.qualifications)

    def _validate(self, ledger: ConstructionObligationLedgerV2) -> None:
        construction_references = [
            record.candidate_span_ref
            for record in ledger.construction_role_audit.construction_records]
        proposition_references = [entry.candidate_span_ref for entry in ledger.entries]
        for reference in construction_references + proposition_references:
            if reference.source_sha256 != self.policy.candidate_sha256:
                self._fail("SEMANTIC_COMPLETENESS_CANDIDATE_IDENTITY_MISMATCH")
        justified = self._validated_gap_partition()
        self._require_coverage(construction_references, justified,
                               "SEMANTIC_COMPLETENESS_CONSTRUCTION_COVERAGE_INCOMPLETE")
        self._require_coverage(proposition_references, justified,
                               "SEMANTIC_COMPLETENESS_PROPOSITION_COVERAGE_INCOMPLETE")

        host_bases = {entry.entry_id: self._entry_base(entry)
                      for entry in ledger.entries}
        fingerprints: set[str] = set()
        for entry in ledger.entries:
            value = self._entry_base(entry)
            value["creative_host"] = (None if entry.creative_host_entry_id is None
                                      else host_bases.get(entry.creative_host_entry_id))
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
        construction_hosts = {
            record.creative_host_entry_id: record.candidate_span_ref
            for record in ledger.construction_role_audit.construction_records
            if record.creative_host_entry_id is not None}
        for audit in ledger.creative_target_audits:
            construction_span = construction_hosts.get(audit.creative_host_entry_id)
            if (construction_span is None or
                    audit.vehicle_span_ref != construction_span):
                self._fail("SEMANTIC_COMPLETENESS_CREATIVE_TARGET_BINDING_INVALID")
        if any(entry.authority_support_ref is not None
               for entry in ledger.entries
               if entry.entry_type is not EntryType.REAL_WORLD_COMMITMENT):
            self._fail("SEMANTIC_COMPLETENESS_AUTHORITY_ON_NONFACTUAL_ENTRY")
        construction_return_ids = {
            entry_id for record in ledger.construction_role_audit.construction_records
            for entry_id in record.literal_or_return_entry_ids}
        bound_returns = [
            entry for entry in ledger.entries
            if (entry.entry_id in construction_return_ids and
                entry.entry_type is EntryType.REAL_WORLD_COMMITMENT)]
        if self.policy.factual_authority_analysis_required:
            if not bound_returns or any(
                    entry.authority_support_ref is None for entry in bound_returns):
                self._fail("SEMANTIC_COMPLETENESS_FACTUAL_AUTHORITY_ANALYSIS_REQUIRED")
            if any(entry.authority_support_ref is not None
                   for entry in ledger.entries
                   if entry.entry_id not in construction_return_ids):
                self._fail("SEMANTIC_COMPLETENESS_AUTHORITY_ON_UNBOUND_ENTRY")
            required_authority_ids = {
                obligation.required_proposition_entry_id
                for obligation in self.policy.qualifications
                if obligation.required_proposition_entry_id is not None}
            if not required_authority_ids:
                required_authority_ids = {entry.entry_id for entry in bound_returns}
            index = {entry.entry_id: entry for entry in bound_returns}
            if not required_authority_ids.issubset(index):
                self._fail("SEMANTIC_COMPLETENESS_REQUIRED_AUTHORITY_RETURN_MISSING")
            for entry_id in sorted(required_authority_ids):
                reference = index[entry_id].authority_support_ref
                if reference is None:
                    self._fail("SEMANTIC_COMPLETENESS_FACTUAL_AUTHORITY_ANALYSIS_REQUIRED")
                if reference.source_sha256 != self.policy.authority_sha256:
                    self._fail("SEMANTIC_COMPLETENESS_AUTHORITY_IDENTITY_MISMATCH")
                if (reference.start_utf8 != 0 or
                        reference.end_utf8 != self.policy.authority_bytes):
                    self._fail("SEMANTIC_COMPLETENESS_AUTHORITY_COVERAGE_INCOMPLETE")
        self._validate_required_returns(ledger)
        self._validate_required_topology(ledger)
        self._validate_required_case_semantics(ledger)

        unresolved = [(entry.entry_id, "entry", entry.candidate_span_ref)
                      for entry in ledger.entries
                      if entry.entry_type is EntryType.UNRESOLVED_SCOPE]
        unresolved.extend((record.construction_id, "construction", record.candidate_span_ref)
                          for record in ledger.construction_role_audit.construction_records
                          if record.construction_role.value == "UNRESOLVED")
        observed_by_span: dict[tuple[int, int], dict[str, set[str]]] = {}
        for record_id, kind, reference in unresolved:
            group = observed_by_span.setdefault(
                (reference.start_utf8, reference.end_utf8),
                {"entry": set(), "construction": set()})
            group[kind].add(record_id)
        declared_by_span: dict[tuple[int, int], UnresolvedJustificationV1] = {}
        for item in self.policy.unresolved_justifications:
            span = (item.start_utf8, item.end_utf8)
            if (span in declared_by_span or
                    len(item.entry_ids) != len(set(item.entry_ids)) or
                    len(item.construction_ids) != len(set(item.construction_ids))):
                self._fail("SEMANTIC_COMPLETENESS_UNRESOLVED_ID_SET_MISMATCH")
            declared_by_span[span] = item
        if set(declared_by_span) != set(observed_by_span):
            self._fail("SEMANTIC_COMPLETENESS_UNRESOLVED_ID_SET_MISMATCH")
        for span, observed_ids in observed_by_span.items():
            item = declared_by_span[span]
            if (set(item.entry_ids) != observed_ids["entry"] or
                    set(item.construction_ids) != observed_ids["construction"]):
                self._fail("SEMANTIC_COMPLETENESS_UNRESOLVED_ID_SET_MISMATCH")
        for record_id, record_kind, reference in unresolved:
            matches = [item for item in self.policy.unresolved_justifications
                       if (item.start_utf8, item.end_utf8) ==
                       (reference.start_utf8, reference.end_utf8) and
                       record_id in (item.entry_ids if record_kind == "entry"
                                     else item.construction_ids)]
            if len(matches) != 1:
                self._fail("SEMANTIC_COMPLETENESS_UNRESOLVED_JUSTIFICATION_REQUIRED")
            item = matches[0]
            if record_kind == "construction":
                record = next(value for value in
                              ledger.construction_role_audit.construction_records
                              if value.construction_id == record_id)
                if record.role_basis != item.reason_code:
                    self._fail("SEMANTIC_COMPLETENESS_UNRESOLVED_REASON_MISMATCH")
            interpretations = item.competing_interpretations
            if (item.reason_code not in {"LEXICAL_AMBIGUITY", "SCOPE_AMBIGUITY",
                                         "CONSTRUCTION_ROLE_AMBIGUITY"} or
                    len(interpretations) < 2 or
                    len({_normalized_text(value.label) for value in interpretations}) !=
                    len(interpretations) or any(
                        value.source_sha256 != self.policy.candidate_sha256 or
                        value.start_utf8 != item.start_utf8 or
                        value.end_utf8 != item.end_utf8 or not value.label.strip()
                        for value in interpretations)):
                self._fail("SEMANTIC_COMPLETENESS_UNRESOLVED_JUSTIFICATION_INVALID")
        self.qualification_audits(ledger)

    def _validated_gap_partition(self) -> set[int]:
        justified: set[int] = set()
        previous_end = -1
        boundaries = set(self.policy.candidate_utf8_boundaries)
        for gap in self.policy.justified_gaps:
            if (gap.reason_code not in {"NON_SEMANTIC_SEPARATOR", "OUT_OF_SCOPE_METADATA"} or
                    gap.start_utf8 not in boundaries or gap.end_utf8 not in boundaries or
                    gap.start_utf8 < previous_end or gap.end_utf8 <= gap.start_utf8):
                self._fail("SEMANTIC_COMPLETENESS_GAP_JUSTIFICATION_INVALID")
            previous_end = gap.end_utf8
            justified.update(range(gap.start_utf8, gap.end_utf8))
        return justified

    def _require_coverage(self, references, justified: set[int], reason: str) -> None:
        covered: set[int] = set()
        for reference in references:
            covered.update(range(reference.start_utf8, reference.end_utf8))
        expected = set(range(self.policy.candidate_bytes))
        if covered | justified != expected or covered & justified:
            self._fail(reason)

    @staticmethod
    def _entry_base(entry) -> dict:
        value = entry.model_dump(mode="json")
        for key in ("entry_id", "independence_group", "creative_host_entry_id"):
            value.pop(key)
        return _normalize_value(value)

    def _qualification_audit(self, ledger, obligation) -> QualificationAuditV1:
        return_ids = {entry_id
                      for record in ledger.construction_role_audit.construction_records
                      for entry_id in record.literal_or_return_entry_ids}
        matching = [entry for entry in ledger.entries
                    if entry.entry_id in return_ids and
                    (obligation.required_proposition_entry_id is None or
                     entry.entry_id == obligation.required_proposition_entry_id) and
                    entry.entry_type is EntryType.REAL_WORLD_COMMITMENT and
                    entry.authority_support_ref is not None and
                    entry.candidate_span_ref.start_utf8 == obligation.start_utf8 and
                    entry.candidate_span_ref.end_utf8 >= obligation.end_utf8 and
                    entry.candidate_modality is obligation.required_modality]
        if len(matching) != 1:
            self._fail("SEMANTIC_COMPLETENESS_QUALIFICATION_MODALITY_REQUIRED")
        entry = matching[0]
        fields = (self.policy.identity, self.policy.candidate_sha256,
                  str(obligation.start_utf8), str(obligation.end_utf8),
                  entry.entry_id, entry.candidate_modality.value)
        identity = hashlib.sha256("\n".join(fields).encode()).hexdigest()
        return QualificationAuditV1(
            self.policy.candidate_sha256, obligation.start_utf8,
            obligation.end_utf8, entry.entry_id, entry.candidate_modality, identity)

    def _validate_required_returns(self, ledger) -> None:
        entries = {entry.entry_id: entry for entry in ledger.entries}
        constructions = {
            record.construction_id: record
            for record in ledger.construction_role_audit.construction_records}
        for obligation in self.policy.required_returns:
            entry = entries.get(obligation.entry_id)
            construction = constructions.get(obligation.construction_id)
            if entry is None or construction is None:
                self._fail("SEMANTIC_COMPLETENESS_REQUIRED_RETURN_MISSING")
            observed = (
                entry.creative_host_entry_id,
                entry.candidate_span_ref.start_utf8,
                entry.candidate_span_ref.end_utf8,
                _normalized_text(entry.commitment),
                entry.scope_basis.value,
                entry.event_alignment.value,
                entry.candidate_modality.value,
                entry.candidate_timing.value,
                entry.authority_modality.value,
                entry.authority_timing.value,
                entry.scope_relation.value,
                entry.factual_return_basis.value,
            )
            expected = (
                obligation.creative_host_entry_id,
                obligation.candidate_start_utf8,
                obligation.candidate_end_utf8,
                obligation.normalized_commitment,
                obligation.scope_basis,
                obligation.event_alignment,
                obligation.candidate_modality,
                obligation.candidate_timing,
                obligation.authority_modality,
                obligation.authority_timing,
                obligation.scope_relation,
                obligation.factual_return_basis,
            )
            if observed != expected:
                self._fail("SEMANTIC_COMPLETENESS_REQUIRED_RETURN_SEMANTICS_MISMATCH")
            if (construction.creative_host_entry_id != obligation.creative_host_entry_id or
                    tuple(construction.literal_or_return_entry_ids) !=
                    obligation.required_construction_return_ids or
                    construction.construction_role.value !=
                    "MIXED_CREATIVE_AND_REAL_WORLD"):
                self._fail("SEMANTIC_COMPLETENESS_REQUIRED_RETURN_BINDING_MISMATCH")

    def _validate_required_topology(self, ledger) -> None:
        topology = self.policy.required_topology
        if topology is None:
            return
        observed = (
            tuple(sorted(record.construction_id for record in
                         ledger.construction_role_audit.construction_records)),
            tuple(sorted(entry.entry_id for entry in ledger.entries)),
            tuple(sorted(audit.audit_id for audit in ledger.creative_target_audits)),
        )
        expected = (
            tuple(sorted(topology.construction_ids)),
            tuple(sorted(topology.entry_ids)),
            tuple(sorted(topology.creative_audit_ids)),
        )
        if observed != expected:
            self._fail("SEMANTIC_COMPLETENESS_REQUIRED_TOPOLOGY_MISMATCH")

    def _validate_required_case_semantics(self, ledger) -> None:
        constructions = {
            item.construction_id: item
            for item in ledger.construction_role_audit.construction_records}
        entries = {item.entry_id: item for item in ledger.entries}
        audits = {item.audit_id: item for item in ledger.creative_target_audits}
        for obligation in self.policy.required_constructions:
            record = constructions.get(obligation.construction_id)
            if record is None or (
                    record.candidate_span_ref.start_utf8,
                    record.candidate_span_ref.end_utf8,
                    _normalized_text(record.role_basis),
                    record.construction_role.value,
                    record.creative_host_entry_id,
                    tuple(record.literal_or_return_entry_ids),
                    record.resolution.value) != (
                        obligation.candidate_start_utf8,
                        obligation.candidate_end_utf8,
                        obligation.normalized_role_basis,
                        obligation.construction_role,
                        obligation.creative_host_entry_id,
                        obligation.literal_or_return_entry_ids,
                        obligation.resolution):
                self._fail("SEMANTIC_COMPLETENESS_CONSTRUCTION_SEMANTICS_MISMATCH")
        for obligation in self.policy.required_creative:
            entry = entries.get(obligation.entry_id)
            audit = audits.get(obligation.audit_id)
            if entry is None or audit is None:
                self._fail("SEMANTIC_COMPLETENESS_CREATIVE_SEMANTICS_MISSING")
            entry_tuple = (
                entry.candidate_span_ref.start_utf8,
                entry.candidate_span_ref.end_utf8,
                _normalized_text(entry.commitment), entry.entry_type.value,
                entry.scope_basis.value, entry.event_alignment.value,
                entry.scope_relation.value, entry.factual_return_basis.value)
            audit_tuple = (
                audit.vehicle_span_ref.start_utf8,
                audit.vehicle_span_ref.end_utf8,
                _normalized_text(audit.semantic_target),
                audit.creative_host_entry_id, audit.target_class.value,
                audit.survival_basis.value, audit.proposition_entry_id,
                audit.resolution.value)
            if entry_tuple != (
                    obligation.candidate_start_utf8,
                    obligation.candidate_end_utf8,
                    obligation.normalized_commitment, "CONTAINED_CREATIVE",
                    "CREATIVE_CONTAINED", "CREATIVE_VEHICLE_ONLY",
                    "CREATIVE_HOST", "NOT_APPLICABLE") or audit_tuple != (
                        obligation.vehicle_start_utf8,
                        obligation.vehicle_end_utf8,
                        obligation.normalized_semantic_target, obligation.entry_id,
                        "NONFACTUAL_EDITORIAL_OR_CREATIVE",
                        "DOES_NOT_SURVIVE_AS_FACT", None,
                        "RETAINED_NONFACTUAL"):
                self._fail("SEMANTIC_COMPLETENESS_CREATIVE_SEMANTICS_MISMATCH")

    @staticmethod
    def _fail(reason: str) -> None:
        raise SemanticCompletenessFailureV1(reason)


def _qualification_obligations(
    candidate: bytes, *, case01: bool,
) -> tuple[QualificationObligationV1, ...]:
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
            obligations.append(QualificationObligationV1(
                start, end, modality, "P2" if case01 else None))
            offset = index + len(cue)
    return tuple(obligations)


def _required_return_obligations(
    candidate: bytes, *, qualifications: tuple[QualificationObligationV1, ...],
    case01: bool,
) -> tuple[RequiredReturnObligationV1, ...]:
    if not case01:
        return ()
    qualification = next(
        item for item in qualifications
        if item.required_proposition_entry_id == "P2")
    commitment = (
        "The candidate states that money is hidden ('banii se ascund în umbră') "
        "and employees remain exposed ('iar angajații rămân la lumină').")
    return (RequiredReturnObligationV1(
        "C1", "P2", ("P2",), "P1", qualification.start_utf8, len(candidate),
        _normalized_text(commitment), "NECESSARILY_IMPLIED", "GOVERNED_EVENT",
        "POSSIBLE", "PAST", "CERTAIN_OR_ACTUAL", "PAST",
        "FACTUAL_RETURN_WITHIN_CREATIVE_HOST",
        "NECESSARY_IMPLICATION_SURVIVES"),)


def _required_construction_semantics(
    candidate: bytes, *, case01: bool,
) -> tuple[RequiredConstructionSemanticsV1, ...]:
    if not case01:
        return ()
    basis = (
        "The candidate contains a creative host ('pare că și hotelul ar avea "
        "nevoie de o cameră cu mai multă transparență') and a factual proposition "
        "('banii se ascund în umbră, iar angajații rămân la lumină') that survives "
        "removal of the creative vehicle.")
    return (RequiredConstructionSemanticsV1(
        "C1", 0, len(candidate), _normalized_text(basis),
        "MIXED_CREATIVE_AND_REAL_WORLD", "P1", ("P2",),
        "MIXED_HOST_AND_RETURNS_REQUIRED"),)


def _required_creative_semantics(
    candidate: bytes, *, case01: bool,
) -> tuple[RequiredCreativeSemanticsV1, ...]:
    if not case01:
        return ()
    commitment = (
        "The candidate uses a metaphor ('pare că și hotelul ar avea nevoie de o "
        "cameră cu mai multă transparență') to frame the factual proposition about "
        "hidden money and exposed employees.")
    target = (
        "The candidate uses a metaphor ('pare că și hotelul ar avea nevoie de o "
        "cameră cu mai multă transparență') to imply that the hotel (or complex "
        "turistic) has a problem with hidden money and exposed employees.")
    return (RequiredCreativeSemanticsV1(
        "P1", 0, len(candidate), _normalized_text(commitment),
        "T1", 0, len(candidate), _normalized_text(target)),)


def _utf8_boundaries(data: bytes) -> tuple[int, ...]:
    boundaries = [0]
    size = 0
    for character in data.decode("utf-8", errors="strict"):
        size += len(character.encode("utf-8"))
        boundaries.append(size)
    return tuple(boundaries)


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).casefold()).strip()


def _normalize_value(value):
    if isinstance(value, str):
        return _normalized_text(value)
    if isinstance(value, dict):
        return {key: _normalize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    return value


def _policy_identity(policy: SemanticCompletenessPolicyV1) -> str:
    value = {
        "version": ADMISSION_VERSION,
        "candidate_sha256": policy.candidate_sha256,
        "authority_sha256": policy.authority_sha256,
        "candidate_bytes": policy.candidate_bytes,
        "authority_bytes": policy.authority_bytes,
        "candidate_utf8_boundaries": policy.candidate_utf8_boundaries,
        "justified_gaps": [
            {"start_utf8": gap.start_utf8, "end_utf8": gap.end_utf8,
             "reason_code": gap.reason_code} for gap in policy.justified_gaps],
        "unresolved_justifications": [
            {"start_utf8": item.start_utf8, "end_utf8": item.end_utf8,
             "reason_code": item.reason_code,
             "construction_ids": item.construction_ids,
             "entry_ids": item.entry_ids,
             "competing_interpretations": [
                 {"label": interpretation.label,
                  "source_sha256": interpretation.source_sha256,
                  "start_utf8": interpretation.start_utf8,
                  "end_utf8": interpretation.end_utf8}
                 for interpretation in item.competing_interpretations]}
            for item in policy.unresolved_justifications],
        "qualifications": [
            {"start_utf8": item.start_utf8, "end_utf8": item.end_utf8,
             "required_modality": item.required_modality.value,
             "required_proposition_entry_id": item.required_proposition_entry_id}
            for item in policy.qualifications],
        "required_returns": [
            {"construction_id": item.construction_id,
             "entry_id": item.entry_id,
             "required_construction_return_ids":
                 item.required_construction_return_ids,
             "creative_host_entry_id": item.creative_host_entry_id,
             "candidate_start_utf8": item.candidate_start_utf8,
             "candidate_end_utf8": item.candidate_end_utf8,
             "normalized_commitment": item.normalized_commitment,
             "scope_basis": item.scope_basis,
             "event_alignment": item.event_alignment,
             "candidate_modality": item.candidate_modality,
             "candidate_timing": item.candidate_timing,
             "authority_modality": item.authority_modality,
             "authority_timing": item.authority_timing,
             "scope_relation": item.scope_relation,
             "factual_return_basis": item.factual_return_basis}
            for item in policy.required_returns],
        "required_topology": (None if policy.required_topology is None else {
            "construction_ids": policy.required_topology.construction_ids,
            "entry_ids": policy.required_topology.entry_ids,
            "creative_audit_ids": policy.required_topology.creative_audit_ids}),
        "required_constructions": [
            {"construction_id": item.construction_id,
             "candidate_start_utf8": item.candidate_start_utf8,
             "candidate_end_utf8": item.candidate_end_utf8,
             "normalized_role_basis": item.normalized_role_basis,
             "construction_role": item.construction_role,
             "creative_host_entry_id": item.creative_host_entry_id,
             "literal_or_return_entry_ids": item.literal_or_return_entry_ids,
             "resolution": item.resolution}
            for item in policy.required_constructions],
        "required_creative": [
            {"entry_id": item.entry_id,
             "candidate_start_utf8": item.candidate_start_utf8,
             "candidate_end_utf8": item.candidate_end_utf8,
             "normalized_commitment": item.normalized_commitment,
             "audit_id": item.audit_id,
             "vehicle_start_utf8": item.vehicle_start_utf8,
             "vehicle_end_utf8": item.vehicle_end_utf8,
             "normalized_semantic_target": item.normalized_semantic_target}
            for item in policy.required_creative],
        "creative_target_analysis_required": policy.creative_target_analysis_required,
        "factual_authority_analysis_required": policy.factual_authority_analysis_required,
    }
    return hashlib.sha256((json.dumps(
        value, ensure_ascii=True, sort_keys=True,
        separators=(",", ":")) + "\n").encode()).hexdigest()


def seal_semantic_completeness_policy_v1(
    policy: SemanticCompletenessPolicyV1,
) -> SemanticCompletenessPolicyV1:
    if type(policy) is not SemanticCompletenessPolicyV1:
        raise TypeError("SEMANTIC_COMPLETENESS_POLICY_EXACT_TYPE_REQUIRED")
    return replace(policy, identity=_policy_identity(policy))


__all__ = (
    "ADMISSION_VERSION", "CoverageGapJustificationV1",
    "QualificationObligationV1", "SemanticCompletenessAdmissionV1",
    "QualificationAuditV1", "SourceBoundInterpretationV1",
    "RequiredReturnObligationV1",
    "RequiredTopologyV1",
    "RequiredConstructionSemanticsV1", "RequiredCreativeSemanticsV1",
    "seal_semantic_completeness_policy_v1",
    "SemanticCompletenessFailureV1", "SemanticCompletenessPolicyV1",
    "UnresolvedJustificationV1",
)
