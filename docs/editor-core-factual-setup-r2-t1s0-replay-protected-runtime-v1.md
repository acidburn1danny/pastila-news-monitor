# T1/S0 Replay-Protected real-runtime boundary

The route binds six arm/seed slots to published commit `cc5e1894506372afca0a915a6ed202968c7b7f10`, R2 step-9, S0 at `5e-7`, the frozen evaluator, and tokenizer `d5f604…8135`.

The control arm learns from the existing T1 signal. The protected arm learns from the replay-protected signal. Both arms use the replay-protected annotations for common teacher-forced critical-span measurement, keeping learning weights separate from measurement coverage.

This state grants no execution authority. Safe route modes are preflight and fixtures only. A separately published execution authority is required before any model load, optimizer creation, training, or real inference.
