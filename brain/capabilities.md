**目的**：提供从任务能力到责任 Agent 的导航，避免 Brain 越过责任人调用下层。

**适用于**：需要选择任务协调或专项责任的助手；能力存在、可用和获权分别核对。

# 能力地图：经 Agent 进入

Brain 按[职责路由](routing.md)只选择责任 Agent。以下是责任入口，不是 Brain 的工具调用清单；Workflow、Loop、Graph 的模板与执行入口由接受任务的 Agent 定位和采用。

| 任务能力 | Agent 入口 | 接受后的选择与边界 |
| --- | --- | --- |
| 单轮阶段协作、同目标多轮执行、多目标依赖并发 | [任务协调者](../agents/task-coordinator.md) | 分别选 Workflow、Loop、Graph；每层均有 templates 与 examples，不要求全部启用 |
| 需求、实现、诊断或专项审查 | [Agent 目录](../agents/README.md) | 采用对应职责，经 Skill 组合 Standards 与 Tools |
| 技术方案、专业复核与模块准备 | [方案作者](../agents/design-author.md)、[设计复核者](../agents/design-reviewer.md)、[模块规划者](../agents/module-planner.md) | 按阶段进入对应 Agent，再由其 Skill 调取原子和工具，Brain 不直接选模板或执行检查 |
| 文档创建、更新与原件保全 | [文档维护者](../agents/document-maintainer.md) | 经文档维护 Skill 采用目的、属性与保留原子，交当前候选与语义依据 |
| 当前状态、交付依赖和恢复条件 | [交付规划者](../agents/delivery-planner.md) | 只规划时不执行发布；组织执行交任务协调者 |
| 构建与隔离 | [Java 构建执行者](../agents/java-build-executor.md)、[容器构建执行者](../agents/container-build-executor.md) | 沿各自 Skill 选择工具和隔离后端，核实际平台及权限 |

Standards 与 Tools 是平级基础资源：规则和验收方法不提供执行器，工具代码不授予操作许可。Skill 适配两者，Agent 对实际选择与结果负责。

定义适用、当前环境可调用、当前授权覆盖与同候选证据分别核对。入口缺失、未安装、调用失败和缺许可分别报告。原任务复用已读且未变的来源，只在变化或缺失时定向刷新。

返回：[Brain 入口](README.md)。
