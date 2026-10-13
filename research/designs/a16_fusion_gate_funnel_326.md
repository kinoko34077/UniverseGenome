# A1.6-2 — Source-native fusion gate funnel observability

Owner: [UniverseGenome #326](https://github.com/kinoko34077/UniverseGenome/issues/326). Parent scientific objective: [#171](https://github.com/kinoko34077/UniverseGenome/issues/171). This is a **design and synthetic-only fixture**, not a prospective naturally evolving universe experiment or permission to consume new seed/held-out.

## Mechanistic question

Original R2 exposed Seed 544/545 through 1,000 native post-h0 steps produced fusion_count = 0, and no local selected reader latent value other than 1. The absence of fusions alone does NOT establish whether natural evolution fails geometry, common structure level, residual bond>=32, relative velocity<=8, actual active lifecycle, or the combination.

The native candidate computation proceeds through all these stage filters, in order:

1. Native 2x2 anchors derived from post-move occupancy, at most 8 local slots, groups of size 2..4.
2. Each footprint contained by candidate region.
3. Non-overlapping footprints.
4. Exact 2x2 cover.
5. Same structure level and level < 7.
6. Every participant's **post-contact** bond >= fusion_bond_threshold.
7. Pairwise relative velocity <= fusion_velocity_threshold.

Only then native _fusion_candidates returns potential groups. The subsequent _fuse_groups may reject a group because its cells were previously consumed or inactive; fusion_enabled controls whether _fuse_groups runs at all. **Count these as distinct endpoints**.

The source-only `research/a16_fusion_eligibility_funnel_326.py` computes each funnel denominator on a native post-move/contact state, calls authoritative _fusion_candidates and **fails closed** if the candidate group list differs, and checks no physical state changed. Its fixture controls distinguish geometry, structural level, bond, velocity, and fusion flag. Tests **do not** instrument naturally evolved cohort outcomes.

### Subtle source constraint: separated cells lose bonds

Four SHAPE_SINGLE cells in a 2x2 complete cover occupy four distinct tiles. Under native collision detection, they do not collide **in the same fusion step**. Their bond decreases by bond_decay=1 if no other compatible contact shares their tiles. Consequently in that synthetic arrangement each enters the step with bond >= 33 to remain >= 32 when fusion candidates are resolved. Source-native previous overlap contacts, if any, grow bonds by 4 up to 255; leaving those contacts decays it by 1 per isolated step. A native physical trajectory must satisfy **both** historical bond accumulation and later exact 2x2 formation while participants survive. No claim that such a trajectory has been found in the original R2 environment.

### Scientific next action (conditional)

Inspect existing frozen R2/D15 artifacts for *authoritatively saved per-step post-contact occupancy and bond/velocity snapshots*. If absent, propose one **read-only** observational gate-count replay of already exposed Seed 544/545, bounded by existing original h0+six golden hashes, native selected event parity, source SHA, 1536 MiB RSS /900 sec, no new cohort. Such replay still requires a separate accepted plan; this file alone does not dispatch it. Count source-specific metric distributions at every stage and identify the earliest bottleneck **without altering thresholds**. If native candidate collection and physical fused_count disagree, retain selected-vs-actual processing distinction.

Only if a fixed observational contrast justifies it may a later independent prospective experiment preregister a single teacher-blind physical method, disjoint seeds/heldout, sham controls and actual B/H-specific recipient readout with turnover/lifetime evidence. New R3/L4+ or learning claim remains blocked.

All tests/results/protocols and future raw source hashes must be committed directly in UniverseGenome, not to Google Drive.
