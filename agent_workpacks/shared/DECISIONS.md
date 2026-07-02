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
