# llm_scheduler

`llm_scheduler` 是仅供 Python 调用的分钟级生产排程包。公共接口使用固定的 timed portfolio；调用方不能选择求解策略、注入固定任务或调用命令行服务。

## 交接要点

- 可行结果在返回前必须通过内置 verifier；只有 `schedule_accepted == true` 的非空 `plan` 可作为可执行排程使用。
- 不支持 `fixed_tasks`，也不接受预先锁定的工序、人员、设备或时间段。请提交完整的订单、工艺、库存、设备和人员可用日。
- `inventory` 会先抵扣需求；净需求为零时返回 `status == "optimal"` 和空 `plan`。
- 返回值是 JSON 可序列化字典，不含本地文件路径。非可行状态请读取 `errors`，不要使用 `plan`。

## Python 接口

```python
import json
from llm_scheduler import solve, solve_json, solve_legacy

with open("examples/request_en.json", encoding="utf-8") as f:
    result = solve(json.load(f))

response_json = solve_json(json.dumps(json.load(open("examples/request_en.json", encoding="utf-8"))))

with open("examples/request_zh.json", encoding="utf-8") as f:
    chinese_request = json.load(f)
legacy_result = solve_legacy(chinese_request["problem"], case_id=chinese_request["case_id"])
```

| 接口 | 请求 | 返回 |
| --- | --- | --- |
| `solve(request)` | 英文主请求或 `problem` 内含中文字段的封装请求 | 结果字典 |
| `solve_json(request_json)` | 上述封装请求的 JSON 字符串 | 结果 JSON 字符串 |
| `solve_legacy(order_payload, case_id=...)` | 原始中文订单对象与案例标识 | 结果字典 |

`solve_json` 对格式错误 JSON 或非有限数值返回 `status: "invalid_input"` 的 JSON 响应。常见状态还包括 `feasible`、`optimal`、`infeasible_proven`、`time_limit` 和 `no_solution_found`。

## 请求格式

英文主请求见 [examples/request_en.json](examples/request_en.json)：

- 顶层固定为 `schema_version: "1.0"`、`case_id`、`problem` 和可选 `options.time_limit_seconds`；默认时限为 120 秒。
- `problem.orders`：`product_id`、非负整数 `quantity`、正整数 `due_day`。
- `problem.processes`：按产品 ID 分组的工序；每道工序包含 `step_index`、`name`、`equipment`、`duration_minutes` 和 `eligible_workers`。
- `problem.inventory`：产品库存；`problem.machines` 为 `{name, count}` 列表；`problem.worker_availability` 为人员到可用日列表。
- `equipment: []` 表示不占设备；多台设备表示必须同时占用。工人单日上限固定为 480 分钟。

中文兼容请求见 [examples/request_zh.json](examples/request_zh.json)。其 `problem` 使用：`当前订单信息`、`产品工序`、`相关产品库存`、`可使用设备信息`、`每日可使用人员列表`。中文工艺键可使用 `<产品名>工艺信息`。

响应固定包含 `solution`、`verification` 与 `schedule_accepted`。`solution.status` 为 `feasible` 或 `optimal` 时才有可验证的排程；`infeasible_proven`、`time_limit`、`no_solution_found` 和 `invalid_input` 的 `verification.status` 为 `not_applicable`。成功响应的 `plan` 是按天组织的列表：每个元素为 `{ "day": ..., "tasks": [...] }`。任务包含物料、工序、数量、人员、设备和分钟级起止时间；任务间的人员、设备、工序先后、库存和期限约束已由 verifier 检查。
