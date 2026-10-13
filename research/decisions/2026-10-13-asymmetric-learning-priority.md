# UniverseGenome — 2026-10-13 research priority decision

Decision ID: `UG-RESEARCH-DIRECTION-2026-10-13`
Status: **ADOPTED RESEARCH ROADMAP / NO NEW PROSPECTIVE PHYSICS AUTHORIZATION**
Authority: user request on 2026-10-13, [#171 decision](https://github.com/kinoko34077/UniverseGenome/issues/171#issuecomment-6145337554), [#289 Outer disposition](https://github.com/kinoko34077/UniverseGenome/issues/289#issuecomment-6145363489), [#317 A1 experiment](https://github.com/kinoko34077/UniverseGenome/issues/317#issuecomment-6145355284).
Scientific source precedence: exact original source SHA + frozen case manifests + original Actions receipts > this compact index. This file is a decision record, not a substitute for raw evidence.

## Original scientific objective

`docs/spec/01_requirements.md` REQ-001: artificial universe with deterministic anonymous **local physics** and demonstrable within-universe autonomous learning, not hidden host semantic labels or conventional backprop. Outer source-native selected population may adapt genomes, but optimizer replacements alone do not establish Inner learning.

## Fixed evidence and environments

| Experiment | Source / environment | Scope | Authenticated result | Scientific limitation |
| --- | --- | --- | --- | --- |
| Outer D16 #217 | `e7f2efd0c9ec49afc53b9265ec4b17e936798160`, native CPython3.12 Linux, original seed16384 | 4 categories ×32 world slots ×37 rounds; 148 category-rounds | 56 absolute-failure world-slot retirements; growth-only E1=0, growth retirement E2=0 | Category-rounds not independent seeds |
| Outer D18.1 #294 | `f855a5da9e848088c4acc8c0397149b9c97cb69e`, native CPython3.12 Linux, new search-only seed49152 | 4×32 ×40, 160 category-rounds; 2 sequential hosts | 83 absolute-failure retirements; E1=E2=0; actual wall1757.748s <=1800s; Actions 38280937691 | No general impossibility of natural growth selection |
| R1 #172 | frozen R1 source and 24 h0 positives+8 negatives | matched teacher B66/H8, +1000 | generic post-h0 write suppression rescues 12/24 | No causal latent read/output |
| R2 #175 | original source `af568ac1558f2f3f86e51341208f5b51557b7a39`, frozen digest `3087009065925887d9db770d3d9bc216db1ff2deba0bc730a2bbdf0a8d9ba543`; 16+8 distinct original cohort | unit_add rate256, +1000 | 10/16 content distinct vs predeclared >=12/16; no certified turnover/read path | FAIL; old cases outcome-exposed |
| D7 #187 | original exposed seed575 B/H, matched receiver life epoch | +1000 | 51/51 identical actual source-read records at surviving recipient; no B/H-content effect | Single exposed case |
| A1.2 #317 / PR319 | old exposed R2 seed544 positive / seed545 negative, CPython3.12.15 and PyPy3.11.16 real Actions38394120581, source head `22ec914f64d9413d09db0b47696dc473f1b11428` | 1000 actual native physical steps, 6 exact original snapshots per branch, replay, matched contact | seed544: matched764, differing source trace95, quantized same width59, differing native mask36, differing recipient after latent0. seed545: matched966, zero B/H difference | Authentic selected events but observational only |
| A1.3 #317 / PR320 | old exposed R2 seed544/545, native original masked_copy, source head `63ca219f807e184408e0a42640c5a7496938dd4c`, real Actions38395344531, CPython3.12.15 / PyPy3.11.16 | replay and source-native algebra for exact B/H matched source/destination | **36/36** differing masks algebraically INERT: `((mask_B XOR mask_H) AND (source_latent XOR recipient_latent)) == 0`; negative545 zero differences; both runtimes' observation equal | Measured mechanism for exposed case only, no causal population-wide/generalization claim |

Outer total: 308 repeated category-rounds, 139 absolute-failure **world-slot** retirements, E1=E2=0. Native E1 gate requires four healthy mature per-category medians each >=2 and a healthy unprotected candidate with all four bitcounts below the halved median; original observed mature half-median thresholds all zero.

Original D18.1 ZIP SHA256: first20 `959dacacf297dec96b0f14bb7c702133ac585ae612eb3ba7fb9d13823647ded0`, full40 `f89580aac6fc8225a14d0730634ecf58023f20f7f5def777011324fd976a166c`. A1.3 original Actions ZIP SHA256: CPython `913f1b945227e85db75992b643866b076124ae1048b666c97f3562c7b92daa09`, PyPy `ab7a004b675b3a2ca7966aa575dba77fd96148a573cbd72cbe1b515bbb0f4103`, comparator `a9060b57044c9f44e18e5097ecbe13d84b21b34939d76c842eacad12d1e0b828`.

Native preservation: D18 `core/search/world` original unaffected; A1 observer and case recorders are additional `research/` and `tests/` only. A1 post-merge code commits PR318 `31a232af4e75bc1e333c5d2adbdda4f9d5e8fa51`, PR319 `47e2f59a9ecb2e90d38495c97b8ef12b37fa8293`, PR320 `cf9785295ddabd017b897988f619ba2b4abca4f0`.

## Common-axis comparison / decision

| Candidate | Relation to original goal | Near-term uncertainty reduction | Cost/seed risk | Decision |
| --- | --- | --- | --- | --- |
| A Outer-only | Indirect genetic adaptation | Low/medium after two true native negative cohorts | New selected128×37+ expensive; threshold-gaming, overfit/seed leakage | Do not prioritize |
| B Inner-only | Direct causal prerequisite for learning | High: native mask/latent bit effectiveness and persistent content | Source-only retrospective tests cheap, independent physics trial gated | Primary |
| C equal parallel | Both eventually useful | Wastes expensive Outer compute before new hypothesis | High coordination/compute | Not selected |
| D wholesale redesign/stop | Limits waste but discards still-testable B mechanism | Low until local native read pathway exhausted | Unknown backward-compatibility tradeoffs | Conditional fallback |
| **C' B-primary, A bounded offline, PERF separate** | Addresses actual causal learning with independent adaptation evidence | **Highest current information gain per resource** | Current step low-cost, no new seed | **SELECTED** |

## Ordered roadmap and stop gates

1. **B1 accepted A1.3** (#317): source-native actual selected mask algebra no-op, CPython/PyPy exact parity and CI/review, no new seeds. PASS does not imply L3.
2. **B2 bounded latent-bit support analysis** (#317 or separately owned microtask): quantify original source/dest pre-latent variation, mask XOR positions, selected read-contact stages on *predeclared exposed* seed544/negative545. Does original source/destination mismatch have any bits at selected mask differences? If no, classify low active latent contrast; do not widen masks or hand-design teacher target bits. End on a falsifiable mechanism statement, not broad tuning.
3. **B3 independently predeclared prospective causal contrast** (new Issue only if B2 warrants): ONE legitimate teacher-blind local physical intervention and matched sham/negative, source SHA, seed roles disjoint from R1/R2/Phase H reserved, fixed window/output/limits, source-native replay, action & latent proof. A failed result is retained and triggers CHANGE_PATH.
4. **B4 R2-compliant candidate → R3 independently held-out L3 persistence → R4 L4 input-conditioned recall → R5 L5-L7 autonomous behavior** (one separate authorized gate each). No jump over failed gates; until then `learning_claim=false`, D1 inert tuple `(0,0,0,0,8)`.
5. **A1 Outer source-only data sufficiency audit** (#289 or separate only if needed): can archived source-bound D16/D18 prove distributions of all four native score bitcounts, healthy maturity, failure and E1 thresholds and genotype support? If no authentic supporting fields: mark missing/NOT_EVALUABLE rather than fabricate. Do not run new physics just to obtain E2.
6. **A2 conditional new Outer cause** (new owner/independent freeze ONLY after a measurable A1 gap): assess genuine survival/score support then E1/E2 and independent actual fitness/generalization; no ad hoc threshold relaxation, no D16/D18 duplicate.
7. **PERF #275 separate**: native original seed0 PyPy performance37 2.664395887× wall but RSS2.50×; current full PyPy D15 long-lived four-worker resource admission fails. Opt-in only with original source/output parity and <=1536MiB RSS; CPython remains reference/fallback and historical environment.

## Durable artifact governance (user directive 2026-10-13)

**New preferred evidence owner: this repository, not Google Drive.** Commit compact original-context manifests, evidence metrics, runtime environment, frozen seeds/config, code/protocol SHA, hashes, negative outcomes and links into `research/artifacts/` under normal Issue/branch/PR/CI/Review/merge governance. Preserve raw compressed source-bound original data in Git objects when size and reproducibility make it worthwhile. Avoid repeated large copies, giant derived cache files or losing decisive original input/condition data. Existing Drive files remain historical backups; do not delete them or mislabel links as repo-native data.

No unauthorized publication, release, credentials/permissions, or destructive operation. New effectful native science runs require new frozen protocols and applicable authorization. No D16/D18 seed repetition or surprise full-app PyPy default switch.
