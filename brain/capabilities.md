**目的**：将完整能力架构与当前组织、专项入口连接，帮助选择可用的最小承载层。

**适用于**：需要按目标选择 Graph、Loop、Workflow 或 Agent 的助手；能力定义、调用前提、授权与验证分别核对。

# 能力地图：组织层与专项职责

**Standards / Tools → Skill → Agent → Workflow → Loop → Graph** 是自底向上的组装关系，Standards 与 Tools 平级；Brain 可选择 Agent 及其上层，执行向下组织至 Agent，再经 Skill 使用底层能力。

| 任务目标 | Brain 的入口候选 | 运行与验证范围 |
| --- | --- | --- |
| 多目标依赖、证据门禁与收口 | [目标 Graph](../graphs/goal-graph.md)、[Graph 目录](../graphs/README.md) | 对应图定义、适配器和实际后端决定能否执行，不能外推任意图 |
| 同目标有限重复与停止 | [Loop 目录](../loops/README.md) | 按具体失败/补证/整改合同与累计预算组织 Workflow |
| 一轮研发、设计或文档阶段交接 | [研发 Workflow](../workflows/java-spring-development.md)、[设计 Workflow](../workflows/technical-design.md)、[文档 Workflow](../workflows/document-maintenance.md) | 由选中流程分配阶段 Agent，专业/文档/业务验收各保边界 |
| 固定任务下能力评估 | [能力评估者](../agents/capability-evaluator.md) | 原始结果、缺陷漏检/误报、脚本还原和耗时；人工/模型/业务效益未测 |
| 重要技术结论反证 | [反证 Workflow](../workflows/conclusion-challenge.md)、[结论复核者](../agents/conclusion-reviewer.md) | 矩阵/主动反证/敏感性；真实取证须绑定来源，结构通过不等于根因确认 |
| 命题取证、采样与完整覆盖 | [取证 Workflow](../workflows/evidence-collection.md)、[证据采集者](../agents/evidence-collector.md) | 组织层或专项均可选，真实来源另需合法适配；给定页观察判定不等于执行查询 |
| 单项需求、实现、诊断或审查 | [Agent 目录](../agents/README.md) | 对应职责经 Skill 组合规则与工具 |
| 设计、专业复核或模块准备的专项阶段 | [方案作者](../agents/design-author.md)、[设计复核者](../agents/design-reviewer.md)、[模块规划者](../agents/module-planner.md) | 专项可选 Agent，多阶段可先选 Workflow；不凭结构有效宣称实施获权 |
| 组织实例的运行协调和接续 | [任务协调者](../agents/task-coordinator.md) | 按已选组织入口维护实例与交接，不强制作为其他组织层的前置 |

具体模板和执行文件从各组织目录进入。Brain 不直接使用 Skill、Standards 或 Tools；来源可读、宿主可调用、当前获权和实际运行不是同一状态。

收到来源变化或恢复时确缺上下文，才定向刷新相交定义，复用原实例、完成前缀和累计预算；不因目录存在声称已经自动调度。

返回：[Brain 入口](README.md)。
