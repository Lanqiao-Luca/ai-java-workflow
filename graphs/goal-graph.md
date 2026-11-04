# 通用目标 Graph 合同

目的：组织多个原目标及其 Loop、证据门禁和显式收口，保留各目标的必需范围，不用某条支路成功代替整体完成。

## 声明与准入

[定义校验器](../tools/goal_graph.py)接收版本 1 的 graph_id、goals、max_parallel、nodes。goals 每项有唯一 id 和完整 required 验收键；每个原目标由一个必需 Loop 节点承担。节点包含 id、kind、depends_on、handler、contract、writes、goal_id、required。handler 仅为受信任宿主注册名，不接受 shell/代码或在定义中存本次运行身份。

kind 分 loop、gate、closure。Loop 声明 task、inspection 或 defect 返回合同及产物；Gate 只读已声明 Loop 的产品；唯一 closure 是终端节点，必须覆盖全部必需分支。所有依赖均为必需依赖，不能用跳过或某个成功输入代替。图中循环拒绝，有限重复交 Loop 承担。

独立分支按并发上限执行，但声明写集不能相交，父/子路径亦冲突；有依赖顺序的节点可沿合同复用逻辑输出。写集准入不等于系统沙箱或对恶意回调的访问隔离。

## 分层与当前交付

Graph 选择[巡检 Loop](../loops/inspection-convergence.md)及[缺陷 Loop](../loops/defect-convergence.md)，具体取证与阶段职责继续由[来源观察 Workflow](../workflows/service-inspection.md)、[整体验收 Workflow](../workflows/defect-completion.md)承载，不把 Loop 的不同终态不经核对统一洗成成功。

[前台执行器](../tools/goal_graph_run.py)现支持声明依赖的有限并发、明确失败的后代阻断、独立分支继续、私有检查点和安全前缀接续。基础 closure 节点核所有必需节点的执行返回及实际产品身份。候选绑定的语义 Gate 与具体 Loop 接线仍按[小步计划](../docs/graph-delivery-plan.md)后续步骤验收；当前基础回执不能替代业务验收。旧 Java/构建/原生 Graph 各自保持原运行边界。

## 运行身份与恢复

`GoalGraphRun(definition, handlers, context, run_root, budget_seconds=..., ...)` 使用仓库外全新私有根。每个 handler 由 `Handler(callable, identity)` 显式登记，identity 为调用者绑定的适配器源码/配置 SHA256。运行 context 固定当前候选、需求、规则 SHA；它是本次输入身份，不嵌入可复用图定义。

派工前先保存 RUNNING、尝试编号和事件，原子替换状态并 fsync；然后才创建节点产物区及调用回调。回调接收自身写集、只读依赖产品、剩余时间和绝对截止。Loop 回执必须有实际声明的 JSON 文件，字节解码与返回 result 一致；产品拒绝越界路径、隐藏/链接/特殊文件、额外输出及总量超过 8MiB。JSON 回执最大 128KiB。

`pause_after` 在本批回调全部返回后暂停。用同定义、context、handler 身份、执行器代码与预算、同私有根及 `resume=True` 接续 READY/PAUSED，逐个重核已成功产品，跳过有效前缀。暂停时间不顺延截止；RUNNING/UNKNOWN、失败终态或产物变化均不重放。已完成检查点可读回，不能借它重跑业务。

每个运行持有单写者锁，状态保留完整原目标和逐节点结果。UNKNOWN 不判停止成功，不复用原运行根；未知回调可能仍在执行。Python 回调不是可强杀进程，必须自行落实传入的内层超时与执行隔离；图不会因等待超时声称底层进程已终止。此执行器不提供系统沙箱或后台调度，跨运行的业务写权与资源分配仍归实际宿主。

已明确失败或 PARTIAL 的节点只阻断后代；无关合法分支继续。必需依赖不能以 SKIPPED 代替；closure 晚于截止的结果保留但不作为成功。回调异常或等待超时保 UNKNOWN，停止后续派工并保存原尝试及恢复条件。

[Graphs](README.md) · [准入回归](../tests/test_goal_graph_definition.py)
