# ADR-002 — No permanent Cell ID
Status: accepted

## Decision
Cells have no persistent semantic UUID/identity. Reusable implementation slots are allowed.

## Reason
Individual identity is not part of the research model and creates lineage/bond/snapshot overhead unrelated to local state evolution.

## Consequence
Randomness, persistence and collision logic must not require permanent Cell IDs.
