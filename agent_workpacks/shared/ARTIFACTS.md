# 产物登记表

所有长期保留的实验和论文产物都要登记在这里。smoke 测试临时文件清理后不要登记。

| 产物 | 生产者 | 路径 | 状态 | 备注 |
|---|---|---|---|---|
| 已有全量结果 summary | 既有结果 | `results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/summary.json` | available | 670 单，576 verify ok，94 infeasible_proven |
| 已有全量 HTML index | 既有结果 | `results/html_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/index.html` | available | 可视化 case 浏览入口 |
| 旧版 solver summary | 既有结果 | `results/raw_view/all_machine_capacity_dynamic_20260626_tl120/summary.json` | available | 旧对照，1 个 time_limit |

## 产物规则

- 新实验必须写入新结果目录。
- 不得覆盖已有结果。
- 每个实验输出应包含机器可读的 `summary.json` 或 `metrics.json`。
- 长任务日志只有在复现或解释结果需要时才保留。
