# Canonical WSL Execution Boundary V1

## Decision

Feasible with staged migration. A transport-only, application-wide boundary is
approved architecturally. A flag-day migration is rejected because historical
Semantic Admission and governed-probe executors have exact byte, command,
dependency, lifecycle, and evidence bindings.

The boundary is shared infrastructure. It is not owned by Scout, Editor, Chief
Editor, Semantic Admission, Voice, or any model. Consumers may use it only when
their separately governed workflow requires local WSL execution. Existing
HTTP-based Ollama and OpenAI paths are not redirected through WSL.

## Ownership boundary

The infrastructure owns:

- the canonical distribution and executable profile;
- deterministic Windows-drive to `/mnt/<drive>` conversion;
- no-shell argument construction and environment transport;
- hidden Windows process creation, UTF-8 decoding, timeout classification;
- typed transport failure codes and cryptographic execution receipts;
- one-shot execution and caller-owned durable process launch.

Consumers continue to own:

- prompts and immutable factual authority;
- model, adapter, tokenizer, grammar, and schema identity;
- request construction and semantic validation;
- admission decisions, output eligibility, abstention, and fail-closed policy;
- retries, selection, repair, cancellation, heartbeat, and durable lifecycle;
- whether execution is authorized at all.

The boundary never retries, repairs, selects, or promotes an output. Its
`authority_reference` is opaque receipt data and grants no authority.

## Audit findings

The inventory found 18 host launch surfaces before migration: Core V1.1 and
V1.2 plus 16 Semantic Admission/evaluation launchers. It also found duplicated
distribution names, VENV paths, path conversion, dependency bridge handling,
process visibility flags, encoding, timeout handling, and WSL failure parsing.
WSL-side runner scripts additionally contain fixed Linux model/repository paths;
those are model contracts, not transport configuration, and remain consumer
owned.

Scout and Chief Editor currently use provider/application workflows and do not
directly launch the WSL model. Editor Core V1.2 is the active application WSL
consumer. The new boundary is available to all layers, but availability does
not authorize use.

## Risk assessment

| Risk | Inherent | After controls | Control |
|---|---:|---:|---|
| Flag-day blast radius | Critical | Low | Staged allowlist; frozen launchers unchanged |
| Authority contamination | Critical | Low | Transport-only types; opaque reference; no prompt/model/schema fields |
| Frozen evidence invalidation | Critical | Low | Historical artifacts stay immutable; each future migration needs a new binding |
| Command or argument drift | High | Low | Deterministic tuple and command SHA-256; no shell |
| Silent distro fallback | High | Low | One canonical named distribution; fail closed, never auto-select another distro |
| Dependency bridge leakage | High | Medium | Bridge is an explicit profile, never global or automatic |
| Retry/output-selection contamination | High | Low | Boundary performs exactly one launch and no selection/repair |
| Timeout/lifecycle behavior drift | High | Low | One-shot typed result; durable lifecycle remains caller owned via `spawn` |
| Sleep/reboot/cold-start behavior | High | Medium | Typed access/distro/launch/timeout failures; operational preflight remains explicit |
| GPU/model contention | High | Medium | No daemon or implicit concurrency introduced; consumer scheduling unchanged |
| Orphan WSL processes | High | Medium | Durable handle exposes process to existing caller lifecycle; no hidden background daemon |
| Windows/WSL path ambiguity | High | Low | Pure absolute-drive mapping; relative and traversal paths rejected |
| Environment or shell injection | High | Low | Argument-vector launch, no shell, NUL rejection, constrained environment names |
| Secrets in receipts | Medium | Low | Receipts hash output and command; they do not serialize argv or environment values |
| Packaging omission | Medium | Low | Explicit PyInstaller hidden imports; no model/distro bundled |
| Installer overreach | High | Low | Installer does not install/upgrade WSL, distro, drivers, models, or bridges |
| Antivirus/process-window UX | Medium | Low | `CREATE_NO_WINDOW`; stable `wsl.exe` process ancestry |
| Test brittleness | Medium | Low | Injected boundary, deterministic command tests, direct-launch governance test |
| Performance regression | Medium | Low | No extra `wslpath` process; no automatic health probe per inference |
| Future version evolution | Medium | Low | Versioned package/profile/receipt; no mutation of V1 identities |

## Packaging and installer impact

The Python boundary is packaged explicitly. Model weights, adapters, Linux
Python, GPU libraries, the distro, and WSL itself remain external operational
prerequisites. Installing or repairing those components from the application
would be destructive, privileged, network-sensitive, and authority-expanding;
V1 therefore detects and reports failures but never changes the machine.

No installer prerequisite action is added in this migration. The existing
installer authority is high-risk and separately frozen. A later user-facing
readiness panel may call a separately authorized preflight, but installation,
distro registration, default-distro changes, and package upgrades must remain
explicit owner operations.

## Testing and evidence impact

Unit tests cover path mapping, profile/command identities, environment sorting,
UTF-8, hidden launch, typed failures, timeout, no retry, durable spawn, opaque
authority, and absence of semantic configuration. A governance test freezes
the current 16 historical direct launchers and rejects any new bypass.

Core V1.1 and V1.2 are compatibility consumers. Their prompt/model/request and
response contracts are unchanged. Their legacy `_wsl_path` names remain as
wrappers. New transport receipt fields may be added to diagnostics, but do not
affect provider results or eligibility.

Existing frozen probe evidence remains evidence for its original executor
bytes. It is not rewritten to claim the new boundary. Each historical executor
may migrate only after command-equivalence, lifecycle-receipt, timeout, and
zero-inference construction verification under a new versioned binding.

## Migration sequence

1. Shared V1 boundary and governance rule.
2. Active Core V1.2 and legacy Core V1.1 compatibility migration.
3. Packaging collection and application regression proof.
4. Future components must use V1 or a separately reviewed successor.
5. Frozen Semantic Admission/probe launchers migrate one family at a time only
   when their work resumes and new evidence is authorized.

This sequence provides a permanent default without contaminating frozen
historical authority or creating an application-wide semantic singleton.
