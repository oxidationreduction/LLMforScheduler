# project_manager_agent Handoff

## 当前状态

工作包已初始化。尚未启动任何实验。

## 下一步

1. 让 `experiment_manager_agent` 先冻结 split、metrics 和实验登记细节。
2. 让 `dev_framework_agent` 在 `experiments/aaai2026/` 下规划新增代码。
3. 让 `dev_runner_agent` 在任何长任务前先确定 tmux 安全运行约定。
4. 让 `paper_writer_agent` 在实验管理 agent 提供表格框架后再写结果段落。
5. 让 `qa_repro_agent` 在每批结果和每版论文 claim 进入正文前审计。

## 未决问题

- 本地 LLM 推理/SFT 具体使用哪个模型族。
- 14 天内 baseline 是跑 full 670 还是优先 test-only。
