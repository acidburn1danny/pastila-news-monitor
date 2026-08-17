# Owner Edit Evidence Capture + Editorial Usability Baseline V1

This observation-only subsystem stores the original governed Editor output before later owner finalization. Evidence is held in the owner-local `editorial-evidence-v1` directory beside ActiveProject, not in ActiveProject or release resources.

Generation capture is idempotent and failure-isolated. Explicit finalization creates one generated-to-final pair; repeated finalization with the same final hash is a no-op and a different second final is rejected. Intermediate saves are not independent samples.

Analysis uses deterministic Romanian sentence-like units and reports retained, lightly edited, substantially edited, deleted, inserted, and moved units. Owner classifications distinguish facts and hallucinations from style. No observation is promoted or injected into generation.

KPI V1 reports a normalized partial score only over available dimensions and always publishes completeness and confidence. Mechanism, factual status, and active edit time remain unavailable unless governed evidence exists. Retention is never treated as factual proof.

The local report renderer exposes baseline, final, diff, KPI, factual flags, and expression outcomes. Store methods support correction, deletion, and reset. Corrupt records are rejected or skipped without changing ActiveProject or owner drafts.
