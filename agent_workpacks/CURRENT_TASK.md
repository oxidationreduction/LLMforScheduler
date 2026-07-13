# 当前任务

围绕本仓库计划并完成一篇 AAAI 风格会议论文，主题是“带独立验证器的工业启发式排产引擎”。

## 总目标

构建论文和实验材料，支撑以下核心观点：

> 工业工厂订单排产不应被包装成 LLM 直接生成完整排班的问题；本文主线是 verifier-backed industrial heuristic scheduling engine：确定性多策略启发式排产器生成分钟级可执行排班，独立 verifier 负责硬约束验收，LLM 相关实验最多作为附录动机或负例。

## 当前已有证据

- 数据集：`raw_orders/` 下有 670 个原始订单 JSON。
- 主结果目录：`results/raw_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/`。
- 主 HTML 目录：`results/html_view/all_machine_capacity_dynamic_chunk25_20260626_tl120/`。
- 现有全量结果摘要：
  - cases：670
  - feasible：560
  - optimal：16
  - infeasible_proven：94
  - verify ok：576
  - unsolved：0
  - total time：195.741s

## 时间和资源

- 所有实验必须在 14 天内完成。
- 默认不新增 GPU 训练或推理任务。
- 如果项目主管后续明确恢复 LLM/SFT 路线，训练默认使用 4 张 RTXPRO6000；推理可使用 8 卡，A6000 每卡任务数按 RTXPRO6000 的一半配置。
- 排产器、verifier、OR-Tools 主线主要使用 CPU。

## Agent 提交流程

- 所有会修改仓库文件的 agent 任务均在项目主管指定基线之上的独立 `agent/<agent-name>/<task-slug>` 分支完成；每个任务结束时必须提交本任务改动。
- 禁止直接向 `main` 或当前集成分支提交，也禁止自行合并、rebase、force-push 或改写历史。
- 禁止提交单个超过 50 MiB 的文件，不得以 Git LFS、压缩或拆分规避；提交前检查暂存范围、`git diff --check` 和暂存文件大小。
- 任务 agent 在 `HANDOFF.md` 报告 branch、commit、文件、验证、artifact 和风险；项目主管检查后决定是否合并。

## 论文定位

- 目标：AAAI 风格 applied AI / agent systems 论文。
- 核心定位：带独立 verifier 的工业启发式/规则组合/portfolio scheduler。
- 不把当前仓库描述成已经完整具备 LLM 训练/推理框架。
- 不把 LLM direct generation 或 LLM tool-agent 写入主方法比较；E5/E6/E7 暂停主线，仅可作为附录动机候选。
- 不声称全局最优；除非是库存完全抵消后的零任务 case。
- 不声称不可行证明完备；只能说容量下界可证明的一类不可行。
