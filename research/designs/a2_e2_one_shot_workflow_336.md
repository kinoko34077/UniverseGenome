# A2 E2 #336 — reviewed marker-only original-exposed native execution lane

Owner: [UniverseGenome #336](https://github.com/kinoko34077/UniverseGenome/issues/336); original h0 design authority [#334](https://github.com/kinoko34077/UniverseGenome/issues/334). Source/protocol accepted through [PR340](https://github.com/kinoko34077/UniverseGenome/pull/340) main `4e31da5883333801a3255172f052506ea943b1e2`. The user's explicit permission covers **only existing outcome-exposed R2 seed544/545** with the single new research-only physical operator `rotate_copy(4)` after original h0; independent and reserved seed sets remain protected.

**This PR installs NO activation marker and launches ZERO native original-seed studies.**

## Exact one-off trigger and source proof

`.github/workflows/a2-e2-original-exposed-336.yml` is configured for `push` **to main only** and only if `research/approvals/a2_e2_336.run` changed. No `workflow_dispatch`, schedule, pull request or other regular trigger. A separate future marker-only PR must first be reviewed and merged with a single squashed marker commit. On execution, the Job checks the checked-out git HEAD is GitHub's actual source SHA and **the previous-to-current commit changes exactly that one marker file**. If source files are changed in the same activation commit the job fails before any seeded physical step.

The separate marker must have exactly the predeclared ASCII bytes `A2-E2-336-EXPOSED-544-545-ROTATE4-ONCE\n`. Only then can the accepted `research/a2_e2_exposed_activation_336.py` check the original frozen R2 manifest and protected seed roster, exact checked-out Git HEAD, clean tracked code and old #334 DESIGN/HOLD provenance. Only then can `research/a2_locked_rotate_copy_pilot_336.py --execute --e2-exposed-only --source-sha "$GITHUB_SHA"` begin its native original-exposed cohort. The runner still independently checks old `masked_copy` checkpoints, positive544 B/H, negative545 B/H identical, positive B/B deterministic sham, distinct no-teacher h0, and instrumented/uninstrumented state parity. This pre-execution lane is not authority for any wider intervention.

Least privilege: `permissions: contents: read`, no token persistence, no repository write from Actions, no credentials/permission changes, no release/deploy. Host Ubuntu, Python3.12, 17-minute hard job timeout and GNU process timeout 900s; native code additionally has per-run RSS<=1536MiB and elapsed<=900s guards. Actual runtime remains unmeasured until the single run. Original research may be marked **NOT_EVALUABLE** due to a valid control failure or resource cap; no hidden criterion tuning or replacement seeds.

## Evidence lifecycle and scientific outcome

If and only if the one-run report validates frozen original controls and false learning claims, Actions uploads the raw compact JSON as artifact `a2-e2-336-original-exposed-raw` retained **5 days**. The run prints the report SHA256 and the actual matched native receiver counts; it does **not** publish the data or alter main. The original artifact is temporary: retrieval, byte-level verification and a separate reviewed Git-native evidence PR including source SHA, host/runtime, complete original conditions, raw JSON SHA256 and statistical decision are required for final accepted archival. If the run is NOT_EVALUABLE or fails, record exact failure in owning Issue and stop; no reruns of the exposed case with altered conditions.

**Important:** This workflow is source-only until a separate activation PR is reviewed and merged. The additional PR static guard tests on CPython3.12/PyPy3.11 do not create h0, run a world or consume seed. Future independent R3, Phase H and scientific learning claims are not unlocked by any old-exposed E2 result alone.

Sequence: (1) static-workflow current-head CI and formal review, source-only merge; (2) re-evaluate evidence gate and exact main state; (3) separately review/merge the marker-only PR if still within user's scoped consent and devflow; (4) verify exactly one authentic Action run and archive its bytes to Git. Missing step or unexpected failure => HOLD, not automatic substitution.
