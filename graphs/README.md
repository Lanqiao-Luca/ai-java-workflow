**目的**：按任务导航多目标依赖、并发与整体收口，保留正式入口与能力边界。

**适用于**：采用本仓库多目标依赖、并发与整体收口的助手与维护者；实际调用须经责任 Agent 并核具体前提。

# Graphs

## 模板与执行文件

- [templates：复用模板](templates/README.md)，由责任 Agent 填写为本次计划，不保存真实进度。
- [examples：执行文件与案例](examples/README.md)，包含已填计划及其实际运行或 NOT_RUN 状态。

Graph 可以由[任务协调者 Agent](../agents/task-coordinator.md)选用并执行，Brain 只向 Agent 交任务，不直接调用本层。每层都可单独采用，无需强制启用更高层。方法合同由 Agent 手动组织，已有程序仅执行其支持的定义格式；填好 Markdown 模板不等于自动运行。

真实工程计划与进度存放于使用者授权的位置；examples 只放适合公开的执行文件和独立虚构案例。沿当前实例接续，不复制既有证据或用空目录冒充完成。具体合同见 [Graph 合同](goal-graph.md)。

[通用目标 Graph 小步计划](../docs/graph-delivery-plan.md)按声明、调度、证据门禁及 Loop 接线逐项验证交付；未实现项不据本计划宣称可运行。[Loop 状态](../docs/loop-status.md)保留相关未迁/未验事项。

- [通用目标图声明合同](goal-graph.md)：完整目标、依赖/写集及显式 closure 的准入；实际运行能力按当前交付阶段核验。

- [巡检/缺陷双目标 Graph](examples/goal-loops/README.md)与[JSON定义](evidence-goals.json)：实际 Graph→Loop、确定性 Gate 与收口，含完整成功、局部 PARTIAL 和未知副作用三个虚构案例；[当前完成范围/待办](../docs/graph-status.md)保留生产与其他图未验项。

- [原生Java/Spring Graph](native-java-spring.md)：六阶段原生上下文、依赖门禁和双审查并发；[完整Spring案例](../examples/native-spring-workflow/README.md)与[结果](../docs/native-agent-workflow-results.md)另列真实调用和测试。

Graph组织多个已声明Workflow实例的依赖、并发额度和汇合。下方三条命令型Graph执行已声明argv；只有上方显式原生支路调用模型角色，不能从目录或JSON存在推定其他定义也支持原生调度。

- [并发Java Graph合同](concurrent-java.md)
- [可执行Graph定义](concurrent-java.json)
- [真实完整案例](../examples/concurrent-java-graph/README.md)

[执行文档](../docs/concurrent-execution-plan.md) · [交付结果](../docs/concurrent-execution-results.md)

返回：[项目入口](../README.md)。

- [Spring Boot可信构建Graph](spring-build.md)与[JSON定义](spring-build.json)：Maven/Gradle功能并发，合入后每工具8测试及Boot JAR。
- [完整构建案例](../examples/spring-build-graph/README.md)：仅macOS实验可信模式，允许fork/loopback，非旧严格前台模式。

- [Docker Spring Graph](docker-spring.md)与[JSON](docker-spring.json)：Linux/macOS显式本地Engine，双宿主真实Spring并发与容器探测；[完整案例](../examples/docker-spring-graph/README.md)。
