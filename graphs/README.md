# Graphs

[通用目标 Graph 小步计划](../docs/graph-delivery-plan.md)按声明、调度、证据门禁及 Loop 接线逐项验证交付；未实现项不据本计划宣称可运行。[Loop 状态](../docs/loop-status.md)保留相关未迁/未验事项。

- [通用目标图声明合同](goal-graph.md)：完整目标、依赖/写集及显式 closure 的准入；实际运行能力按当前交付阶段核验。

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
