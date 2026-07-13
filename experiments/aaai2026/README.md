# AAAI 2026 Experiment Harness

This directory contains the minimal experiment interfaces for the
verifier-backed industrial heuristic scheduling paper track. Scripts write only
to paths passed with `--out`; long experiment runs should still be launched and
monitored by `dev_runner_agent` inside tmux.

Current paper strategy:

- Primary track: H1-H6 heuristic scheduler evidence.
- H1-H3 reuse full-670 E0-E3 heuristic/ablation artifacts.
- H4 reuses the E4 `CP-SAT stratified-50 baseline, 120s/case` artifact.
- H5/H6 are the next planned complexity and verifier case-study outputs.
- E5/E6/E7 LLM/SFT/direct-generation work is paused and may only be used as
  appendix/motivation if the project manager explicitly reopens it.

Primary entry points:

- `build_split_manifest.py`: date-based train/dev/test split plus 2025 OOD tag.
- `build_stratified_manifest.py`: deterministic stratified subset manifests.
- `aggregate_metrics.py`: summary metrics by run, split, and difficulty bucket.
- `heuristic_replan_experiment_plan.md`: H0-H8 project strategy.
- `h_series_heuristic_table_draft.md`: heuristic-first paper table draft.
- `h5_h6_next_phase_task_brief.md`: assigned H5/H6 outputs and acceptance
  rules after H-series table QA PASS.

Paused appendix interfaces:

- `llm_tool_schema.py`: strict JSON tool-call schema and parser.
- `run_llm_tool_agent.py`: JSONL prepare/execute harness for tool-agent runs.
- `build_sft_data.py`: strategy-selection SFT data from verified solver outputs.
- `validate_direct_baseline.py`: verifier-backed direct LLM baseline checker.
