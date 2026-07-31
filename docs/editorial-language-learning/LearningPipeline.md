# Learning Pipeline

## Responsibilities and contract

Correction Import → Graph → Observation → Aggregation → Evidence → Confidence → Candidate → Profile → Guidance. No stage is skipped. A validated correction is required for observation; aggregation produces inactive candidates only; lifecycle changes are explicit; profile construction groups accepted preferences without inventing them.

## Dependencies, limitations, and guarantees

Stages exchange IDs and immutable artifacts. They do not widen scope, create prose, or mutate inputs. Validation failure blocks acceptance and conflicts remain reviewable. Downstream composition may consume guidance but remains its owner.
