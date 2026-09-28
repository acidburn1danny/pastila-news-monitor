# VNext R2 Byte-Identical Consolidation Binding Closure v1

Status: **ISOLATED_NOT_ACTIVE**  
Verdict: **PASS**

## Decision

The existing self-contained R2 step-9 dependency closure is the only R2 materialization authorized for the consolidated product. The future logical target is `components/editor-r2`, but this closure does not copy, move, rename, activate, or rewrite it. Relocation remains a later separately authorized migration using copy-then-verify semantics.

## Frozen dependency

The source closure contains 25 locked files and 28,185,570,253 bytes. Its dependency lock identity is `53fafbc03f70c8c32357645a6a428260f1bdfbd104edbe1c4aa825e95c83a10f`. The binding preserves the adapter, checkpoint, tokenizer, base model, loader, adapter loader, `fix_mistral_regex`, local-only resolution, relative layout, and platform tree identity.

The binding identity is `0084f051f7aac5e90f2209e1796d5dbf7a26bb3fbb14fbf0a9e06b5b0818810f`. The closure identity is `98db9cb3a276b6684fd3f2013a359b55703b8073d7745a9461a40ba4168adbf6`.

## Verification behavior

The verifier accepts an explicit closure root. It validates the exact lock bytes and semantic identity, frozen R2 identities, runtime binding, file inventory, containment, regular-file independence, sizes, and optionally every file SHA-256. It rejects symlinks, hardlink aliases, extra or missing files, unsafe paths, identity drift, byte drift, layout drift, and runtime drift. It performs no model load or inference.

## Architecture binding

The published consolidation authority classifies R2 as `KEEP`: source `components/r2-reference-v1`, target `components/editor-r2`, preserve byte-identically, relocate only during a later authorized migration. The Python ML platform remains a declared platform dependency identified by tree identity; it is not copied or modified here.

## Exclusions

No R2 bytes or identities changed. No model or EDITOR was rebuilt. No factual acceptance, product-lock replacement, active integration, relocation, copy, product-root mutation, model load, inference, training, optimizer activity, or cleanup occurred. `STOP_ALL_CANDIDATES` remains active, `VOICE = DISABLED_UNTIL_PROMOTION`, and `LEGACY_DEPENDENCY_COUNT = 0`.

