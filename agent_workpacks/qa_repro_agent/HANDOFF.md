# qa_repro_agent Handoff

## 当前状态

已就绪。尚未执行审计。

## 初始 checklist

- 确认所有 JSON 文件可解析。
- 确认已有全量结果 summary 的关键数字。
- split manifest 出现后检查 split 泄漏。
- 确认每张论文表格都有来源 artifact。
- 确认所有 claim 都不超过证据边界。

## Claim 红线

- 不写全局最优 claim。
- 不写完备不可行证明 claim。
- LLM 实验完成前，不写 LLM 优越性 claim。
- 没有部署或用户研究证据时，不写工业 KPI claim。
