# A1.9 — original 36-contact local operator counterfactual (source-only)

Owner: [UniverseGenome #326](https://github.com/kinoko34077/UniverseGenome/issues/326), original existing physical source and A1.4 36 selected changed-mask event rows: `research/artifacts/a1_317_bit_support_native_2026-10-13.json`. Source research objective REQ-001 and accepted A1.5 / A1.7 negative outcomes. **No new physics, seed, environment or inference cohort executed.**

## Method — one native contact only

The original R2 positive exposed seed544 B66/H8 with source and destination true original latent=1 had 36 actual corresponding native selected contacts at which the original B/H trace changed the selected mask. Actual `masked_copy` recipient result was identical B/H on all 36. Negative exposed seed545 has zero changed-mask contacts.

The source-only implementation `research/a19_exposed_operator_counterfactual_326.py` reads exactly those **36 historical events** and uses the **existing genuine pure** `core.physics.apply_latent_operator` for each original mask B/H, with source=destination=1 held at the original accepted precontact values. It computes `hypo_B != hypo_H` for four already implemented operators, **once per original contact**. It never calls `step`, changes seeds, replays a physical trajectory, changes active states or edits a `PhysicsConfig`. It fails closed if any original mask, row schema or invariant fails.

| Existing native operator | Hypothetical one-contact recipient B/H differences / original 36 mask-different contacts | Mechanistic property |
| --- | ---: | --- |
| original `masked_copy` | 0 | Homogeneous src=dest=1 is closed under copy |
| `masked_and` | 0 | Homogeneous src=dest=1 remains unchanged |
| `masked_xor` | **4** | Fixed source bit0 toggled if selected mask bit0 differs |
| `rotate_copy` (rotate_amount=4) | **8** | Four mask-difference events at bit0 + four at rotated-source bit4, disjoint |

The XOR witnesses occur at original post-h0-relative generations **37, 299, 550, 680**. The entire 36-row source archive is retained in Git; all changed-output rows (with exact source/recipient slot, life epoch, address, masks and hypothetical outputs) are reproduced by this script and verified in tests.

## Interpretational boundary

This is a **retrospective, outcome-exposed, contact-local mathematical counterfactual**, NOT actual alternate-operator causal evidence. If a live physical universe were changed to `masked_xor` or `rotate_copy`, it could diverge immediately, and future physical positions, collisions, native contact masks, lifetimes and selected teachers would NOT equal the original historical set. Its 4/8 counts must not be described as an observed learned response, a future effect rate, survival, transfer of task-semantic teacher information, or independent confirmation. The negative seed545 control has no B/H changed masks **under its original physical trajectory** only.

The original R2 geometric fusion route is now established as **unreached by original 544/545**: 0 exact native 2×2 covers, even though a manually preloaded 4-single cover produces new word `0x1111`. In the original 32×32 world with only 32 initial active single cells, such 4-cell coverage is sparse under an explicitly hypothetical uniform null; that null is not the source-native probability of fusion. Therefore, a default-compatible fusion mechanism is possible but unobserved, while the original existing alternative operator families have local *conditional* changed-bit support on already selected contacts without requiring fusion.

## Decision axes and future experiment boundary

- **Default-compatibility** favors fusion with existing `masked_copy`, but exact physical geometry is unobserved; changing geometry/initial population is a **new physical intervention** with survival and selection effects.
- **Nearest copy-like operator** is `rotate_copy`: rotates original source bits and copies selected bits, but can also clear preexisting recipient bits and inject a shifted constant bit. Its 8 exposed contrasts are **not** grounds to optimize/select based on known outcomes.
- **Toggle operator** `masked_xor` may produce distinguishable outputs for mask bit0 but also spontaneously flip/erase recipient bits independent of teacher; 4 exposed contrasts are not a generalizable estimated success rate.
- Neither candidate demonstrates that the controlled B/H teacher content remains distinguishable after later collisions, cell turnover, negative/sham input or independent seed holdout.
- **Current permitted scientific operation:** lock one purely **design** hypothesis with native source SHA, physical config, disjoint unexposed seed roster, authentic B/H and no-teacher controls, real `step` and recipient lineage, memory 12/16 acceptance threshold, >= 1000-step long-term retention where relevant, run/host resources <=1536MiB RSS and <=900s. No prospective effectful study, production-default migration or PhaseH until those conditions are accepted under their own owner. Never consume heldout while retrospectively choosing the better-fitting operator from these exposed 36 events.

**Re-evaluation:** Two fundamentally distinct paths now exist — geometry-driven native fusion versus parameterized reader operator — and should be compared using cost, authenticity, causal teacher-specific readout, persistence, generalization and induced diversity/selection effects. Continue source-only preregistration, HOLD new physics cohort and `learning_claim=true`. This document is not an approval to run either candidate.
