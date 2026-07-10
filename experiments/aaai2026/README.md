# AAAI 2026 Experiment Harness

This directory contains the minimal experiment interfaces for the verifier-backed
tool-agent paper track. Scripts write only to paths passed with `--out`; long
experiment runs should still be launched and monitored by `dev_runner_agent`
inside tmux.

Primary entry points:

- `build_split_manifest.py`: date-based train/dev/test split plus 2025 OOD tag.
- `build_stratified_manifest.py`: deterministic stratified subset manifests.
- `aggregate_metrics.py`: summary metrics by run, split, and difficulty bucket.
- `llm_tool_schema.py`: strict JSON tool-call schema and parser.
- `run_llm_tool_agent.py`: JSONL prepare/execute harness for tool-agent runs.
- `build_sft_data.py`: strategy-selection SFT data from verified solver outputs.
- `validate_direct_baseline.py`: verifier-backed direct LLM baseline checker.
