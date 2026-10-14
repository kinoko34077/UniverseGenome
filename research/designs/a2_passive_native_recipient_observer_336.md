# A2 E1a — passive AUTHENTIC source-native contact capture, synthetic-only parity

Owner [UniverseGenome #336](https://github.com/kinoko34077/UniverseGenome/issues/336); E0 contact-schema [PR337](https://github.com/kinoko34077/UniverseGenome/pull/337) is already merged on `228690096002a8991d39aa21c3030188889db2a0`. Future actual experimental treatment remains **HOLD** by source [#334](https://github.com/kinoko34077/UniverseGenome/issues/334) and `research/protocols/a2_rotate_copy_preflight_334.json`.

## The actual validity gap closed

E0 established how to reject false matched contacts in serialized witness records. However it did not prove that a true `core.physics._transmit_latent` native selected source/recipient contact can be captured with every required field **without modifying its physical state, native mask, RNG or transmission order**.

`research/a2_passive_native_recipient_observer_336.py` solves that narrower problem by **reusing** the accepted existing `ReadOnlyReaderProvenance` implementation from A1 [#317](https://github.com/kinoko34077/UniverseGenome/issues/317), not duplicating an independent physics engine. A thin outer read-only wrapper around `core.physics.transmission_mask` calls the original function **exactly once** and snapshots full source/recipient coordinates, structure, direction, speed, HP, bond, both pre-latents, original source trace-start, original native mask, generation, physical spatial address and life epochs at the actual point the native selected mask is generated. The inner original A1 observer independently records both selected directed masks, real recipient postlatent values after the original native `_transmit_latent`, FREE and SPAWN life epochs. The two independent observations must agree on all shared fields; the strict E0 static witness schema validates the exact original native rotate_copy(4) result and mask width. Unknown/unmatched/nonselected event, duplicate physical-life key and source after-word mismatch cause hard error. Native `physics.step` is never replaced or modified.

This adapter can **only** attach to a clearly research-configured rotate_copy(4) `UniverseState` supplied by its caller. It does not configure the operator or create a universe. The caller's separate approval obligation for any actual scientific treatment is unchanged. The helper has no seed, teacher inputs, experiment driver or Actions dispatch path.

## Exactly bounded proof cases

The E1a tests construct exactly two synthetic `SHAPE_SINGLE` cells at an artificially shared tile in a world initialized empty with seed0, manually set trace 128 for one and 0 for the other, and research-only rotate_copy mode. A true one-generation native `core.physics.step` selects a compatible pair. The complete authoritative post-step `state.to_snapshot()` under the attached two-layer passive observer must equal a separately deep-copied **uninstrumented** identical native world after the exact same genuine step, and both directed post-latent fields must correspond to real selected masks. Source patch references are restored after observation; no mutation through the witness code.

A second artificial pair varies the pre-step source trace (128 vs0) solely to exercise native mask bit count and full E0 matched-contact comparison; this is **not a teacher-dependent scientific outcome**. Third fixture frees/reuses a slot to prove lifetime epoch increments, fourth refuses foreign/default copy mode and repeat use of observer.

The synthetic fixture is NOT original exposed R2 seed544/545, not a new independent R3 seed, not a physically evolved natural world, not a teacher learning event and not causal/longevity proof. Only the code's measurement-fidelity gap is addressed. No h0/heldout original population replay, no prospective physics intervention, no L3/learning claim.

## Acceptance, record and stop

- Verify real hosted CPython3.12/PyPy3.11 one-step native synthetic fixture, source+instrumented full-state parity, malformed/epoch/duplicate tests; ordinary Phase5/browser CI and formal exact-head source review; guarded merge and Issue #336 full source SHA/CI checkpoint.
- Future E1b must independently freeze exact actual original-R2 h0 control run, B/H positive544 vs negative545, B/B sham and distinct no-teacher h0, +1000 lifespan/recipient and budget gates, exact output schema/source before any real treatment.
- **HOLD E2** all actual altered-operator exploratory R2 seed544/545 physics, new/heldout seeds, full Action science workflow and default configuration or physics modifications until the exact future executable code/protocol and named intervention approval are explicitly accepted. `learning_claim=false`.
- After E1a acceptance: CONTINUE only if E1b closes a concrete missing validity gate, SPLIT any effectful future run, HOLD E2/E3; STOP unneeded synthetic fixture proliferation.

All evidence belongs directly to the UniverseGenome repository and Issue, never Google Drive.
