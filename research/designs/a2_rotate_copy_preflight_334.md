# A2 — rotate_copy physical-reader candidate: exact preflight (DESIGN ONLY)

Issue: [UniverseGenome #334](https://github.com/kinoko34077/UniverseGenome/issues/334). Parent proposal [#171](https://github.com/kinoko34077/UniverseGenome/issues/171) and previous verified source-only learning analysis [#326](https://github.com/kinoko34077/UniverseGenome/issues/326). The **machine-readable source of this prospective draft's constraints** is `research/protocols/a2_rotate_copy_preflight_334.json`; validate with `python -m research.a2_protocol_preflight_334`. This command validates frozen metadata and actual source-mode semantics but NEVER runs native physics, creates a universe, qualifies new seeds, reads any hidden evaluation outcome or starts an Action.

## Fixed source references and design authority

- Reviewed reference main prior to drafting: `9c5db6b0012744c37b28cdf0509581d6f6ffe819`. New exact head hash will be recorded in owning Issue at current-head review.
- Immutable original R2 physics source: `af568ac1558f2f3f86e51341208f5b51557b7a39`. Accepted R2 manifest SHA256: `3087009065925887d9db770d3d9bc216db1ff2deba0bc730a2bbdf0a8d9ba543`.
- Original R2 `seed=544` is h0 B/H trace-positive, `seed=545` is B/H globally identical (not identical to no-teacher h0). Teacher B=66 and H=8; original research-only local `unit_add` writer, decay256; h0 state generation13 and teacher-free subsequent +1/+10/+100/+250/+500/+1000.
- These two seeds are **already outcome-exposed**. They may serve only as a later accepted *exploratory* source-native treatment/sentinel pair; they cannot confirm learning on unseen examples. Old Phase H reserved pool96..159, R1 160..543, R2 544..1023; independent R3 unseen floor>=1024 is **not touched by this draft**.
- Production `config/default.json` must retain `latent_operator="masked_copy"` and D1 slow-trace defaults `(write,transfer,discharge,decay,bonus_shift)=(0,0,0,0,8)`.

## Exactly one candidate

Alternative existing native `core.physics.apply_latent_operator("rotate_copy", src, dst, native_mask, rotate_amount=4)`. This rotates the physical source's 16-bit word left by 4 and performs original masked copy. It is a different local operator but still source-local, deterministic and no direct semantic/teacher target labels. The only permitted *hypothetical* `PhysicsConfig` change at the **clone after original h0** is `latent_operator: masked_copy -> rotate_copy`. h0 qualification and original training condition must NOT be retrospectively performed under alternate physics, and the current production operator and all native source code remain unchanged.

`masked_xor` is a possible alternative but is **not an additional candidate in this draft**. The earlier 36-event one-contact historical `rotate_copy` hypothetical B/H differences (8) vs `masked_xor` (4) are outcome-exposed bit algebra, NOT real changed-physics events, predictive success rates or grounds for a posthoc winner selection.

## Future empirical run prerequisites (NOT APPROVED)

A separate specifically authorized *physical execution protocol*, exact reviewed executable SHA, accepted original h0 hash, controls/sham observation and static budgets are prerequisites **before** the first prospective changed-physics action. The currently committed JSON has `can_run_actions=false` and `approval_state="HOLD"`. Test rejects any automatic enabling of these flags.

If a later independently accepted pilot is requested:

1. Replay original `masked_copy` as **baseline** and demand its six historical state golden SHA; candidate `rotate_copy` is switched exclusively after canonical original h0, so its **later** state must NOT be tested against those original-mask snapshots.
2. Preserve B/H positive544 and negative545 original h0 identity, plus identical B/B sham and a separate original no-teacher h0 branch. Negative545 B/H **candidate** must remain exactly identical. Do not require no-teacher h0 to equal B/H h0; it is a separately qualified control.
3. Observe native-selected physical contact `source slot + life epoch`, `recipient slot + life epoch`, actual trace + mask, true before and actual after recipient bits, matched vs nonmatched physical topology; distinct observed active latent words, irreversible carrier-free transitions and actual transfer. A trace or output-mask difference alone is not sufficient.
4. Predeclare checkpoint denominator, source-hash parity, rigorous source-generated event list, longest content-specific retention, and `NOT_EVALUABLE` policy for drift/sham failure. Time<=900 s/host, peak RSS<=1536MiB, compact primary results<=128 KiB. Archive exact executed source/host/raw JSON digest and conditions **to Git**, not Drive.
5. Any transient difference is **not L3**. Independent R3 test >=12/16 unseen, later L4 conditioned recall and eventually autonomous L7 A→B→NULL remain separate study levels.

## Exit/decision

- **CONTINUE** static protocol design, source-bound test, honest original seed partition, formal PR review and normal CI.
- **HOLD** any real modified-operator universe, Actions scientific rollout, new independent seed, heldout, physics/default change, or `learning_claim=true` pending separately accepted experimental protocol.
- **CHANGE_PATH** if candidate cannot preserve source-local causality or sham/negative validity.
- **SPLIT** any true physical pilot into the owner Issue with separate execution authority; do not add it to this preflight.
- **STOP** further source-only expansion once the accepted draft/test/Issue record covers the concrete unmet preflight gate.

The acceptance of this document/validator is NOT acceptance of the candidate's scientific effectiveness or authorization of new experiments.
