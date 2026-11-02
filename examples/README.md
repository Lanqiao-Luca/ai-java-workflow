# 案例目录

## 原生Agent完整研发链

[原生Spring标签案例](native-spring-workflow/README.md)：真实原生上下文完成需求、生成Java及作者测试、独立验证、双审查和交付。13项固定验收、7项作者测试、5项独立验证共25项真实离线Spring/MockMvc测试通过；两审查Workflow调用区间重叠。运行时Agent/Skill注册仅在新实例，不改全局Agent/Skill；宿主项目信任登记须另获明确许可，要求全局配置零写入的任务不能运行当前后端。原生原件与公开摘要来源分别声明。仅macOS/Maven参考链，未部署，不将下方命令型Graph或旧角色教材改称原生模型执行。

[先行计划](../docs/native-agent-workflow-plan.md) · [真实交付结果](../docs/native-agent-workflow-results.md)

## Graph并发调度多个Workflow

[并发Java Graph](concurrent-java-graph/README.md)：4实例独立worktree/分支与macOS实验前台sandbox，2功能实际重叠、依赖汇合后8项Java断言，每实例10项探测及26项回归通过。新机制只支持无fork前台命令，非原生LLM调度，不扩写旧Spring/角色教材的历史运行结论。

## 一条完整研发Workflow案例

[书签标签替换](workflow-bookmark-tags/README.md)：同一需求、设计、候选、真实Spring装配和MockMvc红绿13测试、诊断修复、冻结审查及交付。[Workflow合同](../workflows/java-spring-development.md)组织现有角色；本例没有原生Agent自动调度、外部数据库或部署。

## 十条角色案例

十个角色各有一条独立虚构案例；分析产物、代码、语义回放和真实运行分别标识。下表是原有角色教材，历史NOT_RUN不因新增Workflow实跑改写。导航不代表已启动独立Agent。

| 角色 | 案例与实际产物 | 真实运行边界 |
| --- | --- | --- |
| [实现者](../agents/implementer.md) | [书签标题规范化](bookmark-title/README.md)：前后Java、diff、12项契约用例 | Java尚未编译运行 |
| [需求负责人](../agents/requirement-analyst.md) | [标签需求：已决/未决、验收与可实施范围](clarify-bookmark-tags/README.md) | 文档/静态材料分析；不代真实业务或原生Agent运行 |
| [验证者](../agents/verifier.md) | [标题验证：覆盖矩阵、失败复现与未运行状态](verify-bookmark-title/README.md) | 文档/静态材料分析；不代真实业务或原生Agent运行 |
| [代码审查者](../agents/code-reviewer.md) | [改名审查：可复核发现与作者交接](review-bookmark-rename/README.md) | 文档/静态材料分析；不代真实业务或原生Agent运行 |
| [语义审查者](../agents/semantic-reviewer.md) | [标题语义：需求映射与具体反例](compare-title-semantics/README.md) | 文档/静态材料分析；不代真实业务或原生Agent运行 |
| [原则审查者](../agents/principle-reviewer.md) | [范围与证据：四态判断和整改条件](review-scope-and-evidence/README.md) | 文档/静态材料分析；不代真实业务或原生Agent运行 |
| [诊断者](../agents/diagnostician.md) | [版本冲突：竞争解释与证据排除](diagnose-version-conflict/README.md) | 文档/静态材料分析；不代真实业务或原生Agent运行 |
| [查询审查者](../agents/query-reviewer.md) | [游标分页：稳定排序与SQLite局部语义回放](review-cursor-pagination/README.md) | 本地虚构SQLite语义实际回放，不连接外部DB/不证明MySQL性能 |
| [交付规划者](../agents/delivery-planner.md) | [证据门禁：依赖、未决和恢复计划](plan-evidence-gated-delivery/README.md) | 文档/静态材料分析；不代真实业务或原生Agent运行 |
| [文档审查者](../agents/document-reviewer.md) | [运行手册：逐要求审验与修订复核](review-draft-runbook/README.md) | 文档/静态材料分析；不代真实业务或原生Agent运行 |

运行结构与身份检查：`python3 scripts/check_agent_cases.py`（从项目根）。它不理解业务语义，不执行Java、SQL或Agent。SQL局部回放另运行`python3 examples/review-cursor-pagination/replay.py`。

[执行文档](../docs/agent-publication-plan.md) · [逐项发布结果](../docs/agent-publication-results.md) · [项目入口](../README.md)

## 真实Maven/Gradle构建Graph

[Spring Boot并发构建](spring-build-graph/README.md)：Maven3项与Gradle3项功能测试真实并发，合入后每工具8项；4次Boot JAR结构打包，未启动应用/部署。4实例各9探测、新18旧26回归通过，两真实失败阻断提升。可信模式允许fork/loopback，容量2是作业槽；非任意恶意后代容器。

## Docker双宿主Spring Graph

[Docker Spring Boot完整案例](docker-spring-graph/README.md)：同一公开seed与内容地址镜像，在macOS与同一Linux VM内控制器分别实跑；并发3+3→集成每工具8、Boot JAR、4实例各18探测及每宿主13 Engine+8 IO回归。Engine测试含2项明确host故障注入，IO不计内核实跑。未启动应用或部署，VM已停止，旧历史保持。
