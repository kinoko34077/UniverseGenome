# ADR-006 — Separate simulation Core and GUI
Status: accepted

## Decision
The simulation core runs headlessly and owns the authoritative clock. GUI rendering observes summaries/snapshots and provides controls without driving simulation time.

## Reason
Performance, determinism, automated testing and reproducibility must not depend on rendering rate.
