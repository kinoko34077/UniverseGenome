# UniverseGenome v0.1 Overview

Canonical requirements: `01_requirements.md`  
Historical rationale: repository Issue #2  
Detailed source review: repository Issue #4

# 0. Specification status

Status terms:

- `accepted`
- `accepted-default`
- `parameterized`
- `candidate`
- `implemented`
- `tested`

Implementation must not silently promote a default/parameter into a permanent rule.

---

# 1. Architecture

## SPEC-ARCH-001 — Inner / outer split
**Status: accepted**

UniverseGenome is divided into:

### Inner universe
A deterministic discrete local-physics simulation.

### Outer search
A search/evolution process over universe-level physical parameters and fixed rule-family categories.

Inner learned state and outer genome are different data.

---

## SPEC-ARCH-002 — Core / observation split
**Status: accepted**

The authoritative simulation core must run headlessly.

GUI/observation reads summaries/snapshots and must not be the authoritative clock source.

---

## Core research framing

UniverseGenome treats inner learning as deterministic local state evolution through time and separates it from outer search over universe-level physical parameters.

The core does not encode words, syntax categories, semantic tags, concept IDs, or permanent Cell identities.

## Phase boundary

Phase 0 establishes canonical specification and scaffolding. Phase 1 implements only the deterministic single-universe physical foundation.
