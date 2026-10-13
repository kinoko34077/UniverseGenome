# A1.8 — exact sparse-geometry occupancy null (theoretical comparator only)

Authority: UniverseGenome [#326](https://github.com/kinoko34077/UniverseGenome/issues/326), research objective REQ-001, authentic completed original R2 natural-fusion funnel [#329](https://github.com/kinoko34077/UniverseGenome/issues/329). This is a **mathematical assumption-bound reference**, not a native experimental result or a prospective new-Seed protocol.

## Exact reference model

Native world `core/geometry.py` has 32 × 32 periodic **logical tiles** (N=1024). In the already exposed original R2 seed544/545 initial h0 each 32 ACTIVE single-shape cells. Original A1.7 result proves every 1000-step branch had **zero** post-contact local fully covered exact 2×2 region candidates; original 544 source group stages 5843 enumerations, 3973 nonoverlap, 0 exact cover; 545 stages 6397,4325,0. Native original step 1000 fusions0. All raw JSON, original code/seed/environment and SHA256 evidence is preserved in Git at `research/artifacts/a17_329_original_r2_fusion_reports.tar.gz.b64` and sibling manifest.

**Hypothetical null assumption (NOT authentic universe physics):** exactly `n` *distinct occupied logical sites* chosen **uniformly without replacement** from N=1024 sites, observed at a single time. There are 1024 toroidal anchored 2×2 blocks, each containing four distinct sites. For any one anchor:

`P(all 4 sites occupied | uniform n-subset) = (n)(n-1)(n-2)(n-3) / [1024·1023·1022·1021]`.

Therefore by linearity, exact **expected count** of fully occupied 2×2 blocks:

`E_n = 1024 * n(n-1)(n-2)(n-3) / [1024·1023·1022·1021]` for n>=4, else zero.

Results under this **uniform snapshot model** (not measured probability for R2):

| Hypothetical number of distinct occupied sites | Expected exact 2×2 blocks per snapshot |
| ---: | ---: |
| 32 | 0.000808497447570073 |
| 27 | 0.000394580928944794 |
| 22 | 0.000164464928503200 |
| 11 | 0.000007419470458791 |

For 1000 hypothetical time snapshots, each having uniform distinct occupancy with **at most** 32 sites, linearity of expectation alone gives total expected block appearances **at most 0.808497447570073**. This expectation summation does **not** assume the times are independent, only the specified per-time uniform marginals. It is not a statement that the real deterministic time series follows this null, nor a measured probability of first fusion. There may be overlapping blocks in one snapshot, and any number of post-geometry bond/velocity/lifecycle failures.

## What cannot be inferred

Real `create_universe` coordinates come from native deterministic initial event IDs; `step` moves each cell at its configured vector, collides and damages, accumulates/decays bonds, and applies lifetime transitions. This creates **spatial and temporal correlations**. Several active cells may occupy one tile, hence actual distinct occupied tiles <= active cells; comparing nActive directly to the mathematical nUnique is only a hypothetical upper-input illustration. No proof exists that actual sites are uniform independently sampled without replacement at any time. The value `E_32` is **not** the original probability of full cover, not a statistical p-value for the observed zero, and not a proof that deterministic geometry is the sole cause. Conversely zero full covers is compatible with sparse occupancy under the reference model.

The fixed old R2 observations preclude asserting a deficiency in bond>=32 or relative velocity<=8, since there were exactly zero candidate groups that met the preceding geometric gate. Avoid changing bond threshold merely to increase fusion count. Do not silently substitute generated bit variation for teacher-specific causal information.

## Decision and next research gate

**CHANGE_PATH** toward geometry production/physical motion as the first source-local reachability question, before mask width, bond tuning or introducing `masked_xor` or `rotate_copy`. This simple exact reference is sufficient to show why the absence of four-cell blocks at sparse occupancy is not self-evidently an engine bug. It does not make any alternate physical design an accepted learning solution.

For future *new* physical hypotheses, first freeze a single intervention and no-teacher/sham counterfactual, the original/unmodified physics baseline, independent disjoint Seed/held-out rosters, full 2×2/contact/bond/velocity/receiver-state/lifetime stage gates, original checkpoints/hashes, >=12/16 accepted memory gate where applicable, and time<=900 sec/host RSS<=1536MiB before reading outcomes. **Design-only** stage here; independent physics run, modification to production default and R3/PhaseH/L4-L7 remain HOLD. All durable evidence goes to the Git repository, not Google Drive.

The exact integer arithmetic lives in `research/a18_geometry_null_326.py` with matching deterministic tests `tests/test_a18_geometry_null_326.py`. Neither calls `create_universe`, `step`, nor consumes a seed.
