# VNext Critical-Path Authority Repair & EDITOR Vertical Slice v1

## Verdict

`PASS_ISOLATED_VERTICAL_SLICE`

Acest successor corectează authority/state defects demonstrate înainte de factual acceptance. `EditorDraft` există numai după structural validation; outputul structural invalid ajunge într-o stare cu rute explicite către source fallback sau abstention.

## Consolidation

Produsul activ folosește o singură schemă SourcePacket, cea emisă de SCOUT. Binding-ul publicat către vechiul contract EDITOR rămâne numai evidence de compatibilitate și nu intră în graful activ.

Boundary-ul EDITOR leagă într-un singur receipt SourcePacket, promptul, mesajele, rendered prompt, token IDs, chat template, tokenizer/model identities, decoding-ul complet, runtime configuration și outputul brut. Receipt-ul este produs de același apel care construiește `EditorDraft`.

## State repair

SQLite schema v2 extinde `workflow_artifacts` pentru `ACCEPTED_SETUP`, `SOURCE_FALLBACK` și `ABSTAINED`, fără a implementa factual acceptance. Migrarea v1→v2 este monotonică și păstrează `EDITOR_DRAFT`, `VOICE_DRAFT` și `FINAL_OUTPUT` existente.

## Exclusions

Closure-ul este fixture-only și izolat. Nu încarcă modelul, nu rulează inference, nu implementează factual acceptance, nu modifică product root/lock și nu activează vertical slice-ul.
