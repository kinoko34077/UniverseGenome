# #326 — Native contact readout: next mechanism-first design checkpoint

**Status: DESIGN ONLY / NOT APPROVED TO EXECUTE.** Owner [#326](https://github.com/kinoko34077/UniverseGenome/issues/326); parent [#171](https://github.com/kinoko34077/UniverseGenome/issues/171) remains design-only. Exact accepted previous source main `d482f2f9e3a74adb1598d81dfe5fd51524aa8a06`.

## What the completed genuine trial established

Completed [#336](https://github.com/kinoko34077/UniverseGenome/issues/336) exposed-only `rotate_copy(4)` native experiment genuinely created multiple active latent words from homogeneous original conditions. Its authentic report and classification [are preserved in Git](../../research/artifacts/a2_e2_336_original_exposed_544_545_run38544898470_evidence.md): 740 source-native B/H directed contacts with equal nontrace context, 72 source-trace differences, 35 selected-mask differences, **zero recipient-after latent differences**. The source archive does **not** contain all 35 paired event inputs, so no literal mask-bit distribution is asserted. This is a valid negative in exposed conditions only; no independent learning or generic impossibility result.

## Mechanistic alternative chosen for prospective *design*, not execution

Compare exact existing local operator effects under **one matched precontact** with identical actual native source-latent word `S`, recipient prelatent `D`, and branch masks `M_B,M_H`. Let `ΔM=M_B XOR M_H`, `R=rotl16(S,4)`. For 16-bit operations:

| Original source-native operator | Exact predicted `after_B XOR after_H` |
|---|---|
| `masked_copy` | `(S XOR D) AND ΔM` |
| `rotate_copy(4)` | `(R XOR D) AND ΔM` |
| `masked_xor` | `S AND ΔM` |
| `masked_and` | `(D AND NOT S) AND ΔM` |

These are identities from unchanged `core.physics.apply_latent_operator`, independently evaluated over **9,604 synthetic tuples** in `tests/test_a1_6_effective_contact_readout_design_326.py`. This synthetic exercise is **not a universe step or contact observation**.

The present *single-candidate design hypothesis* is `masked_xor`: its immediate conditional **difference** does not depend on the existing recipient word `D` as long as the source and recipient precontexts are genuinely equal between B/H. This avoids the additional `R XOR D` cancellation seen with `rotate_copy(4)`. Example, with `S=D=1` and masks `0` vs `1`, original `masked_copy` produces no difference, `masked_xor` produces difference `1`. But native bit0 mask variation and selected directed contact availability have NOT been shown for any new exploratory cohort. XOR toggles/erases bits and may manufacture teacher-independent variation, so this mathematical property does not establish physical memory, teacher-specific causality or lifetime persistence.

The old **4/36 vs 8/36** original-contact retrospective results did **not** select the candidate: comparing these as real success rates would be invalid because neither came from prospective modified-operator trajectories and the 36 conditions are outcome-exposed.

## Falsifiable, pre-outcome stages for a future separately authorized owner

1. Freeze exact implementation, unchanged initial state/h0 qualification, source and control SHA, seed eligibility, excluded old outcome-exposed cases and reserved holdout, and the native one-factor operator delta. No currently selected new seeds and **no native run**.
2. Observe **authentic** physical selected directed contacts with source/destination life-epoch keys and full precontact nontrace context. Exclude mismatched topology/context before calculating any teacher contrast. Count every denominator, not just contacts with favorable masks.
3. For an equal-precontext B/H contact, verify B/H source-trace difference, native-selected-mask difference, and `source_word AND mask_delta != 0` before even considering an effective XOR read. Compare the *actual* recipient-after source-native values to the algebraic predicted difference. A bit-support overlap observed in a synthetic fixture is not authentic contact reachability.
4. Require same-teacher B/B repeat equality, negative sentinel B/H full-state equality, source-distinct no-teacher characterization (never equate it to B/B sham), original unchanged golden default, instrumented/uninstrumented parity, original host and source SHA, and resource caps. If the real positive contact denominator is zero/confounded or validity fails: classify **NOT_EVALUABLE**, not zero causal response.
5. If immediate true recipient differentiation is observed, separately require first/last native carrier life epochs and +1000 state/lineage evidence, then independent frozen R3 acceptance on genuinely disjoint new cohorts. Neither an immediate XOR change nor active-population word diversity is learned input→output.

The machine-readable, **nonexecuting** [design contract](a1_6_effective_contact_readout_design_326.json) is intentionally under `docs/research`, outside any executable research runner; it asserts `can_run_actions=false`, `new_seed_ids=[]`, no change to marker/Action/source lock/core/defaults, and prohibits Phase H 96–159 and new R3 seed consumption. It is not a fully approved prospective study protocol or a basis for automatic dispatch. A new study requires a separate owner, predeclared source-blind sham/negative and sample/threshold controls and scoped human approval **before** real outcomes.

Decision after this unit: **CONTINUE** source-only mechanism design until accepted; **SPLIT** any future legitimate effectful study with new authority; **HOLD** new physical seed/holdout usage; **STOP** repeating old 544/545/E2.
