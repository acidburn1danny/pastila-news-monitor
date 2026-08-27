"""Canonical persistence for explicit expression selection or omission receipts."""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import ValidationError

from pastila_scout.voice_fact_atoms_v2.persistence import canonical_bytes

from .eligibility import ExpressionEligibilityIntegrityError, _sealed
from .eligibility_models import ExpressionOwnerSelectionReceiptV1


class UnknownExpressionSelectionReceiptVersionError(ValueError):
    pass


class ExpressionSelectionReceiptStoreV1:
    def __init__(self, path: Path):
        self.path = path

    def save(self, receipt: ExpressionOwnerSelectionReceiptV1) -> None:
        if receipt.receipt_identity != _sealed(receipt, "receipt_identity"):
            raise ExpressionEligibilityIntegrityError("receipt identity mismatch")
        raw = canonical_bytes(receipt)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with temporary.open("wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def load(self) -> ExpressionOwnerSelectionReceiptV1:
        raw = self.path.read_bytes()
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExpressionEligibilityIntegrityError(
                "invalid selection receipt JSON"
            ) from exc
        if (
            not isinstance(value, dict)
            or value.get("schema_name")
            != "pastilaacida-voice-expression-owner-selection-receipt"
            or value.get("schema_version") != "1"
        ):
            raise UnknownExpressionSelectionReceiptVersionError(
                "unsupported expression selection receipt version"
            )
        try:
            receipt = ExpressionOwnerSelectionReceiptV1.model_validate(value)
        except ValidationError as exc:
            raise ExpressionEligibilityIntegrityError(
                "invalid expression selection receipt"
            ) from exc
        if canonical_bytes(receipt) != raw:
            raise ExpressionEligibilityIntegrityError(
                "selection receipt is not canonical"
            )
        if receipt.receipt_identity != _sealed(receipt, "receipt_identity"):
            raise ExpressionEligibilityIntegrityError("receipt identity mismatch")
        return receipt


__all__ = [
    "ExpressionSelectionReceiptStoreV1",
    "UnknownExpressionSelectionReceiptVersionError",
]
