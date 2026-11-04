# 通用目标 Graph 合同

目的：组织多个原目标及其 Loop、证据门禁和显式收口，保留各目标的必需范围，不用某条支路成功代替整体完成。

## 声明与准入

[定义校验器](../tools/goal_graph.py)接收版本 1 的 graph_id、goals、max_parallel、nodes。goals 每项有唯一 id 和完整 required 验收键；每个原目标由一个必需 Loop 节点承担。节点包含 id、kind、depends_on、handler、contract、writes、goal_id、required。handler 仅为受信任宿主注册名，不接受 shell/代码或在定义中存本次运行身份。

kind 分 loop、gate、closure。Loop 声明 task、inspection 或 defect 返回合同及产物；Gate 只读已声明 Loop 的产品；唯一 closure 是终端节点，必须覆盖全部必需分支。所有依赖均为必需依赖，不能用跳过或某个成功输入代替。图中循环拒绝，有限重复交 Loop 承担。

独立分支按并发上限执行，但声明写集不能相交，父/子路径亦冲突；有依赖顺序的节点可沿合同复用逻辑输出。写集准入不等于系统沙箱或对恶意回调的访问隔离。

## 分层与当前交付

Graph 选择[巡检 Loop](../loops/inspection-convergence.md)及[缺陷 Loop](../loops/defect-convergence.md)，具体取证与阶段职责继续由[来源观察 Workflow](../workflows/service-inspection.md)、[整体验收 Workflow](../workflows/defect-completion.md)承载，不把 Loop 的不同终态不经核对统一洗成成功。

本步仅交付定义准入与反例测试，尚未交付新目标图的调度、持久化、Gate 证据裁决或实际 Loop 接线。后续按[小步计划](../docs/graph-delivery-plan.md)分别验证；现有 Java/构建/原生 Graph 各自保持原运行边界。

[Graphs](README.md) · [准入回归](../tests/test_goal_graph_definition.py)
