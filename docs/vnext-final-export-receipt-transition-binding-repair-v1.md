# VNext FINAL Export Receipt Transition-Binding Repair v1

## Verdict

PASS + 0 BLOCKERS, isolated and not active.

## Repair

Export eligibility now requires an exact authoritative transition binding:

- workflow identity matches;
- exactly one FINAL_READY to EXPORTED transition exists;
- transition input identity equals FINAL identity;
- transition output identity equals export receipt identity.

A receipt that is internally content-addressed but rebound to another path,
workflow, or transition is rejected.

## Evidence

Dedicated tests cover valid replay/recovery, failure before FINAL_READY, failure
before EXPORTED, export-byte tampering, self-consistent receipt rebinding,
cross-workflow receipt substitution, missing transition binding, and duplicate
transition binding.

Product root, product lock, schema, and active integration state are unchanged.
Audit streak remains 0/2.
