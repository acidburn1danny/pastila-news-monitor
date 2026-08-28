# Construction-Obligation V2 zero-model operational preflight

Verdict: **PASS**.

The canonical WSL V1.1 bridge profile successfully executed the separately
versioned zero-model worker. On the shared DrvFS repository path, the worker
fully flushed a 59-byte temporary file, published it through an exclusive hard
link, removed the temporary name, and verified the published bytes and SHA-256.

The worker then spawned one non-daemon synthetic sleeping child. PID 361 was
observed alive, terminated, joined, and reaped with exit code -15. `/proc/361`
was absent both inside the worker after joining and in a separate post-run WSL
check.

Tokenizer loads, model loads, and generation calls were all zero. No provider,
probe, Stage C, runtime, or production authority was exercised.

The initial attempt failed before evidence-root creation because a host process
running under `python -m` passed `__main__` as the Linux module name. Commit
`116b7bdd3c27d4e2fe6de2939788f057dae6826c` bound the canonical importable
module name. The failed attempt created no evidence and started no synthetic
child; the remediated attempt used the still-unused exclusive evidence root.

Actual generation remains blocked because no request-bound generation authority
receipt has been issued.
