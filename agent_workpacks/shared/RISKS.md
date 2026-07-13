# 风险表

| ID | 风险 | 严重性 | 负责人 | 缓解措施 | 状态 |
|---|---|---|---|---|---|
| R1 | 如果题目或正文仍暗示 LLM scheduler，审稿人会要求 LLM 主实验。 | high | project_manager_agent | 将主线改为 verifier-backed industrial heuristic scheduling engine；E5/E6/E7 暂停主线，只保留 appendix/motivation 候选。 | open |
| R2 | 论文 claim 可能过度声称最优性。 | high | qa_repro_agent | 只使用“verified feasible”和“capacity-lower-bound infeasible”；避免全局最优表述。 | open |
| R3 | baseline 可能混用旧结果目录，导致比较不一致。 | medium | experiment_manager_agent | 在同一 split、同一 verifier 下重跑关键 baseline。 | open |
| R4 | CP-SAT 子集可能超出时间预算。 | medium | dev_runner_agent | 限制为分层 50 单、120s/case；600s 只作为可选附录。 | open |
| R5 | 外部标准 benchmark 缺少库存、人员可用、设备副本和交期验收，强行适配会削弱业务语义。 | medium | experiment_manager_agent | JSPLib/FJSPLib/Taillard/DMU 只作相关工作或未来工作，除非能无损适配。 | open |
| R6 | 多 agent 可能覆盖或污染已有结果。 | high | project_manager_agent | 新文件/新目录优先；每个产物都登记到 `ARTIFACTS.md`。 | open |
| R7 | H5/H6 如果只做定性描述，论文证据链可能不够可审计。 | medium | qa_repro_agent | H5 必须产出机器可读 summary/metrics；H6 每个案例必须指向 solution/verify 或 infeasible artifact，并通过 QA gate。 | open |
