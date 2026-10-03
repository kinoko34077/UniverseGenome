# ADR-007 — Evaluate on a clone
Status: accepted-default

## Decision
Learning evaluation uses a clone/snapshot-derived universe where possible rather than perturbing the authoritative training universe.

## Reason
Evaluation stimuli must not themselves become additional training history.
