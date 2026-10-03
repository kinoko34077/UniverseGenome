# ADR-005 — Compact 8-bit bus I/O
Status: accepted-default

## Decision
Use eight data lines plus VALID for input, and eight data lines plus VALID and NULL for output instead of 256 one-hot byte organs.

## Constraint
Toroidal geometry means opposite board edges are adjacent; I/O placement must account for that.
