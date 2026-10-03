# ADR-003 — Structure uses 2 bits × 8 hierarchy levels
Status: accepted

## Decision
Use a 16-bit structure field partitioned into eight 2-bit hierarchy slots.

Default vocabulary: 00 empty, 01 1×1, 10 1×2, 11 2×1. A 2×2 arrangement is a fusion/carry condition.

## Consequence
One hierarchy shift is a two-bit field shift (`<< 2` / `>> 2`), distinct from geometric movement.
