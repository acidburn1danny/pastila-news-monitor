from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from .analysis import analyze_pair_v1
from .models import (
    CaptureMetadataV1,
    EditorialObservationV1,
    ExpressionEvidenceV1,
    OwnerClassificationV1,
    SnapshotV1,
)


class EvidenceStoreErrorV1(ValueError):
    pass


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _capture_id(metadata: CaptureMetadataV1, generated_sha: str) -> str:
    authority = f"{metadata.project_id}\0{metadata.component_id}\0{generated_sha}"
    return "editorial-capture-v1:" + hashlib.sha256(authority.encode()).hexdigest()


def _provenance(value: object, names: tuple[str, ...]) -> str | None:
    if isinstance(value, dict):
        for name in names:
            found = value.get(name)
            if isinstance(found, str) and found.strip():
                return found
        for child in value.values():
            if (found := _provenance(child, names)) is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            if (found := _provenance(child, names)) is not None:
                return found
    return None


class EditorialEvidenceStoreV1:
    """Separate owner-local append/update-by-governed-finalization evidence store."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def capture_generated(
        self,
        *,
        metadata: CaptureMetadataV1,
        text: str,
        captured_at: datetime | None = None,
    ) -> EditorialObservationV1:
        if not text.strip():
            raise EvidenceStoreErrorV1("generated snapshot missing")
        stamp = (captured_at or datetime.now(UTC)).isoformat()
        digest = _sha(text)
        capture_id = _capture_id(metadata, digest)
        existing = self.load(capture_id)
        if existing is not None:
            if existing.generated.sha256 != digest or existing.metadata != metadata:
                raise EvidenceStoreErrorV1("duplicate capture ID conflict")
            return existing
        observation = EditorialObservationV1(
            capture_id=capture_id,
            metadata=metadata,
            generated=SnapshotV1(captured_at=stamp, sha256=digest, text=text),
        )
        self._write(observation)
        return observation

    def capture_editor_output(
        self,
        *,
        path: Path,
        expected_payload_sha256: str,
        project_id: str,
        event_id: int,
    ) -> EditorialObservationV1:
        """Capture a successful governed Editor export without trusting mutable text."""
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
            if envelope.get("payload_sha256") != expected_payload_sha256:
                raise EvidenceStoreErrorV1("editor output identity mismatch")
            check = dict(envelope)
            check["payload_sha256"] = ""
            canonical = (
                json.dumps(
                    check,
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                + b"\n"
            )
            if (
                "sha256:" + hashlib.sha256(canonical).hexdigest()
                != expected_payload_sha256
            ):
                raise EvidenceStoreErrorV1("editor output hash mismatch")
            result = envelope["operational_result"]
            if result.get("status") != "completed":
                raise EvidenceStoreErrorV1("editor output incomplete")
            draft = result["draft"]
            text = draft.get("assembled_text") or draft.get("teleprompter_text")
            receipts = draft.get("usage_receipts") or ()
            tool_ids = sorted(
                {
                    identity
                    for receipt in receipts
                    for key, values in receipt.items()
                    if key.endswith("_ids_used")
                    for identity in values
                }
            )
            metadata = CaptureMetadataV1(
                project_id=project_id,
                event_id=event_id,
                component_id=f"story:event:{event_id}",
                provider=_provenance(result, ("provider", "provider_id")),
                model=_provenance(result, ("model_identifier", "model")),
                prompt_identity=result.get("execution_request_fingerprint"),
                policy_identity=result.get("preparation_result_fingerprint"),
                catalog_identity=next(
                    (
                        receipt.get("catalog_bundle_sha256")
                        for receipt in receipts
                        if receipt.get("catalog_bundle_sha256")
                    ),
                    None,
                ),
                retrieved_tool_ids=tuple(tool_ids),
                generation_attempt=result.get("attempt_count"),
            )
            return self.capture_generated(metadata=metadata, text=text)
        except EvidenceStoreErrorV1:
            raise
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
            AttributeError,
        ) as exc:
            raise EvidenceStoreErrorV1("editor output unavailable") from exc

    def finalize(
        self,
        capture_id: str,
        *,
        final_text: str,
        finalization_source: str,
        classifications: tuple[OwnerClassificationV1, ...] = (),
        finalized_at: datetime | None = None,
    ) -> EditorialObservationV1:
        current = self.require(capture_id)
        if not final_text.strip() or not finalization_source.strip():
            raise EvidenceStoreErrorV1("final snapshot missing")
        final_sha = _sha(final_text)
        if current.final is not None and current.final.sha256 == final_sha:
            return current
        if current.final is not None:
            raise EvidenceStoreErrorV1("capture already finalized")
        diff, kpi = analyze_pair_v1(
            current.generated.text,
            final_text,
            classifications,
            mechanism_available=current.metadata.mechanism_identity is not None,
        )
        evidence = self._expression_evidence(current, final_text)
        updated = current.model_copy(
            update={
                "final": SnapshotV1(
                    captured_at=(finalized_at or datetime.now(UTC)).isoformat(),
                    sha256=final_sha,
                    text=final_text,
                ),
                "finalization_source": finalization_source,
                "diff": diff,
                "classifications": classifications,
                "expression_evidence": evidence,
                "kpi": kpi,
            }
        )
        self._write(updated)
        return updated

    @staticmethod
    def _expression_evidence(
        current: EditorialObservationV1, final_text: str
    ) -> tuple[ExpressionEvidenceV1, ...]:
        """Use only catalog authority already tied to the generated receipt."""
        try:
            from pastila_scout.expression_retrieval_v1 import load_catalog_v1

            catalog = load_catalog_v1()
        except OSError, ValueError:
            return ()
        generated = current.generated.text.casefold()
        final = final_text.casefold()
        records = {
            item.expression_id: (item.preferred_surface or item.text)
            for item in catalog.expressions
        }
        records.update({item.term_id: item.term for item in catalog.controlled_terms})
        result = []
        for authority_id in current.metadata.retrieved_tool_ids:
            surface = records.get(authority_id)
            if not surface or surface.casefold() not in generated:
                continue
            outcome = "RETAINED" if surface.casefold() in final else "REMOVED"
            result.append(
                ExpressionEvidenceV1(
                    authority_id=authority_id,
                    generated_surface=surface,
                    outcome=outcome,
                )
            )
        return tuple(result)

    def correct_classifications(
        self, capture_id: str, classifications: tuple[OwnerClassificationV1, ...]
    ) -> EditorialObservationV1:
        current = self.require(capture_id)
        if current.final is None:
            raise EvidenceStoreErrorV1("capture not finalized")
        if any(item.diff_index >= len(current.diff) for item in classifications):
            raise EvidenceStoreErrorV1("classification index invalid")
        diff, kpi = analyze_pair_v1(
            current.generated.text,
            current.final.text,
            classifications,
            mechanism_available=current.metadata.mechanism_identity is not None,
        )
        updated = current.model_copy(
            update={"diff": diff, "classifications": classifications, "kpi": kpi}
        )
        self._write(updated)
        return updated

    def load(self, capture_id: str) -> EditorialObservationV1 | None:
        path = self._path(capture_id)
        if not path.exists():
            return None
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
            payload = envelope["observation"]
            canonical = json.dumps(
                payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            if envelope["sha256"] != _sha(canonical):
                raise EvidenceStoreErrorV1("evidence hash mismatch")
            value = EditorialObservationV1.model_validate_json(
                json.dumps(payload, ensure_ascii=False), strict=True
            )
            if (
                value.capture_id != capture_id
                or value.generated.sha256 != _sha(value.generated.text)
                or (value.final and value.final.sha256 != _sha(value.final.text))
            ):
                raise EvidenceStoreErrorV1("snapshot integrity mismatch")
            return value
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            if isinstance(exc, EvidenceStoreErrorV1):
                raise
            raise EvidenceStoreErrorV1("evidence corrupt") from exc

    def require(self, capture_id: str) -> EditorialObservationV1:
        value = self.load(capture_id)
        if value is None:
            raise EvidenceStoreErrorV1("capture missing")
        return value

    def list_valid(self) -> tuple[EditorialObservationV1, ...]:
        result = []
        for path in sorted(self.root.glob("*.json")) if self.root.exists() else ():
            try:
                result.append(self.require("editorial-capture-v1:" + path.stem))
            except EvidenceStoreErrorV1:
                continue
        return tuple(result)

    def delete(self, capture_id: str) -> bool:
        path = self._path(capture_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def reset(self) -> int:
        paths = tuple(self.root.glob("*.json")) if self.root.exists() else ()
        for path in paths:
            path.unlink()
        return len(paths)

    def _path(self, capture_id: str) -> Path:
        if not capture_id.startswith("editorial-capture-v1:") or any(
            char not in "0123456789abcdef" for char in capture_id.split(":", 1)[1]
        ):
            raise EvidenceStoreErrorV1("capture ID invalid")
        return self.root / f"{capture_id.split(':', 1)[1]}.json"

    def _write(self, value: EditorialObservationV1) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        payload = value.model_dump(mode="json")
        canonical = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        envelope = (
            json.dumps(
                {
                    "schema_version": 1,
                    "sha256": _sha(canonical),
                    "observation": payload,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )
        handle, temporary = tempfile.mkstemp(
            prefix=".editorial-evidence-", suffix=".tmp", dir=self.root
        )
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(envelope)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self._path(value.capture_id))
        except BaseException:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise
