# dev_runner_agent Handoff

## 当前状态

已就绪。尚未启动任何进程。

## 运行规则

- 所有长任务都用 tmux。
- 使用唯一 session 名，例如 `llm_sched_e1_full670`。
- 日志和 summary 写入新结果目录。
- 长任务需要提供 watcher/status 文件。
- smoke 测试后删除临时文件，除非它们是必要 artifact。

## 等待事项

- 具体实验命令。
- split manifest。
- 输出目录命名约定。
