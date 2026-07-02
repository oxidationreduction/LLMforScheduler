# 风险表

| ID | 风险 | 严重性 | 负责人 | 缓解措施 | 状态 |
|---|---|---|---|---|---|
| R1 | 如果 LLM 层证据弱，审稿人可能认为论文只是非 LLM 排产器。 | high | project_manager_agent | 补最小 LLM tool-agent 推理、SFT 策略选择和 direct-generation baseline。 | open |
| R2 | 论文 claim 可能过度声称最优性。 | high | qa_repro_agent | 只使用“verified feasible”和“capacity-lower-bound infeasible”；避免全局最优表述。 | open |
| R3 | baseline 可能混用旧结果目录，导致比较不一致。 | medium | experiment_manager_agent | 在同一 split、同一 verifier 下重跑关键 baseline。 | open |
| R4 | CP-SAT 子集可能超出时间预算。 | medium | dev_runner_agent | 限制为分层 50 单、120s/case；600s 只作为可选附录。 | open |
| R5 | LLM 直接排班可能失败严重。 | low | paper_writer_agent | 将其作为 tool+verifier 路线的动机，不作为主方法。 | open |
| R6 | 多 agent 可能覆盖或污染已有结果。 | high | project_manager_agent | 新文件/新目录优先；每个产物都登记到 `ARTIFACTS.md`。 | open |
