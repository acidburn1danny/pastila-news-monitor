"""Canonical restart-safe persistence authority for one Voice V2 workspace."""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from pastila_scout.editor.generation.semantic_draft_v2 import (
    PastilaEditorSemanticDraftV2,
)
from pastila_scout.expression_catalog_v2.eligibility_models import (
    CommentaryRelationBinding,
    ExpressionEligibilityResultV1,
    ExpressionOwnerSelectionReceiptV1,
)
from pastila_scout.voice_eligibility_v2.models import (
    MechanicEligibilityClaimV1,
    VoiceEligibilityResultV1,
    VoiceOwnerSelectionReceiptV1,
    VoiceRepetitionSnapshotV1,
)
from pastila_scout.voice_executor_v2.models import (
    DeterministicTerminalKindV2,
    VoiceDeterministicExecutionRequestV2,
    VoiceDeterministicPreviewSidecarV2,
)
from pastila_scout.voice_fact_atoms_v2.models import VoiceFactAtomBundle
from pastila_scout.voice_fact_atoms_v2.persistence import (
    canonical_bytes,
    canonical_identity,
)
from pastila_scout.voice_repetition_v2 import finalize_order_authority_v1
from pastila_scout.voice_repetition_v2.models import (
    EpisodeOrderAuthorityV1,
    VoiceAcceptanceReceiptV1,
    VoiceRemovalReceiptV1,
)
from pastila_scout.voice_repetition_v2.persistence import (
    atomic_write,
    load_canonical,
    load_receipt,
)
from pastila_scout.voice_workflow_v2 import semantic_draft_revision_identity
from pastila_scout.voice_workflow_v2.models import VoiceStoryBindingV1

SHA = r"^sha256:[0-9a-f]{64}$"
ZERO = "sha256:" + "0" * 64


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CanonicalVoiceLifecycleV2(StrEnum):
    ELIGIBILITY_AVAILABLE = "eligibility_available"
    PROGRAM_SELECTED = "program_selected"
    EXPRESSION_SELECTED_OR_NONE = "expression_selected_or_none"
    PREVIEW_AVAILABLE = "preview_available"
    SAFE_ABSTENTION = "safe_abstention"
    ACCEPTED_COMMENTARY = "accepted_commentary"
    OWNER_REMOVED_COMMENTARY = "owner_removed_commentary"
    STALE_REEVALUATION_REQUIRED = "stale_reevaluation_required"
    INTEGRITY_FAILURE = "integrity_failure"


class CanonicalVoiceStoryStateV2(_Frozen):
    schema_name: Literal["pastilaacida-voice-canonical-story-state"] = (
        "pastilaacida-voice-canonical-story-state"
    )
    schema_version: Literal["2"] = "2"
    lifecycle: CanonicalVoiceLifecycleV2
    binding: VoiceStoryBindingV1
    authored_draft: PastilaEditorSemanticDraftV2
    fact_atom_bundle: VoiceFactAtomBundle
    mechanic_claims: tuple[MechanicEligibilityClaimV1, ...]
    relationship_bindings: tuple[CommentaryRelationBinding, ...] = ()
    repetition_snapshot: VoiceRepetitionSnapshotV1
    program_eligibility: VoiceEligibilityResultV1
    program_selection: VoiceOwnerSelectionReceiptV1 | None = None
    expression_eligibility: ExpressionEligibilityResultV1 | None = None
    expression_selection: ExpressionOwnerSelectionReceiptV1 | None = None
    execution_request: VoiceDeterministicExecutionRequestV2 | None = None
    preview: VoiceDeterministicPreviewSidecarV2 | None = None
    order_authority: EpisodeOrderAuthorityV1
    adjudication_state_identity: str | None = Field(default=None, pattern=SHA)
    fact_atom_receipt_identities: tuple[str, ...] = ()
    mechanic_claim_receipt_identities: tuple[str, ...] = ()
    activation_policy_identity: str | None = Field(default=None, pattern=SHA)
    acceptance_transaction_identity: str | None = Field(default=None, pattern=SHA)
    acceptance_receipt_identity: str | None = Field(default=None, pattern=SHA)
    removal_transaction_identity: str | None = Field(default=None, pattern=SHA)
    removal_receipt_identity: str | None = Field(default=None, pattern=SHA)
    stale_reason: str | None = None
    integrity_failure_code: str | None = None
    prior_state_identity: str | None = Field(default=None, pattern=SHA)
    state_identity: str = Field(default=ZERO, pattern=SHA)

    @model_validator(mode="after")
    def lifecycle_shape(self):
        if semantic_draft_revision_identity(self.authored_draft) != (
            self.binding.semantic_draft_revision_identity
        ) and self.lifecycle not in {
            CanonicalVoiceLifecycleV2.ACCEPTED_COMMENTARY,
            CanonicalVoiceLifecycleV2.OWNER_REMOVED_COMMENTARY,
        }:
            raise ValueError("authored draft and story binding differ")
        if (
            self.fact_atom_bundle.bundle_identity
            != self.program_eligibility.fact_atom_bundle_identity
        ):
            raise ValueError("eligibility and atom bundle differ")
        if (
            self.repetition_snapshot.snapshot_identity
            != self.program_eligibility.repetition_snapshot_identity
        ):
            raise ValueError("eligibility and repetition snapshot differ")
        selection_states = {
            CanonicalVoiceLifecycleV2.PROGRAM_SELECTED,
            CanonicalVoiceLifecycleV2.EXPRESSION_SELECTED_OR_NONE,
            CanonicalVoiceLifecycleV2.PREVIEW_AVAILABLE,
            CanonicalVoiceLifecycleV2.SAFE_ABSTENTION,
            CanonicalVoiceLifecycleV2.ACCEPTED_COMMENTARY,
        }
        if self.lifecycle in selection_states and self.program_selection is None:
            raise ValueError("program selection lifecycle mismatch")
        expression_states = selection_states - {
            CanonicalVoiceLifecycleV2.PROGRAM_SELECTED
        }
        if self.lifecycle in expression_states and (
            self.expression_eligibility is None or self.expression_selection is None
        ):
            raise ValueError("expression selection lifecycle mismatch")
        preview_states = {
            CanonicalVoiceLifecycleV2.PREVIEW_AVAILABLE,
            CanonicalVoiceLifecycleV2.SAFE_ABSTENTION,
            CanonicalVoiceLifecycleV2.ACCEPTED_COMMENTARY,
        }
        if self.lifecycle in preview_states and (
            self.execution_request is None or self.preview is None
        ):
            raise ValueError("preview lifecycle mismatch")
        if self.lifecycle is CanonicalVoiceLifecycleV2.SAFE_ABSTENTION and (
            self.preview is None
            or self.preview.terminal_result.kind
            is not DeterministicTerminalKindV2.SAFELY_ABSTAINED
        ):
            raise ValueError("safe abstention lacks abstained result")
        accepted = self.lifecycle is CanonicalVoiceLifecycleV2.ACCEPTED_COMMENTARY
        if accepted != bool(
            self.acceptance_transaction_identity and self.acceptance_receipt_identity
        ):
            raise ValueError("accepted lifecycle lacks atomic acceptance binding")
        removed = self.lifecycle is CanonicalVoiceLifecycleV2.OWNER_REMOVED_COMMENTARY
        if removed != bool(
            self.removal_transaction_identity and self.removal_receipt_identity
        ):
            raise ValueError("removal lifecycle mismatch")
        if (
            self.lifecycle is CanonicalVoiceLifecycleV2.STALE_REEVALUATION_REQUIRED
        ) != bool(self.stale_reason):
            raise ValueError("stale lifecycle mismatch")
        if (self.lifecycle is CanonicalVoiceLifecycleV2.INTEGRITY_FAILURE) != bool(
            self.integrity_failure_code
        ):
            raise ValueError("integrity lifecycle mismatch")
        return self


class CanonicalVoiceStoryPointerV2(_Frozen):
    schema_name: Literal["pastilaacida-voice-story-current-pointer"] = (
        "pastilaacida-voice-story-current-pointer"
    )
    schema_version: Literal["2"] = "2"
    event_id: int = Field(gt=0)
    state_identity: str = Field(pattern=SHA)
    state_relative_path: str = Field(min_length=1)
    acceptance_transaction_identity: str | None = Field(default=None, pattern=SHA)
    pointer_identity: str = Field(default=ZERO, pattern=SHA)


class CanonicalVoiceWorkspaceStateV2(_Frozen):
    schema_name: Literal["pastilaacida-voice-workspace-current-state"] = (
        "pastilaacida-voice-workspace-current-state"
    )
    schema_version: Literal["2"] = "2"
    project_identity: str = Field(min_length=1)
    order_authority: EpisodeOrderAuthorityV1
    story_pointer_identities: tuple[tuple[int, str], ...] = ()
    acceptance_root_relative_path: Literal["acceptance"] = "acceptance"
    state_identity: str = Field(default=ZERO, pattern=SHA)

    @model_validator(mode="after")
    def unique_stories(self):
        ids = [event_id for event_id, _ in self.story_pointer_identities]
        if (
            len(ids) != len(set(ids))
            or tuple(sorted(self.story_pointer_identities))
            != self.story_pointer_identities
        ):
            raise ValueError("workspace story pointers must be sorted and unique")
        return self


class CanonicalVoicePersistenceError(ValueError):
    pass


class UnknownCanonicalVoiceVersionError(CanonicalVoicePersistenceError):
    pass


def _seal(value, field: str):
    return value.model_copy(
        update={field: canonical_identity(value.model_copy(update={field: ZERO}))}
    )


def resolve_voice_workspace_root(project_path: Path) -> Path:
    if not project_path.is_absolute() or project_path.name in {"", ".", ".."}:
        raise CanonicalVoicePersistenceError("project path is not canonical")
    return project_path.parent / f"{project_path.name}.voice-v2"


class CanonicalVoiceWorkspaceStoreV2:
    def __init__(self, *, project_path: Path, project_identity: str):
        self.project_path = project_path
        self.project_identity = project_identity
        self.root = resolve_voice_workspace_root(project_path)
        self._acceptance_store = None

    @property
    def acceptance_store(self):
        """Load atomic acceptance authority only for acceptance operations."""
        if self._acceptance_store is None:
            from pastila_scout.voice_repetition_v2 import VoiceAtomicAcceptanceStoreV1

            self._acceptance_store = VoiceAtomicAcceptanceStoreV1(
                self.root / "acceptance"
            )
        return self._acceptance_store

    def _story_root(self, event_id: int) -> Path:
        if type(event_id) is not int or event_id <= 0:
            raise CanonicalVoicePersistenceError("invalid story identity")
        return self.root / "stories" / str(event_id)

    def _load_model(self, path: Path, model, name: str, version: str):
        try:
            raw = path.read_bytes()
            payload = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CanonicalVoicePersistenceError(
                "invalid canonical persistence"
            ) from exc
        if (
            not isinstance(payload, dict)
            or payload.get("schema_name") != name
            or payload.get("schema_version") != version
        ):
            raise UnknownCanonicalVoiceVersionError("unknown canonical Voice version")
        try:
            value = model.model_validate(payload)
        except ValidationError as exc:
            raise CanonicalVoicePersistenceError(
                "invalid canonical Voice structure"
            ) from exc
        if canonical_bytes(value) != raw:
            raise CanonicalVoicePersistenceError("noncanonical Voice persistence")
        return value

    def save_story(
        self, state: CanonicalVoiceStoryStateV2
    ) -> CanonicalVoiceStoryStateV2:
        if finalize_order_authority_v1(state.order_authority) != state.order_authority:
            raise CanonicalVoicePersistenceError("invalid story order authority")
        workspace = (
            self.load_workspace() if (self.root / "current.json").exists() else None
        )
        state = _seal(state, "state_identity")
        story_root = self._story_root(state.binding.event_id)
        revision = (
            story_root
            / "revisions"
            / f"{state.state_identity.removeprefix('sha256:')}.json"
        )
        atomic_write(revision, canonical_bytes(state))
        pointer = _seal(
            CanonicalVoiceStoryPointerV2(
                event_id=state.binding.event_id,
                state_identity=state.state_identity,
                state_relative_path=str(revision.relative_to(story_root)).replace(
                    "\\", "/"
                ),
                acceptance_transaction_identity=state.acceptance_transaction_identity,
            ),
            "pointer_identity",
        )
        atomic_write(story_root / "current.json", canonical_bytes(pointer))
        if workspace is not None:
            pointers = dict(workspace.story_pointer_identities)
            pointers[state.binding.event_id] = pointer.pointer_identity
            self.save_workspace(
                workspace.model_copy(
                    update={
                        "story_pointer_identities": tuple(sorted(pointers.items())),
                        "state_identity": ZERO,
                    }
                )
            )
        return state

    def load_story(self, event_id: int) -> CanonicalVoiceStoryStateV2 | None:
        story_root = self._story_root(event_id)
        pointer_path = story_root / "current.json"
        if not pointer_path.exists():
            return None
        pointer = self._load_model(
            pointer_path,
            CanonicalVoiceStoryPointerV2,
            "pastilaacida-voice-story-current-pointer",
            "2",
        )
        if (
            pointer.pointer_identity
            != _seal(pointer, "pointer_identity").pointer_identity
            or pointer.event_id != event_id
        ):
            raise CanonicalVoicePersistenceError("story pointer identity mismatch")
        relative = Path(pointer.state_relative_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise CanonicalVoicePersistenceError("unsafe story revision pointer")
        state = self._load_model(
            story_root / relative,
            CanonicalVoiceStoryStateV2,
            "pastilaacida-voice-canonical-story-state",
            "2",
        )
        if (
            state.state_identity != _seal(state, "state_identity").state_identity
            or state.state_identity != pointer.state_identity
            or state.binding.event_id != event_id
        ):
            raise CanonicalVoicePersistenceError("orphan story pointer")
        if (
            pointer.acceptance_transaction_identity
            != state.acceptance_transaction_identity
        ):
            raise CanonicalVoicePersistenceError("acceptance/story pointer mismatch")
        if state.lifecycle is CanonicalVoiceLifecycleV2.ACCEPTED_COMMENTARY:
            assert state.acceptance_transaction_identity is not None
            receipt = load_receipt(
                self.acceptance_store.transactions
                / state.acceptance_transaction_identity.removeprefix("sha256:")
                / "receipt.json"
            )
            if (
                receipt.transaction_identity != state.acceptance_transaction_identity
                or receipt.receipt_identity != state.acceptance_receipt_identity
                or semantic_draft_revision_identity(state.authored_draft)
                != receipt.resulting_semantic_draft_revision_identity
                or not any(
                    event.transaction_identity == receipt.transaction_identity
                    for event in self.acceptance_store.current_ledger().events
                )
            ):
                raise CanonicalVoicePersistenceError(
                    "atomic acceptance is not authoritative"
                )
        if state.lifecycle is CanonicalVoiceLifecycleV2.OWNER_REMOVED_COMMENTARY:
            assert state.removal_transaction_identity is not None
            receipt = load_canonical(
                self.acceptance_store.transactions
                / state.removal_transaction_identity.removeprefix("sha256:")
                / "receipt.json",
                VoiceRemovalReceiptV1,
                name="pastilaacida-voice-removal-receipt",
                version="1",
            )
            if (
                receipt.transaction_identity != state.removal_transaction_identity
                or receipt.receipt_identity != state.removal_receipt_identity
                or semantic_draft_revision_identity(state.authored_draft)
                != receipt.resulting_semantic_draft_revision_identity
                or not any(
                    event.transaction_identity == receipt.transaction_identity
                    for event in self.acceptance_store.current_ledger().events
                )
            ):
                raise CanonicalVoicePersistenceError(
                    "atomic removal is not authoritative"
                )
        return state

    def save_workspace(
        self, state: CanonicalVoiceWorkspaceStateV2
    ) -> CanonicalVoiceWorkspaceStateV2:
        if state.project_identity != self.project_identity:
            raise CanonicalVoicePersistenceError("workspace project identity mismatch")
        if finalize_order_authority_v1(state.order_authority) != state.order_authority:
            raise CanonicalVoicePersistenceError("invalid workspace order authority")
        state = _seal(state, "state_identity")
        revision = (
            self.root
            / "workspace-revisions"
            / f"{state.state_identity.removeprefix('sha256:')}.json"
        )
        atomic_write(revision, canonical_bytes(state))
        pointer = {
            "schema_name": "pastilaacida-voice-workspace-current-pointer",
            "schema_version": "1",
            "project_identity": self.project_identity,
            "state_identity": state.state_identity,
            "state_relative_path": str(revision.relative_to(self.root)).replace(
                "\\", "/"
            ),
        }
        pointer["pointer_identity"] = canonical_identity(pointer)
        atomic_write(
            self.root / "current.json",
            json.dumps(
                pointer, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            + b"\n",
        )
        return state

    def load_workspace(self) -> CanonicalVoiceWorkspaceStateV2 | None:
        pointer_path = self.root / "current.json"
        if not pointer_path.exists():
            return None
        try:
            pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CanonicalVoicePersistenceError("invalid workspace pointer") from exc
        identity = pointer.pop("pointer_identity", None)
        if (
            pointer.get("schema_name") != "pastilaacida-voice-workspace-current-pointer"
            or pointer.get("schema_version") != "1"
            or pointer.get("project_identity") != self.project_identity
            or identity != canonical_identity(pointer)
        ):
            raise CanonicalVoicePersistenceError("workspace pointer identity mismatch")
        relative = Path(pointer["state_relative_path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise CanonicalVoicePersistenceError("unsafe workspace pointer")
        state = self._load_model(
            self.root / relative,
            CanonicalVoiceWorkspaceStateV2,
            "pastilaacida-voice-workspace-current-state",
            "2",
        )
        if (
            state.state_identity != pointer["state_identity"]
            or state.state_identity != _seal(state, "state_identity").state_identity
        ):
            raise CanonicalVoicePersistenceError("orphan workspace pointer")
        for event_id, pointer_identity in state.story_pointer_identities:
            story_pointer = self._load_model(
                self._story_root(event_id) / "current.json",
                CanonicalVoiceStoryPointerV2,
                "pastilaacida-voice-story-current-pointer",
                "2",
            )
            if story_pointer.pointer_identity != pointer_identity:
                raise CanonicalVoicePersistenceError("workspace references stale story")
        return state

    def promote_acceptance(
        self, prior: CanonicalVoiceStoryStateV2, receipt: VoiceAcceptanceReceiptV1
    ) -> CanonicalVoiceStoryStateV2:
        current_receipt = self.acceptance_store.current_receipt()
        current_draft = self.acceptance_store.current_draft()
        if (
            current_receipt != receipt
            or current_draft is None
            or receipt.source_semantic_draft_revision_identity
            != prior.binding.semantic_draft_revision_identity
        ):
            raise CanonicalVoicePersistenceError(
                "acceptance transaction is not current"
            )
        promoted = prior.model_copy(
            update={
                "lifecycle": CanonicalVoiceLifecycleV2.ACCEPTED_COMMENTARY,
                "authored_draft": current_draft,
                "acceptance_transaction_identity": receipt.transaction_identity,
                "acceptance_receipt_identity": receipt.receipt_identity,
                "prior_state_identity": prior.state_identity,
                "state_identity": ZERO,
            }
        )
        return self.save_story(promoted)

    def promote_removal(
        self, prior: CanonicalVoiceStoryStateV2, receipt: VoiceRemovalReceiptV1
    ) -> CanonicalVoiceStoryStateV2:
        current_draft = self.acceptance_store.current_draft()
        persisted_receipt = load_canonical(
            self.acceptance_store.transactions
            / receipt.transaction_identity.removeprefix("sha256:")
            / "receipt.json",
            VoiceRemovalReceiptV1,
            name="pastilaacida-voice-removal-receipt",
            version="1",
        )
        if (
            persisted_receipt != receipt
            or current_draft is None
            or receipt.source_semantic_draft_revision_identity
            != semantic_draft_revision_identity(prior.authored_draft)
            or receipt.resulting_semantic_draft_revision_identity
            != semantic_draft_revision_identity(current_draft)
            or not any(
                event.transaction_identity == receipt.transaction_identity
                for event in self.acceptance_store.current_ledger().events
            )
        ):
            raise CanonicalVoicePersistenceError("removal transaction is not current")
        promoted = prior.model_copy(
            update={
                "lifecycle": CanonicalVoiceLifecycleV2.OWNER_REMOVED_COMMENTARY,
                "authored_draft": current_draft,
                "acceptance_transaction_identity": None,
                "acceptance_receipt_identity": None,
                "removal_transaction_identity": receipt.transaction_identity,
                "removal_receipt_identity": receipt.receipt_identity,
                "prior_state_identity": prior.state_identity,
                "state_identity": ZERO,
            }
        )
        return self.save_story(promoted)


__all__ = [
    "CanonicalVoiceLifecycleV2",
    "CanonicalVoicePersistenceError",
    "CanonicalVoiceStoryPointerV2",
    "CanonicalVoiceStoryStateV2",
    "CanonicalVoiceWorkspaceStateV2",
    "CanonicalVoiceWorkspaceStoreV2",
    "UnknownCanonicalVoiceVersionError",
    "resolve_voice_workspace_root",
]
