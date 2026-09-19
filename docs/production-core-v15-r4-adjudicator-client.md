# V15 R4 human adjudicator client

The client runs one registered role per isolated session. It accepts the private
key only as an explicit external path, derives its public key through the bound
OpenSSL executable, and rejects a mismatch with the frozen owner registry. It
never reads private-key bytes into Python or writes them to logs or outputs.

`ADJUDICATOR_A` uses custody root
`/root/pf9-v15-r4-human-adjudication/custody/ADJUDICATOR_A` and receipt root
`/root/pf9-v15-r4-adjudicator-a-receipts`. `ADJUDICATOR_B` uses the corresponding
`ADJUDICATOR_B` custody root and `/root/pf9-v15-r4-adjudicator-b-receipts`.

Run from the published repository with `PYTHONPATH=src`. Supply the evaluator's
existing private-key path and the explicit OpenSSL executable. The command
displays one blinded packet, accepts only `PASS`, `FAIL`, or `INDETERMINATE`,
signs the canonical receipt in Ed25519 raw-message mode, immediately verifies
it, and atomically creates a no-clobber receipt. On restart it verifies all
existing receipts and resumes at the first missing ordinal. Progress contains
receipt identities and counts but no verdicts. Do not expose either receipt
root to the other evaluator until both independent sets are complete.

```bash
PYTHONPATH=src python3 scripts/adjudicate_production_core_v15_r4.py \
  --role ADJUDICATOR_A \
  --custody-root /root/pf9-v15-r4-human-adjudication/custody/ADJUDICATOR_A \
  --receipt-root /root/pf9-v15-r4-adjudicator-a-receipts \
  --private-key /OWNER/EXTERNAL/PATH/TO/A-PRIVATE-KEY.pem \
  --registry docs/artifacts/production-core-semantic-adjudicator-public-key-registry-v1.json \
  --openssl /usr/bin/openssl
```

The B command changes only the role, custody root, receipt root, and external
private-key path to their B values. Complete per-role closure is exactly 1,986
locally verified receipts. Aggregation, semantic verdict, and promotion remain
outside this client.
