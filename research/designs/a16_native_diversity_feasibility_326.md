# A1.6 — native latent-alphabet diversity: bounded design decision

**Status:** Source-only feasibility and experimental protocol **draft**.
**Owner:** [UniverseGenome #326](https://github.com/kinoko34077/UniverseGenome/issues/326), cross-lane [#171](https://github.com/kinoko34077/UniverseGenome/issues/171).  
**Frozen parent:** A1.5 original-R2 retrospective, source/conditions/negative results archived at
`research/artifacts/a1_317_selected_latent_diversity_2026-10-13.json`.
**Not authorized:** new independent physical seed, revised default physics,
experimental candidate promotion, reserved held-out, R3/Phase H, autonomous-learning claim.
**Source baseline at design start:** `d466eb62e5acdeb082e3e476ae07f0a06a24b12a`.
The exact PR head and CI must be recorded in #326 prior to accepting this design.

## 1. Identified logical obstacle

The original source-native R2 cases (already exposed positive seed544 / negative seed545)
contain **764 / 966 genuine directed native selected reads per branch** with both source
and destination 16-bit pre-latents equal to `1`; fusion/fragmentation/noise counts were
`0` through +1000 generations in both cases. Source-native B/H trace values differ
in 95 positive events, and the selected mask differs in 36, but
`masked_copy(1, 1, mask) == 1` for **every** possible mask.

The obstacle at these fixed cases is **absence of an information-bearing source
latent contrast in native read contacts**, not merely too narrow a transmission mask.
This result is retrospective; it is not independent evidence of universal impossibility.

## 2. Existing native physical alternatives

| Existing native mechanism | Homogeneous input, simple algebra | Reachability requirements / risk | Interpretation |
| --- | --- | --- | --- |
| Default `masked_copy` | `(1,1,any mask) -> 1` | Needs a source/destination latent contrast from another physical process | Cannot create contrast alone |
| **Existing exact-cover fusion** | Four `SHAPE_SINGLE` cells with latent `1` -> `mix_fusion_latent([1]*4)=0x1111` | 2x2 physical cover, same structure level below 7; each bond >=32 **at fusion stage**, pairwise relative velocity <=8; high conjunction cost, and fusion was absent in original R2 | Potential default-compatible generator; not natural reachability proof |
| Existing `masked_xor` | `(source1,dest1,mask bit0) -> 0` | Actual mask must include bit0; can toggle/erase as easily as produce | Parameterized physics alternate, changes original replay |
| Existing `rotate_copy` (rotate4) | `(source1,dest1,mask bit4) -> 17` | Actual mask must select bit4; shifted contents may not preserve semantics | Parameterized physics alternate, changes original replay |
| New initialization/injection | Can trivially seed multiple latent words | Shortcuts genuine local emergence and risks seeded-answer leakage | **HOLD** |

The bounded synthetic fixture `tests/test_a16_native_latent_diversity_feasibility_326.py`
tests a genuine `core.physics.step` on **four manually positioned and bonded**
single-shape cells covering a 2x2 region. Its configuration has `bond_decay=1`,
so preloaded bonds `33` survive at `32` for native fusion; bond `32`
decays to `31` and fails the original `fusion_bond_threshold=32`.
Other controls: incomplete cover, `fusion_enabled=False`. The fixture verifies
zero collision/latent transfer, one local fusion into `0x1111`, and exact deterministic
snapshot replay across two independently constructed identical states.

**Synthetic preloading is not evidence that an unmodified self-evolving
universe ever reaches those bonds/positions.** Nor does novel word generation
alone prove teacher-specific information transfer or learning.

## 3. Scientific priority

**Select existing physical fusion reachability as the FIRST mechanism to
investigate, not yet as an accepted learning solution.**

Rationale: it can create a nontrivial latent alphabet without changing the
default `masked_copy` rule, teacher semantics, or deterministic engine.
The strongest unresolved issue is whether the old default native population
can reach all fusion gates at once. If it cannot, the evidence will determine
whether to CHANGE_PATH to exactly one already-parametrized alternate operator
(`masked_xor` or `rotate_copy`) rather than alter thresholds to manufacture fusion.

The next **smallest observational study proposal** is an eligibility-funnel
diagnostic, not a new candidate parameter sweep: count actual source-native
physical 2x2 covers by stage, then counts passing level/bond/velocity/lifecycle
gates, using strictly original per-step event provenance. Do not label synthetic
manually assembled 2x2 covers as natural. Reuse source-native prior-exposed
seed data only if a justified additional observation is needed and approved in
the owning issue; do not repeat original evidence that already answers the question.

## 4. Separate future prospective causal protocol — NOT YET FROZEN OR APPROVED

A future independently owned prospective causal test, if later authorized,
must freeze **before outcomes**:

- **One** source-native mechanism candidate and exact physics config / code SHA;
  baseline remains unmodified `masked_copy` with default source semantics.
- Seed roster separated from *all* R1/R2/D7/A1 and reserved Phase H/held-out
  partitions; equal physical host conditions across B/H and no-teacher/sham.
- Ex ante native gate counts: eligible local geometry, level, bond, velocity,
  actual fusion, distinct active latent words, actual compatible selected
  source/destination contrast, mask overlap, native changed recipient result,
  carrier survival/turnover. Each has its own denominator.
- Autonomous teacher-specific causal endpoint requires controlled B/H-to-recipient
  change that disappears in the negative/sham, not merely nonzero latent diversity.
- Resource ceiling <=1536 MiB max RSS, fixed wall/runtime/case budget, deterministic
  CPython baseline, PyPy only with independently matched full state/event hashes,
  no manual seed selection, no post hoc threshold tuning.
- Explicit FAIL/NOT_EVALUABLE/CHANGE_PATH and high-cost STOP condition.
  No R3/L3 promotion until its independent predeclared >=12/16 threshold is met.
- No effectful new cohort, held-out or default change from this design alone.

## 5. Acceptance record for the present unit

This unit is accepted only after the synthetic fixture verifies authentic
native step/fusion constraints, CPython+PyPy short CI and ordinary Phase5/browser
regression succeed, formal current-head review is recorded, and the reviewed
PR is merged. Record exact source SHA, CI ids, fixture pass/fail and next decision
on #326. **No independent learning claim**.
