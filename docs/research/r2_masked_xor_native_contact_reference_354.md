# #354 — Masked XOR native contact witness: reference-only acceptance boundary

Owner: [#354](https://github.com/kinoko34077/UniverseGenome/issues/354). Parent [#171](https://github.com/kinoko34077/UniverseGenome/issues/171) remains **DESIGN ONLY**. The accepted h0 proposal [PR356](https://github.com/kinoko34077/UniverseGenome/pull/356) has been merged; future exploratory 2048..2559 seeds are NOT independently cleared, qualified, or executed. No native experiment has been performed by this reference.

## Scope

`tests/support_r2_masked_xor_contact_354.py` is **pure reference validation of externally supplied records only**, not a source-native observer. It cannot establish that any supplied records are authentic physical events. The separate, future native observer and runner require new exact-source verification, golden test, control/role freeze, CI, preflight and accepted scientific gates before applying standing approval to a single bounded physical study.

Each purported directed selected contact must use the exact accepted A2 contact keys (native generation, physical address, source/recipient slot, source/recipient life epoch), full observed nontrace precontact fields and the current source-selected native mask and recipient-after latent value. Unlike the old immutable `rotate_copy(4)` witness, this candidate requires `native_operator=masked_xor`, `rotate_amount=0`, and a direct check of `apply_latent_operator` against the *actual asserted native* recipient-after. The selected-mask bit count must match the existing width derived from source bond and slow trace. Missing, extra, malformed, duplicate or impossible events cause invalidation.

For B/H events with the same contact key and identical observed nontrace precontact context (including source and recipient before-latent):

```
recipient_after_B XOR recipient_after_H
  = source_latent_before AND (native_mask_B XOR native_mask_H)
```

Count and report *all* directed events, matched contact keys, unmatched keys, confounded precontexts, comparable precontexts, source-trace differences, native-mask differences, effective source-mask overlap and actual recipient-after changes. Same slow trace and otherwise equal context must not produce different selected masks under a valid fixed native RNG/schedule. Empty comparable denominators → `NOT_EVALUABLE_NO_SEED_REPLACEMENT`; valid comparable contacts with zero recipient changes → `NEGATIVE_NO_MATCHED_RECIPIENT_EFFECT`; one or more genuine conditional recipient differences → at most `LOCAL_RECEIVER_EFFECT_RETENTION_UNRESOLVED`.

## Evidence restrictions

The test fixtures fabricate event dictionaries to exercise arithmetic and rejection boundaries. **Their values are not authentic Seed observations, not proof of physical mask reachability, and not teacher-dependent information transfer.** A source-matched event still does not establish randomized teacher causality; carrier identity/turnover across +1000 and a distinct held-out cohort require separate authenticated study and independent gates. The current reference always returns `native_source_provenance_verified_here=false`, `actual_native_experiment_executed_here=false`, `long_term_retention=NOT_ESTABLISHED`, `independent_confirmation=false`, `learning_claim=false`.

This PR changes only tests plus this explanation; it does not modify `research/a2_matched_recipient_contract_336.py`, existing E2 scientific source-lock blobs or used marker, physics/defaults/Action, new seed rosters or h0. All genuine masked_xor native activity remains HOLD pending study-specific full source and cohort preregistration. The user has granted standing in-scope authorization for bounded research after these gates; no redundant permission question is needed once genuinely met.
