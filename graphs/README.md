# Graphs

- [原生Java/Spring Graph](native-java-spring.md)：六阶段原生上下文，依赖门禁和双审查并发；与下方固定命令型Graph分开。

Graph组织多个已声明Workflow实例的依赖、并发额度和汇合；不代表平台原生LLM Agent自动调度。

- [并发Java Graph合同](concurrent-java.md)
- [可执行Graph定义](concurrent-java.json)
- [真实完整案例](../examples/concurrent-java-graph/README.md)

[执行文档](../docs/concurrent-execution-plan.md) · [交付结果](../docs/concurrent-execution-results.md)

返回：[项目入口](../README.md)。

- [Spring Boot可信构建Graph](spring-build.md)与[JSON定义](spring-build.json)：Maven/Gradle功能并发，合入后每工具8测试及Boot JAR。
- [完整构建案例](../examples/spring-build-graph/README.md)：仅macOS实验可信模式，允许fork/loopback，非旧严格前台模式。

- [Docker Spring Graph](docker-spring.md)与[JSON](docker-spring.json)：Linux/macOS显式本地Engine，双宿主真实Spring并发与容器探测；[完整案例](../examples/docker-spring-graph/README.md)。
