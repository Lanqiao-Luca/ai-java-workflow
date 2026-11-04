**目的**：按任务导航入口协调与阶段结果责任，保留正式入口与能力边界。

**适用于**：采用本仓库入口协调与阶段结果责任的助手与维护者；实际调用须经责任 Agent 并核具体前提。

# Agents

角色定义结果责任，经 Skill 组合平级的 Standards 与 Tools。Brain 可直接选择 Agent 或其上的 Workflow、Loop、Graph；组织层分配阶段职责，Agent 经 Skill 使用底层规则与工具。

[证据采集者](evidence-collector.md)经证据采集 Skill 与 EC01–EC04 原子核来源、事实和覆盖，再交诊断者解释；[虚构案例](../workflows/examples/evidence-coverage/README.md)仅执行显式页观察判定。

新增技术设计到实施准备能力线：

- [方案作者](design-author.md) → 技术设计 Skill → 输入与方案原子。
- [设计复核者](design-reviewer.md) → 专业复核 Skill → 冻结审验与反例方法。
- [模块规划者](module-planner.md) → 模块规划 Skill → 归属/写集/依赖原子与结构工具。

对应 [Workflow](../workflows/technical-design.md)和[完整虚构案例](../workflows/examples/design-to-modules/README.md)说明真实验证范围。

[文档维护者](document-maintainer.md)负责本地文档创建、更新与原件保全，经文档维护 Skill 消费目的原子，再交文档审查者核内容。

[任务协调者](task-coordinator.md)协助 Brain 已选组织入口的运行，保存实例、组织阶段职责并交回总体状态；下表角色负责具体阶段。下面是角色与案例的导航，不代表平台安装或自动调度；十条案例均独立虚构。

| 角色 | 完整案例 |
| --- | --- |
| [实现者](implementer.md) | [书签标题规范化](../skills/code-implementation/example.md) |
| [需求负责人](requirement-analyst.md) | [标签需求：已决/未决、验收与可实施范围](../examples/clarify-bookmark-tags/README.md) |
| [验证者](verifier.md) | [标题验证：覆盖矩阵、失败复现与未运行状态](../examples/verify-bookmark-title/README.md) |
| [代码审查者](code-reviewer.md) | [改名审查：可复核发现与作者交接](../examples/review-bookmark-rename/README.md) |
| [语义审查者](semantic-reviewer.md) | [标题语义：需求映射与具体反例](../examples/compare-title-semantics/README.md) |
| [原则审查者](principle-reviewer.md) | [范围与证据：四态判断和整改条件](../examples/review-scope-and-evidence/README.md) |
| [诊断者](diagnostician.md) | [版本冲突：竞争解释与证据排除](../examples/diagnose-version-conflict/README.md) |
| [查询审查者](query-reviewer.md) | [游标分页：稳定排序与SQLite局部语义回放](../examples/review-cursor-pagination/README.md) |
| [交付规划者](delivery-planner.md) | [证据门禁：依赖、未决和恢复计划](../examples/plan-evidence-gated-delivery/README.md) |
| [文档审查者](document-reviewer.md) | [运行手册：逐要求审验与修订复核](../examples/review-draft-runbook/README.md) |

Java用例未实跑；查询案例仅有进程内SQLite语义回放，其他案例为文档/静态分析。作者自查、独立文档复核和业务验收分别说明。

[全部案例](../examples/README.md) · [执行文档](../docs/agent-publication-plan.md) · [发布结果](../docs/agent-publication-results.md)

[Java构建执行者](java-build-executor.md)为新增第11项职责，服务于[Spring构建Graph](../examples/spring-build-graph/README.md)。旧十个角色教材运行状态保持；新案例运行确定性夹具，不声称原生AI自动编码。

[容器构建执行者](container-build-executor.md)为第12项职责，通过Skill核显式本地Docker/镜像、容器限制和真实验收；[完整案例](../examples/docker-spring-graph/README.md)使用确定性命令，非平台注册或LLM派工。
