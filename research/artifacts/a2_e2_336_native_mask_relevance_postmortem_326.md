# A2 E2 original-exposed negative — source-bound native readout mechanism audit

- Analysis owner: [A1.6 design #326](https://github.com/kinoko34077/UniverseGenome/issues/326)
- Completed trial owner: [#336](https://github.com/kinoko34077/UniverseGenome/issues/336) (closed as valid negative)
- Parent [causal-to-learning roadmap #171](https://github.com/kinoko34077/UniverseGenome/issues/171) remains **DESIGN ONLY**
- Authenticated actual [Action 38544898470](https://github.com/kinoko34077/UniverseGenome/actions/runs/38544898470), attempt 1, source `c5bb3429159098a4be4eef547dbb044c552a7f4c`.
- Byte-exact archived GitHub ZIP: `research/artifacts/a2_e2_336_original_exposed_544_545_run38544898470.zip.base64`. SHA256 of *decoded ZIP* `04a502b7ec7a908d87b1053e26e068f4b9592c9148b796f25b287bc983f89c27`; internal actual native JSON SHA256 `cb321787f18592e981aadc28d008efaf6ff0626f2299ff41cdfb4fa5233bcc8c`; F5 decision SHA256 `16b37df9a03aca47d6cbfc0f26d18c8fb9991feea3d47014a97c44d90e70530c`.
- Companion pure read-only regression: `tests/test_a2_e2_negative_mask_relevance_326.py`. It authenticates the ZIP and derives exact bitwise predictions by calling existing `core.physics.apply_latent_operator`. It does **not** create or step a universe, replay seed544/545, or modify the scientific outcome.

## 1. Two different mechanistic stages

The original source `masked_copy` case had only the homogeneous latent word `1` under native matched selected contact in the previous exposed A1.5 study. The new single intervention `rotate_copy(4)` after original h0 produced real **latent alphabet diversification**, despite **zero fusion** and **zero fragmentation** in all archived treatment branches:

| Authentic +steps | seed544 B distinct words | seed544 H distinct words | seed544 original no-teacher distinct words | seed545 B | seed545 H |
|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 1 | 1 | 1 | 1 |
| 10 | 1 | 1 | 1 | 3 | 3 |
| 100 | 6 | 6 | 6 | 3 | 3 |
| 250 | 8 | 8 | 8 | 9 | 9 |
| 500 | 8 | 8 | 8 | 10 | 10 |
| 1000 | 3 | 3 | 3 | 6 | 6 |

At +1000 the seed544 B/H/no-teacher conditions have 11 active cells; seed545 B/H 13 active. The *count of distinct latent words* is not a signature of which teacher produced them. In this actual experiment the source-distinct seed544 no-teacher branch has the SAME full authoritative checkpoint SHA as H at `h0,+1,+10,+100,+250,+500,+1000`, but a different SHA from B. That is an observed equality in this particular frozen h0, not a claim that every no-teacher control is equivalent to H or that B's global-state difference is a native transferred latent memory.

The second, essential stage is **teacher-dependent source trace differences causing DIFFERENT ACTUAL RECIPIENT LATENT VALUES under comparable local conditions**. The genuine positive544 B/H native paired physical events showed:

| Source-locked physical observation | Count |
| --- | ---: |
| Genuine directed contacts in each branch | 764 |
| Paired native contacts | 764 |
| Matched nontrace precontact context | 740 |
| Precontext-confounded contacts (excluded) | 24 |
| Different source trace in 740 valid contacts | 72 |
| Different source-selected native mask in 740 | 35 |
| Different actual recipient postlatent in 740 | **0** |

Thus this treatment has already satisfied the **native alphabet variety is possible** property on the old-exposed host; it has NOT satisfied actual B/H information readout on the same matched contacts. The first property neither implies the second nor implies retention, semantics, independent L3, output learning or L7.

## 2. Exact bit-level reason a different mask can be ineffectual

This is an algebraic identity of **already existing** `core.physics.apply_latent_operator`, not a new empirical hypothesis or a rewritten operator.

For an otherwise identical native local contact let `S` be the source latent, `D` the recipient latent before transfer, `R=rotl16(S,4)`, and `M_B, M_H` the source-selected masks from B and H. The existing operation is

```text
output(S,D,M) = (D & ~M) | (R & M)
              = D XOR ((D XOR R) & M)      [within 16 bits]

output_B XOR output_H = (D XOR R) & (M_B XOR M_H)
```

Consequently, **a mask difference is necessary but not sufficient** to create a recipient-latent difference at equal nontrace/source+recipient precontext. The extra necessary and sufficient factor is that one of the *different mask bits* coincides with an actual `R XOR D` bit. A changed mask on an irrelevant bit does nothing to the recipient output.

For the authentic 35 mask-differing, equal-precontext pairs, the F5 scorer observed zero postlatent difference. Given the exact existing operator and the source/recipient-latent precontext equality enforced by the contact comparator, these pairs satisfy `(D XOR R) & (M_B XOR M_H) == 0`. This explains **how** a real mask contrast and no receiver contrast can coexist; it does **not** identify the exact source/recipient word and mask positions for each historical event.

Historical A1.9 *one-contact* hypothetical original masked_copy trajectory used original event masks with constant source=dest=1 and reported `rotate_copy(4)` possible receiver differences 8/36. The actual E2 study continued with altered physics and newly selected native masks, hence 0/35 real postlatents. The 8/36 *retrospective static counterfactual* is NOT a prediction validated in the genuine changed-physics trajectory; the event contexts and masks need not be equal across counterfactual and treatment.

## 3. Evidence ceiling and legitimate next experiment design

The archived original native E2 JSON contains genuine counters, per-checkpoint hashes, distributions, selected-event hashes and only first/last selected witnesses. It does **not** include all 35 matched mask-different pairwise witness records. Therefore exact decomposition into `R XOR D`-support overlap at those individual 35 real historical contacts is a **logical aggregate consequence**, not separately archived event-by-event proof. Do not infer missing bit histograms, source-word frequency, carrier lineages or teacher-semantic causality from aggregate counts.

Before choosing any next effectful candidate, **separately predeclare and review** source-blind local mechanistic eligibility:
1. Reproducible physical precontact source/recipient bit diversity (not mere whole-population word count).
2. Native matched contact `mask_XOR` overlap with *operator-relevant* `source_transformed XOR destination` support. A mask difference alone is not a success.
3. True recipient-after B/H contrast at that matched contact, separate from confounded topology/state, with a same-teacher repeat and source-distinct no-teacher reference.
4. Carrier lifetime/turnover and +1000 lineage evidence separately, without claiming retention from word variety.
5. Immutable conditions, limited source-native cohorts, unseen and heldout roles isolated, no parameter sweep/posthoc seed replacement, <=1536MiB RSS / <=900s on host, frozen original default and no-learning claim.

The existing candidate set from #326/#334 includes local `masked_xor`, `rotate_copy`, native fusion eligibility and future architectural hypotheses. Neither the previous exposed `rotate_copy=8` versus `masked_xor=4` one-step hypothetical counts nor the latest zero real receiver differences authorizes choosing a new winner, modifying defaults, launching another exposed run, consuming independent R3>=1024/old Phase H96..159 or modifying acceptance thresholds.

**Disposition:** original A2 #336 = complete VALID NEGATIVE. Design-only #326 = continue source-only causal reachability/readout criteria, then explicitly select and freeze one scientifically justified prospective study in a separate owner before any new native outcome. Parent #171 remains DESIGN ONLY; `independent_confirmation=false`, `learning_claim=false`.
