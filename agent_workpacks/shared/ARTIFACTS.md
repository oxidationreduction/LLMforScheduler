# 产物登记表

所有长期保留的实验和论文产物都要登记在这里。smoke 测试临时文件清理后不要登记。

| 产物 | 生产者 | 路径 | 状态 | 备注 |
|---|---|---|---|---|
| 已有全量结果 summary | 既有结果 | `results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/summary.json` | available | 670 单，576 verify ok，94 infeasible_proven |
| 已有全量 HTML index | 既有结果 | `results/html_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/index.html` | available | 可视化 case 浏览入口 |
| 旧版 solver summary | 既有结果 | `results/raw_view/all_machine_capacity_dynamic_20260626_tl120/summary.json` | available | 旧对照，1 个 time_limit |
| AAAI 2026 实验框架 | dev_framework_agent | `experiments/aaai2026/` | available | split、metrics、LLM tool schema、SFT data、direct baseline validator |
| AAAI 2026 split manifest | experiment_manager_agent | `experiments/aaai2026/split_manifest.json` | available | 670 单；train 473，dev 64，test 133；2025-only OOD/recent 64 |
| 现有 timed_greedy 基线 metrics | experiment_manager_agent | `experiments/aaai2026/metrics_timed_greedy_existing.json` | available | 670 单；576 verify ok，94 infeasible_proven，0 unsolved，0 verify invalid |
| E1 full 670 复现 summary | dev_runner_agent | `results/raw_view/e1_full670_repro_20260703_232018/summary.json` | available | 670 单；576 verify ok，94 infeasible_proven，0 unsolved，0 verify invalid；elapsed 167.628s |
| E1 full 670 复现 metrics | dev_runner_agent | `experiments/aaai2026/metrics_e1_full670_repro.json` | available | 与 existing baseline case-level 状态一致；coverage 1.0 |

## 产物规则

- 新实验必须写入新结果目录。
- 不得覆盖已有结果。
- 每个实验输出应包含机器可读的 `summary.json` 或 `metrics.json`。
- 长任务日志只有在复现或解释结果需要时才保留。
