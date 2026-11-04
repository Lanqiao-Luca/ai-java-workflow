**目的**：按任务结果选择入口 Agent，并规定继续、变化、未知与停止的交接。

**适用于**：当前助手选择责任入口；流程和工具选择由接受任务的 Agent 承担。

# 职责路由：先交 Agent

Brain 只恢复目标、项目、授权和本轮变化，再将任务交给责任 Agent；不直接选择、实例化或启动 Workflow、Loop、Graph，也不直接调用 Skill、Standards 或 Tools。

## 选择入口责任

| 当前任务 | 交给谁 | 接收后的职责 |
| --- | --- | --- |
| 多阶段任务、多目标依赖、有限重复或已有组织实例的续作 | [任务协调者](../agents/task-coordinator.md) | 由它按需选择 Workflow、Loop、Graph，读取模板、保存执行文件并组织阶段 Agent |
| 澄清目标、保持项与验收 | [需求负责人](../agents/requirement-analyst.md) | 确认契约和关键未知；不将建议当用户决定 |
| 已有流程分配的实现任务，或范围明确的单项改动 | [实现者](../agents/implementer.md) | 接受候选与写集，经 Skill 取得规则和工具 |
| 未知失败原因 | [诊断者](../agents/diagnostician.md) | 核合法证据与反证，缺事实不补猜测 |
| 行为验证、代码、语义或查询风险审查 | [验证者](../agents/verifier.md)、[代码审查者](../agents/code-reviewer.md)、[语义审查者](../agents/semantic-reviewer.md)、[查询审查者](../agents/query-reviewer.md) | 按问题选择专项责任，给定 SQL 审查不等于执行 SQL 或 DDL 获权 |
| 范围、目的、保留和完成声明 | [原则审查者](../agents/principle-reviewer.md) | 核同候选证据，不替代功能或业务验收 |
| 编制或修订技术方案 | [方案作者](../agents/design-author.md) | 经设计 Skill 核输入、当前能力、保持项与实质方案；需要多阶段组织时沿协调者进入 Workflow |
| 对冻结设计作专业复核 | [设计复核者](../agents/design-reviewer.md) | 经复核 Skill 核覆盖、反例与真实上下文，返回候选绑定发现 |
| 从当前设计形成模块包 | [模块规划者](../agents/module-planner.md) | 经规划 Skill 分配需求/写者与依赖，工具只核结构，实施准入另核 |
| 创建、更新本地文档或维护模板 | [文档维护者](../agents/document-maintainer.md) | 经文档维护 Skill 核目的、适用、原件和实际写入；多阶段任务沿原协调者组织 |
| 说明与实际能力一致 | [文档审查者](../agents/document-reviewer.md) | 核使用说明、来源和真实状态 |
| 只需交付顺序、残余与恢复计划 | [交付规划者](../agents/delivery-planner.md) | 规划，不代发布或部署；需要实际组织执行则交任务协调者 |

Brain 可以判断任务需要组织责任，但具体组织层和模板由接受任务的 Agent 决定。已有适用流程时沿当前协调者和阶段职责接续，不重复派一条链。

## 续作与变化

- 普通继续：交原责任 Agent，复用有效状态和证据，不重建实例或重置预算。
- 验收、候选、环境或授权变化：由责任 Agent 判断相交阶段和失效范围，保留无关结果。
- 已受理操作结果未知：由当前责任 Agent 查状态，不换运行身份重放。
- 停止：通知当前责任 Agent 停止相关新动作，返回在途未知、最后可信状态和恢复条件，不预约后台继续。

缺必要角色或能力时列出具体缺口，只停依赖动作，不由 Brain 绕过 Agent 自行调用下层。采用角色文档、原生安装和实际独立委派分别表述。

返回：[Brain 入口](README.md)。
