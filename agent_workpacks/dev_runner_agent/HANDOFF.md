# dev_runner_agent Handoff

## 当前状态

E1 full 670 solver 复现实验已完成并验收通过。当前没有本任务遗留 tmux session 或运行中进程。

## 运行规则

- 所有长任务都用 tmux。
- 使用唯一 session 名，例如 `llm_sched_e1_full670`。
- 日志和 summary 写入新结果目录。
- 长任务需要提供 watcher/status 文件。
- smoke 测试后删除临时文件，除非它们是必要 artifact。

## E1 任务单：复现 full 670 solver

### 目标

复现当前 full 670 timed_greedy solver 结果，验证主线 solver/verifier 在当前仓库路径下仍能得到同量级证据。

验收目标：

- case_count：670。
- verify ok：目标 576。
- infeasible_proven：目标 94。
- unsolved：目标 0。
- verify invalid：目标 0。

参考基线：

- split manifest：`experiments/aaai2026/split_manifest.json`
- existing metrics：`experiments/aaai2026/metrics_timed_greedy_existing.json`
- existing summary：`results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/summary.json`

### 输出要求

- 新结果目录必须写入 `results/raw_view/e1_full670_repro_<YYYYMMDD_HHMMSS>/`。
- 不得覆盖 `results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/` 或其它既有结果目录。
- 结果目录至少包含：
  - `summary.json`
  - `solutions/*.solution.json`
  - `solutions/*.verify.json`
  - `run.log` 或等价日志
  - `status.json` 或等价 watcher/status 文件
- 完成后用 `experiments/aaai2026/aggregate_metrics.py` 生成对应 metrics，例如：

```bash
python3 experiments/aaai2026/aggregate_metrics.py \
  --split-manifest experiments/aaai2026/split_manifest.json \
  --run e1_full670_repro=<E1_RESULT_DIR> \
  --out experiments/aaai2026/metrics_e1_full670_repro.json
```

### 启动规则

- tmux session 名称：`llm_sched_e1_full670`。
- 仅使用 CPU；不要占用 GPU。
- 启动前检查是否已有同名 tmux session；如存在，先确认它是否属于本任务，严禁误杀其它 session。
- 先做短 smoke：任选 1-3 个 `raw_orders/*.json`，确认 solver 和 verifier 能写入临时目录；smoke 临时目录完成后删除。
- smoke 通过后再启动 full 670 长任务。

### 执行注意

- 仓库没有专门的 full-670 runner 时，优先复用现有 `solver/schedule_solver.py`、`solver/verify_schedule.py`、`checker/check_schedule.py` 的 import/API 组合；如需新增 runner，先把最小脚本交给 `dev_framework_agent` 或项目主管确认。
- summary 字段需要兼容 `experiments/aaai2026/aggregate_metrics.py`，至少包含 `case_count`、`cases`，每个 case 包含 `case_id`、`status`/`solve_status`、`verify_status`、`solve_seconds`、`task_count`。
- `infeasible_proven`、`time_limit`、`no_solution_found` 等非可验证状态应写入 solution 和 summary；不可强行调用 verifier 当成 ok。
- 若结果偏离基线，先保留完整 artifact，并在 handoff 中报告偏离 case 列表和可能原因，不要覆盖重跑。

### 完成后交付

- tmux session 名称和最终状态。
- E1 结果目录路径。
- E1 metrics 路径。
- 与 existing baseline 的关键差异：
  - verify ok
  - infeasible_proven
  - unsolved
  - verify invalid
  - total elapsed/runtime 分位
- 更新 `shared/ARTIFACTS.md` 和 `shared/EXPERIMENT_REGISTRY.md`，或把精确路径交给 `experiment_manager_agent` 登记。

## 等待事项

- E1 已完成；等待后续 E2/E3/E4 等实验指挥。

## E1 完成记录：full 670 solver reproduction

- tmux session：`llm_sched_e1_full670`，full run 完成后自然退出。
- runner：新增 `solver/run_full_benchmark.py`，复用现有 `schedule_solver`/`verify_schedule` API；未修改 solver/verifier 核心逻辑。
- CPU-only：full run 使用 `CUDA_VISIBLE_DEVICES=""`，未占用 GPU。
- smoke：`SO-2020-10-0002-2` + `SO-2020-11-0001-2` 通过，临时目录已删除。
- 结果目录：`results/raw_view/e1_full670_repro_20260703_232018/`
- summary：`results/raw_view/e1_full670_repro_20260703_232018/summary.json`
- status/watcher：`results/raw_view/e1_full670_repro_20260703_232018/status.json`
- 日志：`results/raw_view/e1_full670_repro_20260703_232018/run.log`
- metrics：`experiments/aaai2026/metrics_e1_full670_repro.json`

关键数字：

- case_count：670。
- verify ok：576。
- infeasible_proven：94。
- unsolved：0。
- verify invalid：0。
- coverage_rate：1.0。
- elapsed_seconds：167.6277772031026。
- solve_seconds：mean 0.2331358470，median 0.0775131771，p90 0.4924942168，p95 0.7600731058，max 15.0109289760。

与 existing baseline 的差异：

- baseline ok 但 E1 非 ok：0。
- baseline infeasible 但 E1 非 infeasible：0。
- E1 新增 infeasible：0。
- E1 新增 ok：0。
- manifest missing cases：0。
- manifest extra cases：0。
