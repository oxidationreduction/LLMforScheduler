# experiment_manager_agent Handoff

## 当前状态

已就绪。尚未收到新增实验结果。

## 初始任务

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
4. 为论文写手提供表格框架。

## 等待事项

- 开发框架 agent 提供代码路径。
- 开发运行 agent 提供复现实验和新实验 artifact 路径。
