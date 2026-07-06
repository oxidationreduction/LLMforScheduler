# experiment_manager_agent Handoff

## 当前状态

第一步已完成：split manifest 和现有 timed_greedy 基线 metrics 已冻结，并已登记到共享产物表。

关键产物：

- `experiments/aaai2026/split_manifest.json`
- `experiments/aaai2026/metrics_timed_greedy_existing.json`
- 参考 summary：`results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/summary.json`

关键数字：

- split：train 473，dev 64，test 133。
- OOD/recent：2025-only，共 64，作为 test 内额外标签。
- existing timed_greedy：670 cases，576 verify ok，94 infeasible_proven，0 unsolved，0 verify invalid。

## 已完成任务

1. 审计已有全量结果 summary。
2. 定义 train/validation/test/OOD split：
   - Train：2020-2023。
   - Validation：2024H1。
   - Test：2024H2-2025。
   - OOD/recent：2025-only。
3. 定义指标：
   - verify ok rate；
   - infeasible_proven count；
   - unsolved rate；
   - verifier error count；
   - runtime mean/median/p90/p95/max；
   - task count；
   - makespan；
   - resource balance。
4. 将 split 和 metrics 产物登记到 `shared/ARTIFACTS.md`。
5. 将 E0 更新为 complete。

## 下一步

- `dev_runner_agent` 启动 E1：用 tmux 复现 full 670 solver。
- E1 目标核对：576 verify ok、94 infeasible_proven、0 unsolved。
- 新复现结果必须写入新目录，不覆盖既有主结果目录。
