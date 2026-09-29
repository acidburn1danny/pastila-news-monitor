"""Canonical SourcePacket -> R2 invocation receipt -> EditorDraft vertical slice."""
from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .vnext_foundation_v1 import (
    BoundaryError,
    atomic_json,
    object_identity,
    sha256_bytes,
)
from .vnext_r2_consolidation_binding_v1 import EXPECTED_LOCK_IDENTITY, verify_closure
from .vnext_scout_production_v1 import validate_scout_packet
from .vnext_state_sqlite_v1 import SQLiteStateStore
from .vnext_workflow_v1 import TransitionRequest

R2_IDENTITIES = {
    "adapter_flat_identity": "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02",
    "base_model_flat_identity": "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39",
    "checkpoint_identity": "96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be",
    "tokenizer_flat_identity": "026c7803af845d166451a8845defbc359cfda96d2d33c56d9648dcc8c117d1b2",
    "tokenizer_json_sha256": "d5f6046775b112f0e2d456ee9dba450684ab964fe5c4e231599bdc6773028135",
}
PROMPT = {
    "system": "Ești EDITOR factual. SourcePacket este singura autoritate factuală. Produce un setup factual sigur, concis și util pentru VOICE. Nu introduce comentariu, sarcasm sau informații noi.",
    "user_template": "Transformă exclusiv sursele de mai jos într-un setup factual, uzual 2–3 propoziții și mai lung numai când factualitatea o cere. Păstrează actorii, cifrele, atribuirea, modalitatea și statutul procedural. Returnează numai JSON: {\"case_id\":\"{event_id}\",\"text\":\"...\"}.\nSURSE:\n{sources}",
}
DECODING = {"do_sample": False, "max_new_tokens": 256, "num_beams": 1, "use_cache": True}
RUNTIME = {
    "loader": "AutoModelForImageTextToText", "adapter_loader": "PeftModel",
    "local_files_only": True, "fix_mistral_regex": True,
    "quantization": "BNB_NF4_DOUBLE_BFLOAT16", "attention": "sdpa",
}
PROMPT_IDENTITY = object_identity(PROMPT)
DECODING_IDENTITY = object_identity(DECODING)
RUNTIME_IDENTITY = object_identity(RUNTIME)
_SHA256 = re.compile(r"[0-9a-f]{64}")


class EditorVerticalSliceError(BoundaryError):
    pass


@dataclass(frozen=True)
class GenerationEvidence:
    rendered_prompt: str
    input_token_ids: tuple[int, ...]
    raw_output: bytes
    eos_token_id: int
    pad_token_id: int
    chat_template_sha256: str


class R2Backend(Protocol):
    r2_lock_identity: str

    def generate(self, messages: Sequence[Mapping[str, str]], decoding: Mapping[str, object]) -> GenerationEvidence: ...


def _pairs_without_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise EditorVerticalSliceError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def editor_messages(packet: Mapping[str, object]) -> tuple[dict[str, str], dict[str, str]]:
    spans = validate_scout_packet(packet)
    source = "\n".join(f"[{span['span_id']}] {span['text']}" for span in spans)
    user = PROMPT["user_template"].replace("{event_id}", str(packet["event_identity"])).replace("{sources}", source)
    return ({"role": "system", "content": PROMPT["system"]}, {"role": "user", "content": user})


def parse_r2_output(raw_output: bytes, event_id: str) -> str:
    try:
        value = json.loads(raw_output.decode("utf-8"), object_pairs_hook=_pairs_without_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EditorVerticalSliceError("R2 output is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict) or set(value) != {"case_id", "text"}:
        raise EditorVerticalSliceError("R2 output must contain exactly case_id and text")
    if value["case_id"] != event_id:
        raise EditorVerticalSliceError("R2 case_id does not match SourcePacket event_identity")
    text = value["text"]
    if not isinstance(text, str) or not text.strip():
        raise EditorVerticalSliceError("R2 text must be a non-empty string")
    return text.strip()


def run_editor_vertical_slice(packet: Mapping[str, object], backend: R2Backend) -> tuple[dict[str, object], dict[str, object]]:
    messages = editor_messages(packet)
    if backend.r2_lock_identity != EXPECTED_LOCK_IDENTITY:
        raise EditorVerticalSliceError("backend is not bound to the verified R2 closure")
    evidence = backend.generate(messages, DECODING)
    if not evidence.rendered_prompt or not evidence.input_token_ids or not evidence.raw_output:
        raise EditorVerticalSliceError("incomplete R2 generation evidence")
    if any(type(value) is not int or value < 0 for value in evidence.input_token_ids):
        raise EditorVerticalSliceError("invalid input token IDs")
    if evidence.eos_token_id < 0 or evidence.pad_token_id < 0:
        raise EditorVerticalSliceError("invalid resolved special token IDs")
    text = parse_r2_output(evidence.raw_output, str(packet["event_identity"]))
    invocation: dict[str, object] = {
        "schema": "vnext-r2-editor-invocation-receipt", "schema_version": 1,
        "source_packet_identity": packet["packet_identity"],
        "r2_lock_identity": EXPECTED_LOCK_IDENTITY, "r2_identities": dict(R2_IDENTITIES),
        "prompt_identity": PROMPT_IDENTITY, "messages_identity": object_identity(messages),
        "rendered_prompt_sha256": sha256_bytes(evidence.rendered_prompt.encode("utf-8")),
        "input_token_ids_identity": object_identity(list(evidence.input_token_ids)),
        "chat_template_sha256": evidence.chat_template_sha256,
        "decoding": dict(DECODING), "decoding_identity": DECODING_IDENTITY,
        "resolved_special_tokens": {"eos_token_id": evidence.eos_token_id, "pad_token_id": evidence.pad_token_id},
        "runtime_identity": RUNTIME_IDENTITY, "raw_output_sha256": sha256_bytes(evidence.raw_output),
        "parsed_text_sha256": sha256_bytes(text.encode("utf-8")),
        "model_loaded": True, "inference_performed": True,
        "optimizer_created": False, "training_performed": False,
    }
    invocation["receipt_identity"] = object_identity(invocation)
    draft: dict[str, object] = {
        "schema": "vnext-editor-draft", "schema_version": 1, "artifact_kind": "EDITOR_DRAFT",
        "event_identity": packet["event_identity"], "source_packet_identity": packet["packet_identity"],
        "invocation_receipt_identity": invocation["receipt_identity"],
        "raw_output_sha256": invocation["raw_output_sha256"], "text": text,
        "structural_status": "PASS", "factual_acceptance_status": "NOT_EVALUATED",
        "eligible_as_accepted_setup": False, "eligible_for_voice": False,
    }
    draft["draft_identity"] = object_identity(draft)
    validate_editor_draft(draft, source_packet=packet, invocation_receipt=invocation)
    return invocation, draft


def validate_editor_draft(
    draft: Mapping[str, object], *, source_packet: Mapping[str, object], invocation_receipt: Mapping[str, object]
) -> None:
    validate_scout_packet(source_packet)
    if draft.get("schema") != "vnext-editor-draft" or draft.get("artifact_kind") != "EDITOR_DRAFT":
        raise EditorVerticalSliceError("EditorDraft schema/kind mismatch")
    if draft.get("source_packet_identity") != source_packet.get("packet_identity"):
        raise EditorVerticalSliceError("EditorDraft SourcePacket binding mismatch")
    receipt_identity = invocation_receipt.get("receipt_identity")
    required_receipt = {
        "schema", "schema_version", "source_packet_identity", "r2_lock_identity", "r2_identities",
        "prompt_identity", "messages_identity", "rendered_prompt_sha256", "input_token_ids_identity",
        "chat_template_sha256", "decoding", "decoding_identity", "resolved_special_tokens",
        "runtime_identity", "raw_output_sha256", "parsed_text_sha256", "model_loaded", "inference_performed",
        "optimizer_created", "training_performed", "receipt_identity",
    }
    if set(invocation_receipt) != required_receipt or invocation_receipt.get("schema") != "vnext-r2-editor-invocation-receipt" or invocation_receipt.get("schema_version") != 1:
        raise EditorVerticalSliceError("invocation receipt schema mismatch")
    semantic_receipt = {key: value for key, value in invocation_receipt.items() if key != "receipt_identity"}
    if receipt_identity != object_identity(semantic_receipt) or draft.get("invocation_receipt_identity") != receipt_identity:
        raise EditorVerticalSliceError("EditorDraft invocation binding mismatch")
    if invocation_receipt.get("r2_lock_identity") != EXPECTED_LOCK_IDENTITY or invocation_receipt.get("r2_identities") != R2_IDENTITIES:
        raise EditorVerticalSliceError("R2 identity drift")
    if invocation_receipt.get("prompt_identity") != PROMPT_IDENTITY or invocation_receipt.get("decoding_identity") != DECODING_IDENTITY or invocation_receipt.get("runtime_identity") != RUNTIME_IDENTITY:
        raise EditorVerticalSliceError("R2 invocation contract drift")
    if invocation_receipt.get("source_packet_identity") != source_packet.get("packet_identity") or invocation_receipt.get("messages_identity") != object_identity(editor_messages(source_packet)):
        raise EditorVerticalSliceError("R2 input provenance drift")
    for key in ("rendered_prompt_sha256", "input_token_ids_identity", "chat_template_sha256", "raw_output_sha256"):
        if not isinstance(invocation_receipt.get(key), str) or _SHA256.fullmatch(str(invocation_receipt[key])) is None:
            raise EditorVerticalSliceError(f"invalid invocation identity: {key}")
    if draft.get("raw_output_sha256") != invocation_receipt.get("raw_output_sha256"):
        raise EditorVerticalSliceError("EditorDraft output binding mismatch")
    if invocation_receipt.get("parsed_text_sha256") != sha256_bytes(str(draft.get("text", "")).encode("utf-8")):
        raise EditorVerticalSliceError("EditorDraft parsed-text binding mismatch")
    if draft.get("factual_acceptance_status") != "NOT_EVALUATED" or draft.get("eligible_as_accepted_setup") is not False or draft.get("eligible_for_voice") is not False:
        raise EditorVerticalSliceError("EditorDraft crossed eligibility boundary")
    semantic_draft = {key: value for key, value in draft.items() if key != "draft_identity"}
    if draft.get("draft_identity") != object_identity(semantic_draft):
        raise EditorVerticalSliceError("EditorDraft identity mismatch")


def build_structural_failure(
    packet: Mapping[str, object], *, failure_code: str, evidence_identity: str,
) -> dict[str, object]:
    """Create bounded evidence for the review-gated structural recovery path."""
    validate_scout_packet(packet)
    if not failure_code or _SHA256.fullmatch(evidence_identity) is None:
        raise EditorVerticalSliceError("invalid structural failure evidence")
    failure: dict[str, object] = {
        "schema": "vnext-editor-structural-failure", "schema_version": 1,
        "artifact_kind": "STRUCTURAL_FAILURE",
        "event_identity": packet["event_identity"],
        "source_packet_identity": packet["packet_identity"],
        "failure_code": failure_code,
        "evidence_identity": evidence_identity,
        "eligible_as_accepted_setup": False,
        "eligible_for_voice": False,
    }
    failure["failure_identity"] = object_identity(failure)
    return failure


def validate_structural_failure(failure: Mapping[str, object], *, packet: Mapping[str, object]) -> None:
    validate_scout_packet(packet)
    if failure.get("schema") != "vnext-editor-structural-failure" or failure.get("schema_version") != 1 or failure.get("artifact_kind") != "STRUCTURAL_FAILURE":
        raise EditorVerticalSliceError("structural failure schema mismatch")
    if failure.get("source_packet_identity") != packet.get("packet_identity") or failure.get("event_identity") != packet.get("event_identity"):
        raise EditorVerticalSliceError("structural failure source binding mismatch")
    if not isinstance(failure.get("failure_code"), str) or not failure["failure_code"] or _SHA256.fullmatch(str(failure.get("evidence_identity"))) is None:
        raise EditorVerticalSliceError("invalid structural failure evidence")
    if failure.get("eligible_as_accepted_setup") is not False or failure.get("eligible_for_voice") is not False:
        raise EditorVerticalSliceError("structural failure crossed eligibility boundary")
    semantic = {key: value for key, value in failure.items() if key != "failure_identity"}
    if failure.get("failure_identity") != object_identity(semantic):
        raise EditorVerticalSliceError("structural failure identity mismatch")


def persist_editor_draft(
    store: SQLiteStateStore, *, workflow_identity: str, packet: Mapping[str, object],
    invocation: Mapping[str, object], draft: Mapping[str, object], observed_at: str,
    retry_authorization_identity: str | None = None,
) -> None:
    validate_editor_draft(draft, source_packet=packet, invocation_receipt=invocation)
    state = store.load_workflow(workflow_identity)["state"]
    if state == "SOURCE_PACKET_READY":
        store.transition(_transition(workflow_identity, "editor-start", "SOURCE_PACKET_READY", "EDITOR_PENDING", str(packet["packet_identity"]), None, observed_at))
    elif state != "EDITOR_PENDING":
        raise EditorVerticalSliceError(f"workflow is not ready to persist EditorDraft: {state}")
    relative = Path("blobs/editor-drafts") / f"{draft['draft_identity']}.json"
    receipt_relative = Path("blobs/editor-invocations") / f"{invocation['receipt_identity']}.json"
    receipt_path = store.root / receipt_relative
    path = store.root / relative
    if receipt_path.exists():
        if json.loads(receipt_path.read_text(encoding="utf-8")) != invocation:
            raise EditorVerticalSliceError("immutable invocation receipt conflict")
    else:
        atomic_json(receipt_path, dict(invocation), root=store.root, overwrite=False)
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != draft:
            raise EditorVerticalSliceError("immutable EditorDraft conflict")
    else:
        atomic_json(path, dict(draft), root=store.root, overwrite=False)

    transition_input = str(invocation["receipt_identity"])
    if retry_authorization_identity is not None:
        if _SHA256.fullmatch(retry_authorization_identity) is None:
            raise EditorVerticalSliceError("invalid retry authorization identity")
        retry_receipt: dict[str, object] = {
            "schema": "vnext-editor-retry-authorization-receipt",
            "schema_version": 1,
            "workflow_identity": workflow_identity,
            "source_packet_identity": packet["packet_identity"],
            "invocation_receipt_identity": invocation["receipt_identity"],
            "authorization_identity": retry_authorization_identity,
        }
        retry_receipt["receipt_identity"] = object_identity(retry_receipt)
        retry_relative = Path("blobs/editor-retry-authorizations") / f"{retry_receipt['receipt_identity']}.json"
        retry_path = store.root / retry_relative
        if retry_path.exists():
            if json.loads(retry_path.read_text(encoding="utf-8")) != retry_receipt:
                raise EditorVerticalSliceError("immutable retry authorization conflict")
        else:
            atomic_json(retry_path, retry_receipt, root=store.root, overwrite=False)
        transition_input = str(retry_receipt["receipt_identity"])

    def insert_artifact(connection: object) -> None:
        connection.execute(
            "INSERT INTO workflow_artifacts VALUES(?,?,?,?,?,?)",
            (draft["draft_identity"], workflow_identity, "EDITOR_DRAFT", draft["draft_identity"], relative.as_posix(), "vnext-editor-draft-v1"),
        )

    store.transition(
        _transition(workflow_identity, "editor-draft", "EDITOR_PENDING", "EDITOR_DRAFT_READY", transition_input, str(draft["draft_identity"]), observed_at),
        before_commit=insert_artifact,
    )
    store.transition(_transition(workflow_identity, "editor-structural-pass", "EDITOR_DRAFT_READY", "FACTUAL_REVIEW_PENDING", str(draft["draft_identity"]), str(draft["draft_identity"]), observed_at))


def persist_structural_failure(
    store: SQLiteStateStore, *, workflow_identity: str, packet: Mapping[str, object],
    failure: Mapping[str, object], observed_at: str,
) -> None:
    """Persist a non-eligible failure and route it through factual review."""
    validate_structural_failure(failure, packet=packet)
    state = store.load_workflow(workflow_identity)["state"]
    if state == "SOURCE_PACKET_READY":
        store.transition(_transition(workflow_identity, "editor-start", "SOURCE_PACKET_READY", "EDITOR_PENDING", str(packet["packet_identity"]), None, observed_at))
    elif state != "EDITOR_PENDING":
        raise EditorVerticalSliceError(f"workflow is not ready to persist structural failure: {state}")
    relative = Path("blobs/editor-failures") / f"{failure['failure_identity']}.json"
    path = store.root / relative
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != failure:
            raise EditorVerticalSliceError("immutable structural failure conflict")
    else:
        atomic_json(path, dict(failure), root=store.root, overwrite=False)

    def insert_artifact(connection: object) -> None:
        connection.execute(
            "INSERT INTO workflow_artifacts VALUES(?,?,?,?,?,?)",
            (failure["failure_identity"], workflow_identity, "STRUCTURAL_FAILURE", failure["failure_identity"], relative.as_posix(), "vnext-editor-structural-failure-v1"),
        )

    store.transition(
        _transition(workflow_identity, "editor-structural-fail", "EDITOR_PENDING", "STRUCTURAL_FAIL", str(packet["packet_identity"]), str(failure["failure_identity"]), observed_at),
        before_commit=insert_artifact,
    )
    store.transition(
        _transition(workflow_identity, "editor-failure-review", "STRUCTURAL_FAIL", "FACTUAL_REVIEW_PENDING", str(failure["failure_identity"]), str(failure["failure_identity"]), observed_at)
    )


def _transition(workflow: str, operation: str, previous: str, resulting: str, input_id: str, output_id: str | None, observed_at: str) -> TransitionRequest:
    semantic = {"workflow": workflow, "operation": operation, "previous": previous, "resulting": resulting, "input": input_id, "output": output_id}
    identity = object_identity(semantic)
    return TransitionRequest(
        workflow, f"editor:{operation}", previous, resulting, "EDITOR", "PASS", input_id,
        output_id, f"attempt:{identity}", f"idempotency:{identity}", observed_at,
        {"component": "VNext Critical-Path Authority Repair & EDITOR Vertical Slice v1"},
    )


class TransformersR2Backend:
    """Adapter over an already loaded, byte-verified R2 model and tokenizer."""

    r2_lock_identity = EXPECTED_LOCK_IDENTITY

    def __init__(self, model: object, tokenizer: object):
        self.model = model
        self.tokenizer = tokenizer

    @classmethod
    def load_verified(cls, closure_root: Path) -> TransformersR2Backend:
        """Verify all R2 bytes, then load only the frozen closure in inference mode."""
        verify_closure(closure_root, verify_bytes=True)
        import torch
        from peft import PeftModel
        from transformers import (
            AutoModelForImageTextToText,
            AutoTokenizer,
            BitsAndBytesConfig,
        )

        lock = json.loads((closure_root / "dependency-lock.json").read_text(encoding="utf-8"))
        layout = lock["layout"]
        tokenizer = AutoTokenizer.from_pretrained(
            closure_root / layout["tokenizer"], local_files_only=True, fix_mistral_regex=True,
        )
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
        quantization = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
        base = AutoModelForImageTextToText.from_pretrained(
            closure_root / layout["base_model"], local_files_only=True, device_map={"": 0},
            dtype=torch.bfloat16, attn_implementation="sdpa", low_cpu_mem_usage=True,
            quantization_config=quantization,
        )
        if hasattr(base.model, "vision_tower"):
            base.model.vision_tower = None
        if hasattr(base.model, "multi_modal_projector"):
            base.model.multi_modal_projector = None
        model = PeftModel.from_pretrained(base, closure_root / layout["adapter"], is_trainable=False)
        model.eval()
        return cls(model, tokenizer)

    def generate(self, messages: Sequence[Mapping[str, str]], decoding: Mapping[str, object]) -> GenerationEvidence:
        import torch

        rendered = self.tokenizer.apply_chat_template(list(messages), tokenize=False, add_generation_prompt=True)
        encoded = self.tokenizer(rendered, return_tensors="pt").to(self.model.device)
        input_ids = tuple(int(value) for value in encoded.input_ids[0].tolist())
        eos = self.tokenizer.eos_token_id
        pad = self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else eos
        if eos is None or pad is None:
            raise EditorVerticalSliceError("tokenizer special tokens unavailable")
        with torch.inference_mode():
            generated = self.model.generate(
                **encoded, do_sample=decoding["do_sample"], num_beams=decoding["num_beams"],
                max_new_tokens=decoding["max_new_tokens"], use_cache=decoding["use_cache"],
                eos_token_id=eos, pad_token_id=pad,
            )
        raw = self.tokenizer.decode(generated[0, len(input_ids):], skip_special_tokens=True).strip().encode("utf-8")
        template = self.tokenizer.chat_template or ""
        return GenerationEvidence(rendered, input_ids, raw, int(eos), int(pad), sha256_bytes(template.encode("utf-8")))
