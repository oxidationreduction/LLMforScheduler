# 当前任务

围绕本仓库计划并完成一篇 AAAI 风格会议论文，主题是“带独立验证器的工厂订单智能排产 Agent”。

## 总目标

构建论文和实验材料，支撑以下核心观点：

> 工业工厂订单排产不应被包装成 LLM 直接生成完整排班的问题；更稳妥的路线是 verifier-backed tool-agent：LLM 负责计划、解释和工具调用，确定性排产器生成分钟级可执行排班，独立 verifier 负责硬约束验收。

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
- 可用 GPU：4 张 RTXPRO6000。
- GPU 只用于 LLM 推理或 LoRA；排产器、verifier、OR-Tools 主线主要使用 CPU。

## 论文定位

- 目标：AAAI 风格 applied AI / agent systems 论文。
- 核心定位：带独立 verifier 的 tool-augmented scheduling agent。
- 不把当前仓库描述成已经完整具备 LLM 训练/推理框架。
- 不声称全局最优；除非是库存完全抵消后的零任务 case。
- 不声称不可行证明完备；只能说容量下界可证明的一类不可行。
