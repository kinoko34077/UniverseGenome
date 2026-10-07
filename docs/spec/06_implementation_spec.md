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

The current v0.1 authoritative state uses fixed-capacity structure-of-arrays
semantics implemented with fixed-length Python lists, and does not currently
use a Numba hot-loop path. This is an explicit implementation-default
deviation, not a change to cell/state semantics: capacity is still fixed,
snapshot/replay behavior is deterministic, and bounded performance is measured.
Do not migrate the stable core solely to match the preferred stack. Revisit
NumPy/Numba only when profiling or a concrete performance target demonstrates
a benefit and preserve the same upper-level behavior contracts.

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

# 45.1 D1 slow-trace implementation boundary (#132)

## SPEC-IMPL-ST-001 — Specification-first implementation gate
**Status: accepted**

#132 accepts the specification only; it does not introduce production slow
trace. Production implementation belongs to a separate successor owner.

A separate implementation owner may begin only from the accepted #132 terminal
route and must use RED-first acceptance evidence against this specification.

Expected production surfaces if later authorized:

- authoritative UniverseState storage/allocation/reset;
- physical configuration for accepted slow-trace parameters;
- synchronous step ordering and local event resolution;
- latent mask-width calculation only at the bounded read-coupling point;
- fusion/fragmentation trace material handling;
- BLACK_HOLE discharge / FREE erasure;
- deterministic decay event addressing;
- independent UniverseState snapshot v1→v2 and Phase 5 optimizer envelope
  v5→v6 migration;
- clone/replay/equality and relevant observer serialization where authoritative
  state is projected;
- unit/integration/research-gate tests.

Not authorized by D1 adoption alone:

- I/O organ geometry/protocol change;
- new semantic labels/tokens;
- Phase 5 fitness/growth/pruning/objective change;
- automatic addition of slow-trace parameters to the evolved genome;
- P6.10+ capability work;
- L4 recall or output-readout redesign.

---

## SPEC-IMPL-ST-002 — Bounded state/work target
**Status: accepted**

The specified authoritative state cost is one uint8 per cell slot:

- 1024 bytes per max-capacity Universe in compact representation;
- 128 KiB raw slow-trace arrays across 128 max-capacity Phase 5 Universe slots,
  before Python/container/snapshot-history overhead.

Normal per-generation work must remain bounded by existing local structures:

- O(active cells) write/decay bookkeeping;
- O(already-selected compatible local pairs) trace transfer;
- bounded local-neighborhood work for BLACK_HOLE discharge;
- no persistent N² pair matrix;
- no global memory search/broadcast.

A later implementation owner must measure actual runtime/snapshot overhead and
may not treat these raw-state arithmetic bounds as performance acceptance by
themselves.

---

## SPEC-IMPL-ST-003 — Deterministic event-addressing boundary
**Status: accepted**

Slow-trace **stochastic decay** must reuse the accepted deterministic
event-address model of SPEC-RNG-001/002.

BLACK_HOLE discharge ordering is deterministic rather than stochastic. It uses
the physical-state ordering defined by SPEC-ST-006. A reusable storage-slot
index may appear only as the final total-order tie-break after the physical
tuple is equal.

A reusable storage slot may therefore be used as an implementation array
reference / final deterministic ordering tie-break, but it must not:

- become a permanent Cell identity;
- enter any slow-trace probability/event key;
- act as lineage identity;
- preserve trace through FREE-slot reuse.

Physical position/address, generation, event type and a documented physical
local-index/subevent domain remain the event-key basis for stochastic decay.

---

## SPEC-IMPL-ST-004 — Migration / rollback boundary
**Status: accepted**

A later implementation must preserve a reversible compatibility boundary:

- the standalone/nested UniverseState snapshot advances independently from
  version 1 to specified version 2;
- the Phase 5 optimizer envelope advances independently from version 5 to
  specified version 6;
- accepted optimizer v4/v5 and UniverseState v1 compatibility remains readable
  as defined by the data spec;
- migration produces zero slow trace rather than inferred history;
- migrated legacy states use the SP3-defined inert compatibility parameter
  profile so old continuation does not silently activate new memory physics;
- the accepted implementation/default profile is the same inert tuple
  `(0,0,0,0,8)` until a later non-inert operating regime is separately
  accepted;
- non-inert values are explicit research-only physical overrides and must not be
  silently promoted to config defaults or the Phase 5 evolved genome;
- any later non-inert default promotion requires predeclared L3, migration,
  semantic-cleanliness and TEST-ST-010 performance evidence;
- no implementation migration rewrites historical repository data in place;
- if production adoption is rejected after research, rollback is performed by
  ordinary version-controlled change/revert rather than shared-history rewrite.

No release/deploy/publication action is implied by this accepted specification.

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


---

# 48. Generalized Outer Search implementation boundary (#144 / #145)

## OSG-IMPL-001 — Dependency direction
**Status: accepted / blocking**

The generalized implementation shall preserve this dependency direction:

```text
SearchPlan + registries + ObjectiveProfile
                |
                v
        Outer Search model
                |
                v
        candidate resolver
                |
                v
        ResolvedUniverseSpec
                |
                v
        Inner Universe construction/step
                |
                v
        evaluation adapter
                |
                v
        Outer evidence/selection
```

Inner modules shall not import or depend on SearchPlan, candidate rank,
comparison-stratum state, lineage, cohort role or ObjectiveProfile.

Outer modules may depend on stable Inner construction/snapshot interfaces but
shall not mutate authoritative Inner cell arrays directly to implement search.

## OSG-IMPL-002 — Registry / resolver boundary
**Status: accepted**

Dimension and rule registries belong to the generalized Outer/resolution
boundary.

Registry responsibilities:

- declare stable dimension/rule IDs;
- declare domains, defaults/inert values and compatible strategies;
- map generalized values to one authoritative physical destination;
- validate physical combination constraints;
- bind registered rule implementations.

Resolver responsibilities:

- validate one candidate under one SearchPlan;
- evaluate structured conditional activation;
- produce canonical candidate identity;
- produce immutable ResolvedUniverseSpec;
- bind physical rule implementations before Inner execution.

The generic scheduler/selector shall not contain per-dimension field-name
branches merely to recognize registered dimensions.

## OSG-IMPL-003 — No SearchPlan dependency in Inner hot loops
**Status: accepted / blocking**

SearchPlan lookup, registry iteration, strategy lookup, objective lookup and
candidate metadata lookup shall not occur per cell/per local event merely to
execute a fixed resolved candidate.

Where a rule choice can be resolved once at Universe construction, the Inner
step shall receive the bound implementation/value directly.

This requirement supports OSG-REQ-020 and prevents Outer policy from leaking
into physical behavior.

## OSG-IMPL-004 — Trusted finite rule registration
**Status: accepted / blocking**

A new Rule Dimension variant is added through reviewed repository code/data and
a stable registry entry.

SearchPlan may only choose registered IDs. It may not supply:

- Python source;
- bytecode;
- import strings to execute;
- lambdas/callables;
- runtime `eval` expressions;
- arbitrary AST/program fragments.

This is a finite trusted rule-family registry, not arbitrary code evolution.

## OSG-IMPL-005 — Authoritative legacy mapping
**Status: accepted / blocking**

There shall be one authoritative generalized mapping for the existing
UniverseGenome scalar surface and latent rule category.

Legacy compatibility APIs may remain temporarily, but their field/domain/rule
knowledge shall delegate to the generalized registry/resolver rather than be
maintained as a second independent source of truth.

The legacy mapping includes exactly the current eleven UniverseGenome physical
fields and current four latent operator rule variants. Slow-trace parameters
are registered physical dimensions but fixed/inert in Legacy SearchPlan.

## OSG-IMPL-006 — Incremental migration sequence
**Status: accepted**

Production generalization shall be introduced in bounded checkpoints:

1. generic SearchPlan/dimension/rule/candidate/ResolvedUniverseSpec model;
2. canonical Legacy SearchPlan static population reconstruction;
3. generic candidate resolution and scalar/rule mutation;
4. generic strata/evidence allocation/replacement;
5. generic selection/pruning and ObjectiveProfile binding;
6. optimizer v7 persistence/migration;
7. full frozen-oracle dynamic parity and performance gate.

A later checkpoint shall not begin while the immediately prior checkpoint's
acceptance is unresolved.

## OSG-IMPL-007 — Legacy adapter lifetime
**Status: accepted**

An adapter from existing UniverseGenome/category callers to the generalized
model may exist during migration.

The adapter shall:

- preserve exact existing public/config behavior;
- contain no independent mutation/selection policy;
- resolve through the same registry used by generalized SearchPlan;
- be removable without changing generalized candidate semantics.

No approximate parallel "legacy optimizer" may be kept as the compatibility
proof. Compatibility is established by Legacy SearchPlan running through the
generalized engine.

## OSG-IMPL-008 — ObjectiveProfile adapter boundary
**Status: accepted**

Current Phase 5 fitness/growth/pruning calculations may initially be wrapped as
the legacy ObjectiveProfile.

The wrapper shall preserve all existing semantics and expose evidence to the
generic Outer engine without changing Inner state.

New research ObjectiveProfiles are separate registered Outer definitions. Their
existence shall not alter the legacy objective or canonical learning claim.

## OSG-IMPL-009 — Optimizer persistence boundary
**Status: accepted / blocking**

When generalized Outer state becomes authoritative for continuation, optimizer
persistence advances from envelope v6 to v7 as specified by OSG-DATA-011/012.

UniverseState remains on its independently accepted schema unless an actual
Inner-state change separately requires migration.

Migration code shall have one deterministic v6→v7 legacy path. It shall not
select/search new dimensions or infer research settings.

## OSG-IMPL-010 — Frozen oracle is read-only compatibility authority
**Status: accepted / blocking**

The Phase A artifact generated from
`211d84b18fe68e70f89c8921d156e1b7c0592895` is immutable compatibility
evidence.

Production generalized code may read/compare against it in tests, but shall not
rewrite/regenerate it after generalized production paths change.

Any oracle mismatch is investigated as a generalized implementation/spec
defect; the expected artifact is not updated merely to make a new
implementation pass.

## OSG-IMPL-011 — Performance implementation boundary
**Status: accepted**

Generic dispatch shall remain outside per-cell work where possible.

The implementation shall not add:

- a persistent N² all-Universe comparison matrix;
- per-cell dynamic SearchPlan lookup;
- per-cell rule registry search;
- global memory search/broadcast through the generalized framework.

Matched density4/density32 legacy measurements shall enforce the 5% median
regression gate from OSG-REQ-020.

## OSG-IMPL-012 — Slow-trace registration boundary
**Status: accepted**

The generalized registry may represent:

- `trace_write_cap`;
- `trace_transfer_cap`;
- `trace_discharge_cap`;
- `trace_decay_rate`;
- `trace_bonus_shift`.

Legacy SearchPlan fixes them at `(0,0,0,0,8)`.

Phase B does not authorize production search over non-inert slow-trace values,
a second manually selected D1 profile, or reuse of the #140 cohort for adaptive
tuning.

A later memory-physics research owner must define a new predeclared SearchPlan,
search cohort, ObjectiveProfile and held-out validation cohort after generalized
legacy compatibility is fully accepted.

## OSG-IMPL-013 — Rollback boundary
**Status: accepted**

Generalization changes shall remain recoverable through ordinary version-control
revert/forward-fix.

No shared-history rewrite, snapshot-history rewrite or release/deploy action is
required by this implementation sequence.

Before the generalized implementation is accepted, current production defaults
and `learning_claim=false` remain unchanged.
