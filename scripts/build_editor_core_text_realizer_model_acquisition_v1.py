"""Build the bounded metadata-only acquisition authority for two Qwen snapshots."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
PREFIX = "editor-core-text-realizer-model-acquisition-v1"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identified(value: dict, key: str) -> dict:
    return {**value, key: sha(canonical(value))}


def write(name: str, value: dict) -> None:
    (ART / name).write_bytes((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))


def file(name: str, size: int, oid: str, lfs_sha256: str | None = None) -> dict:
    return {"path": name, "size": size, "git_oid": oid, "sha256": lfs_sha256}


models = [
    {
        "candidate_id": "C1_QWEN3_8B", "repo_id": "Qwen/Qwen3-8B",
        "revision": "b968826d9c46dd6066d109eabc6255188de91218", "license": "apache-2.0",
        "files": [
            file(".gitattributes",1570,"52373fe24473b1aa44333d318f578ae6bf04b49b"), file("LICENSE",11343,"6634c8cc3133b3848ec74b9f275acaaa1ea618ab"),
            file("README.md",16660,"ecc3ebd0849aa08d9484bd911dddfd5261b10d30"), file("config.json",728,"d46195ac87f837ad233d02b2f80f148bf7c005e0"),
            file("generation_config.json",239,"20a8a9156fc8c3f25295ca067f61fdf120d517c5"), file("merges.txt",1671853,"31349551d90c7606f325fe0f11bbb8bd5fa0d7c7"),
            file("model-00001-of-00005.safetensors",3996250744,"8d46cf470aff053c27fd6d956d4d69af9460bd2a","31d6a825ae35f11fb85b195b4c42c146c051e446433125a215336abdf95cbf5f"),
            file("model-00002-of-00005.safetensors",3993160032,"e726a2bcb3b100cba7ae899689cc029d8a08b20c","5991236cea6fe21f3d43cab0f0e84448734fbbe0789816202989f2ddc9d18282"),
            file("model-00003-of-00005.safetensors",3959604768,"c94db38adbcb837246c797986365b8e4603ef3ac","c5185c4794be2d8a9784d5753c9922db38df478ce11f9ed0b415b7304d896836"),
            file("model-00004-of-00005.safetensors",3187841392,"a6c92dd09e29e1f72271e087f89ee033b321101c","b5ee7de71fbf17db3d5704e0c8f2bc7d005ca9e1d7ca2aeb19827b0cfcaa917a"),
            file("model-00005-of-00005.safetensors",1244659840,"7bbb0cbc623d70925a3a82b301a99cb52ac9ed5b","20c2d6366ab85c90786ccdd829cd2b9e7d30ef3b2ebbb998280e7e4014b542ff"),
            file("model.safetensors.index.json",32878,"2b85c00f1b118961cd7a477e2bba0fe197a4ce1a"),
            file("tokenizer.json",11422654,"cd71f61a15a522601badb3dc960d800d9cb3766c","aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4"),
            file("tokenizer_config.json",9732,"417d038a63fa3de29cfde265caedae14d1a58d92"), file("vocab.json",2776833,"4783fe10ac3adce15ac8f358ef5462739852c569"),
        ],
    },
    {
        "candidate_id": "C2_QWEN25_7B", "repo_id": "Qwen/Qwen2.5-7B-Instruct",
        "revision": "a09a35458c702b33eeacc393d103063234e8bc28", "license": "apache-2.0",
        "files": [
            file(".gitattributes",1519,"a6344aac8c09253b3b630fb776ae94478aa0275b"), file("LICENSE",11343,"6634c8cc3133b3848ec74b9f275acaaa1ea618ab"),
            file("README.md",6240,"4e9536cebaeb5cac673952ad5d0eeae469900f81"), file("config.json",663,"0178295f88afc3c7f279ed284f961f8c1be00654"),
            file("generation_config.json",243,"0eb3c536657dcd12626e09eca4b6198c0cbcde1e"), file("merges.txt",1671839,"20024bfe7c83998e9aeaf98a0cd6a2ce6306c2f0"),
            file("model-00001-of-00004.safetensors",3945441440,"5e68dcea92e3696ddd4e1d44d9b420a31fe5622c","a1333e6293854747c481288ea83b348226af178dd565c49b6f9495ba1966aba7"),
            file("model-00002-of-00004.safetensors",3864726352,"e07e23d4595678a717aaad11eef9bc22056c284a","f5d25a2772cb825164a2a2c0fb6d51a87e282abf21e4dd75bc5cfb3cd0ea6185"),
            file("model-00003-of-00004.safetensors",3864726424,"114c07bb791bac8d2b32109b7729ef2f9a489dfe","8efdec4c1bc12317ae1a38dc42b595ce777738a64deea3fcb8a0a91381bcdfd5"),
            file("model-00004-of-00004.safetensors",3556377672,"f4841c787f178938010ce784a3ec99e5568524b5","1a72d403cdf0c1ec3cb7f289f17b394a01e64394c2e9b3c0f94dbce3faf879bd"),
            file("model.safetensors.index.json",27752,"14d037fdda5a1311dcc0275003a7a370d84114e6"), file("tokenizer.json",7031645,"443909a61d429dff23010e5bddd28ff530edda00"),
            file("tokenizer_config.json",7305,"07bfe0640cb5a0037f9322287fbfc682806cf672"), file("vocab.json",2776833,"4783fe10ac3adce15ac8f358ef5462739852c569"),
        ],
    },
]

for model in models:
    model["total_bytes"] = sum(item["size"] for item in model["files"])
    core = {key: value for key, value in model.items() if key != "snapshot_identity"}
    model["snapshot_identity"] = sha(canonical(core))
    model["content_addressed_root"] = f"/root/pf9-editor-model-store/sha256/{model['snapshot_identity']}"

snapshots = identified({
    "schema": "editor-text-realizer-model-snapshots", "schema_version": 1,
    "metadata_source": "OFFICIAL_HUGGING_FACE_API_AND_GIT_HEAD", "models": models,
    "aggregate_bytes": sum(model["total_bytes"] for model in models),
}, "snapshots_identity")

quantization = identified({
    "schema": "editor-text-realizer-quantization-recipe", "schema_version": 1,
    "applies_to": ["C1_QWEN3_8B", "C2_QWEN25_7B"], "backend": "bitsandbytes", "bits": 4,
    "load_in_4bit": True, "bnb_4bit_quant_type": "nf4", "bnb_4bit_use_double_quant": True,
    "bnb_4bit_compute_dtype": "bfloat16", "device_map": "cuda:0", "persist_quantized_weights": False,
    "runtime_versions": {"transformers": "5.15.0", "torch": "2.13.0+cu130", "bitsandbytes": "0.50.1", "accelerate": "1.14.0"},
    "maximum_peak_vram_gib": 16, "same_recipe_all_challengers": True,
    "reference_or_higher_precision_confirmation_required_before_pivot": True,
}, "quantization_identity")

authority = identified({
    "schema": "editor-text-realizer-model-acquisition-authority", "schema_version": 1,
    "source_commit": "c02f50ace46ff0b55a69a023b8c0536e48d863ef",
    "bakeoff_protocol_identity": "1159a4cd2c658437065485d596178b13d2f2e716c707b48a87ab901f4c2b9e4c",
    "bakeoff_pack_identity": "1c6a6a6eccf1b23bb8627b7a91832936fdd7df56b34dc8cde3ad923a0653cfc3",
    "snapshots_identity": snapshots["snapshots_identity"], "quantization_identity": quantization["quantization_identity"],
    "required_free_bytes": snapshots["aggregate_bytes"] * 2 + 10 * 2**30,
    "store_root": "/root/pf9-editor-model-store/sha256", "download_transport": "HTTPS_STREAM_EXACT_REVISION",
    "no_overwrite": True, "staging_suffix": ".inflight", "atomic_publish_after_full_verification": True,
    "partial_staging_is_eligible": False, "program_receipt_required_for_bakeoff": True,
    "download_authorized": False, "model_load_authorized": False, "quantization_authorized": False,
    "inference_authorized": False, "optimizer_creation_authorized": False, "training_authorized": False,
    "historical_holdouts_allowed": False, "cleanup_authorized": False, "parent_selection_authority": False,
    "promotion_authorized": False, "release_authorized": False,
}, "authority_identity")

for name, value in ((f"{PREFIX}-snapshots.json", snapshots), (f"{PREFIX}-quantization.json", quantization), (f"{PREFIX}-authority.json", authority)):
    write(name, value)

manifest_core = {
    "schema": "editor-text-realizer-model-acquisition-pack", "schema_version": 1,
    "authority_identity": authority["authority_identity"],
    "files": {name: sha((ART / name).read_bytes()) for name in (f"{PREFIX}-authority.json", f"{PREFIX}-quantization.json", f"{PREFIX}-snapshots.json")},
    "source_files": {
        "editor-core-text-realizer-base-bakeoff-v1-manifest.json": sha((ART / "editor-core-text-realizer-base-bakeoff-v1-manifest.json").read_bytes()),
        "editor-core-text-realizer-base-bakeoff-v1-protocol.json": sha((ART / "editor-core-text-realizer-base-bakeoff-v1-protocol.json").read_bytes()),
    },
    "models_downloaded": False, "model_loaded": False, "quantization_performed": False, "inference_performed": False,
}
manifest = identified(manifest_core, "pack_identity")
write(f"{PREFIX}-manifest.json", manifest)
print(json.dumps({"status": "PASS_BUILD", "authority_identity": authority["authority_identity"], "pack_identity": manifest["pack_identity"]}, sort_keys=True))
