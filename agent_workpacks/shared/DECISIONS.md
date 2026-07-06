# 决策记录

## D1. 论文定位

论文定位为“带独立 verifier 的工具增强工厂订单排产 Agent”，而不是“LLM 直接生成排班”。

原因：仓库已经有较强的 solver/verifier 证据，但还没有提交的 LLM 训练/推理框架证据。

## D2. LLM 的职责

LLM 层负责订单摘要、工具选择、策略选择、verifier 反馈处理、解释和交互。

主方法中，LLM 不直接负责生成完整分钟级排班。

## D3. Verifier 是验收边界

任何生成的排班只有通过现有 verifier，并且使用相同业务语义，才算有效。

不得为了提升结果弱化 verifier 检查。

## D4. 实验范围

14 天内优先完成：

- 复现现有 670 单全量结果；
- 固定 dispatching baseline；
- chunked wavefront 消融；
- CP-SAT 子集 baseline；
- LLM tool-agent 推理；
- LLM 策略选择 SFT；
- direct LLM schedule generation 小规模失败模式 baseline。

不做 RL、GNN、670 单全量 exact CP-SAT、大规模合成数据扩展。

## D5. 结果 claim 边界

可以写：

- verifier 通过的可行排班；
- 容量下界证明的不可行；
- 运行时间和任务规模；
- LLM tool-agent 的解析率、策略选择、最终 verifier 结果。

没有新增证据时不能写：

- 全局最优；
- 完备不可行证明；
- 工业 KPI 提升；
- LLM 全面优于所有排产方法。

## D6. Split 和实验范围冻结

主 split 固定为：

- Train：2020-2023；
- Dev/validation：2024H1；
- Test：2024H2-2025；
- OOD/recent：2025-only，作为 test 内的额外评估标签。

CPU solver、dispatching baseline 和 chunked wavefront 消融优先跑 full 670。CP-SAT 主表只跑分层 50，120s/case；600s/case 只作为可选附录。LLM tool-agent 跑 test 133。Direct LLM schedule generation 跑分层 30，只作为失败模式和动机实验。

## D7. 本地模型和 GPU 使用

默认使用本机 Qwen 系列模型作为 LLM 证据来源。LoRA/SFT 使用 4 张 RTXPRO6000；推理可使用 8 卡，但 A6000 每卡分配任务数按 RTXPRO6000 的一半配置。

GPU 只用于 LLM 推理或 LoRA/SFT；solver、verifier、OR-Tools 主线主要使用 CPU。

## D8. 论文证据准入

论文主表只接收已登记 artifact 且通过 QA gate 的结果。旧结果目录可作为背景说明；若要进入主比较，必须在同一 split、同一 verifier、同一 metrics schema 下重新汇总或复现。
