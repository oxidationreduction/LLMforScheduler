# E4 CP-SAT Stratified-50 Table Candidate

This is an E8 table candidate, not a paper-ready table row. Do not merge E4
into paper-ready tables until `qa_repro_agent` records E4 artifact QA PASS.

E4 must be labeled as `CP-SAT stratified-50 baseline, 120s/case`. It is not a
full-670 result and must not be compared with E0-E3 by equal case count.

## Source Artifacts

| Artifact | Path |
|---|---|
| Manifest | `experiments/aaai2026/e4_cpsat_stratified50_manifest.json` |
| Summary | `results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/summary.json` |
| Metrics | `results/raw_view/e4_cpsat_stratified50_tl120_20260709_153557/metrics.json` |

## Candidate Row

| Row | Scope | Time limit | Cases | Coverage | Status counts | Verify counts | OK | Infeasible | Unsolved | Invalid | Method counts | Elapsed | Solve seconds mean/p50/p90/p95/max |
|---|---|---:|---:|---:|---|---|---:|---:|---:|---:|---|---:|---|
| CP-SAT stratified-50 baseline | stratified 50 subset | 120s/case | 50 | 1.0 | feasible 42, optimal 2, infeasible_proven 6 | ok 44, not_applicable 6 | 44 | 6 | 0 | 0 | timed_cpsat 39, timed_cpsat_batched 11 | 265.907s | 5.305 / 2.395 / 13.952 / 19.366 / 38.795 |

## Manifest Scope

- Parent manifest: `experiments/aaai2026/split_manifest.json`.
- Source case count: 670.
- Sample size: 50.
- Split counts: train 35, dev 5, test 10.
- Difficulty counts inferred from strata: easy 17, medium 17, hard 16.
- OOD/recent count: 4.
- Sampling policy: stratified by split and difficulty, largest-remainder quota, deterministic SHA256 order with seed `20260703`.

## QA Gate Requirements

Before paper-ready inclusion, `qa_repro_agent` must record E4 artifact QA PASS:

- Manifest, summary, and metrics JSON parse successfully.
- Manifest confirms 50 cases sampled from 670, with split counts train 35 / dev 5 / test 10 and split+difficulty stratification.
- Metrics coverage is 1.0 with expected_case_count 50.
- Summary and metrics agree on 44 ok, 6 infeasible_proven, 0 unsolved, and 0 verify invalid.
- `method_counts` contains only CP-SAT methods: `timed_cpsat` and `timed_cpsat_batched`; no `timed_greedy`.
- No 600s appendix result or other result directory is mixed into this candidate.

## Claim Boundaries

Allowed claims:

- E4 is a `CP-SAT stratified-50 baseline, 120s/case`.
- E4 achieved 44 verifier-ok schedules and 6 infeasible_proven cases on the stratified-50 subset.

Forbidden claims:

- Do not present E4 as an LLM result.
- Do not present E4 as the main method result.
- Do not present E4 as a full-670 result.
- Do not claim global optimality or complete real-world infeasibility.
- Do not claim industrial KPI evidence.
- Do not make direct case-count-equivalent comparisons against E0-E3 full-670 rows.

## Post-QA Action

After E4 artifact QA PASS appears, create
`experiments/aaai2026/e0_e4_paper_table_draft.md`. Keep E0-E3 full-670 rows
together and add E4 in a separate CP-SAT stratified-50 section or clearly
separated row group.
