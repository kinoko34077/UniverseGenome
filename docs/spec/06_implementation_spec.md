# Implementation and Phase Specification

Implementation choices remain subordinate to requirements/behavior. Phase 0
established the repository/specification scaffold; the accepted implementation
frontier is Phase 1 through Phase 5.

# 39. Existing asset reuse

## SPEC-REUSE-001 — Structured-Cell-Automaton
**Status: accepted**

Conceptual/code reuse targets:

- `engine/evolver.py` → outer genome evolution
- `engine/scoring.py` → universe fitness
- `save/quicksave.py` → snapshot/metadata concept
- `viz/genealogy_plot.py` → genome lineage
- `viz/score_heatmap.py` → optimization visualization

Do not preserve v1 semantic behavior merely to reuse code.

---

## SPEC-REUSE-002 — Remove v1 semantics
**Status: accepted**

Do not carry into the new core:

- Syntax
- meaning_tags
- tagging
- semantic clustering
- MemoryZone semantics
- OutputZone semantic selection
- tag-based think loop

---

## SPEC-REUSE-003 — 2bit-cell-automaton
**Status: accepted**

Reuse/derive UI concepts/code where useful:

- p5.js board drawing
- pause
- step
- rewind/inspection concepts

Do not reuse the old physics update rule as v0.1 core physics.

Derived code must retain a source/provenance comment.

---

---

# 40. Preferred implementation stack

## SPEC-IMPL-001
**Status: accepted-default**

Core first choice:

- Python
- NumPy fixed arrays
- Numba JIT for hot/branch-heavy loops where beneficial

This is implementation-level and may change without changing upper-level behavior requirements.

---

## SPEC-IMPL-002
**Status: accepted-default**

GUI first choice:

- browser/p5.js derivative of `2bit-cell-automaton`
- local state transport/server between GUI and core

Do not overbuild transport in the first version.

---

---

# 41. Phase 0 implementation scope

## SPEC-PHASE0-001
**Status: accepted**

Phase 0:

- preserve/bootstrap repository truth
- canonical spec structure
- ADRs
- core scaffold
- config scaffold
- persistence scaffold
- tests scaffold
- minimal GUI scaffold
- README update

No claim of learning success.

---

---

# 42. Phase 1 implementation scope

## SPEC-PHASE1-001
**Status: accepted**

Implement one universe only:

- 32×32 torus
- 256×256 internal fixed-point position
- fixed slot pool
- no permanent Cell ID
- structure uint16 storage
- latent uint16 storage
- HP uint8
- direction/speed
- synchronous update
- movement
- destination footprint
- tunneling
- noise spawn
- collision discovery/resolution
- basic HP decay/damage
- black-hole lifecycle
- deletion/free slots
- deterministic replay
- minimal snapshot save/load
- headless runner
- performance counters

Explicitly do **not** implement in Phase 1:

- fusion
- fragmentation
- latent category comparison
- 128 universes
- I/O learning
- outer evolution

---

---

# 44. ADRs required before/with implementation

The repository should record at least:

1. v1 semantic architecture → local-physics UniverseGenome
2. no permanent Cell ID
3. `2bit × 8 hierarchy levels`
4. four latent operator categories
5. 8-bit bus I/O
6. Core/GUI separation
7. evaluation clone
8. no cross-category elimination in first comparison phase

---

---

# 45. Specification change rule

Any change to a physical rule must record:

- specification ID changed
- old behavior
- new behavior
- reason
- affected tests
- compatibility/snapshot impact
- whether accepted/default/parameterized status changed

Do not rewrite historical rationale out of existence.

---

---

# 46. Current unresolved / intentionally flexible items

These are not fixed enough to hard-code as hidden assumptions:

- exact initial density range
- exact HP decay/gain values
- exact collision damage formula
- exact fusion threshold
- exact contact gain/decay values
- exact fragmentation probability family
- black-hole duration choice remains parameterized; the current default is
  `black_hole_grace = 2`
- exact bit-selection algorithm for mask
- exact event-hash RNG primitive
- exact I/O organ coordinates are fixed in the Phase 4 contract at
  `docs/spec/02_functional_spec.md`
- exact teacher repetitions/delay
- exact success threshold for the first learning claim
- whether Masked AND remains a productive fourth category
- exact GUI transport mechanism
- exact binary snapshot encoding

Keep these visible as parameters/defaults/candidates.

---

---

# 47. Canonical relation to other Issues

- #1 — parent bootstrap/implementation owner
- #2 — historical meeting/design record
- #3 — requirements
- this Issue — detailed specification

If this specification and #3 conflict on *what must be achieved*, #3 governs and this Issue must be reconciled.

If later repository files become accepted canonical specs, this Issue should link to them and remain a durable review/history surface rather than silently diverging.
