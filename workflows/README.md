# Workflows

- [原生Agent研发链](native-java-spring.md)：六阶段真实原生派工、独立worktree、冻结审查与失败阻断；[完整Spring案例](../examples/native-spring-workflow/README.md)及[实跑结果](../docs/native-agent-workflow-results.md)区分模型、构建和被动检查。

Workflow负责阶段顺序、输入输出交接和失败返回；各Agent自行选择Skill并消费Standards。方法合同可手动采用，命令型JSON由原执行器运行；`native-*.json`通过显式原生执行器在新实例注册并派工，不改全局Agent/Skill注册，也不把全部方法文档自动安装成平台能力；Codex宿主项目信任登记需另外获得平台写入许可。

- [Java/Spring研发全流程](java-spring-development.md)：同一需求与候选，从澄清到实现、验证、审查、整改及交付。
- [完整虚构案例](../examples/workflow-bookmark-tags/README.md)：书签标签替换，真实Spring装配/MockMvc红绿测试与阶段证据。

## 实例并发执行

- [执行实例合同](concurrent-execution.md)：资源、前台沙箱、写集、状态和失败返回。
- [标题Workflow定义](concurrent-java-title.json)与[标签Workflow定义](concurrent-java-tags.json)：独立功能工作区，宿主派发前台JVM。
- [集成Workflow定义](concurrent-java-integration.json)：等待依赖，合并后重编译并运行8项断言。
- [Graph完整案例](../examples/concurrent-java-graph/README.md)：仅已测macOS前台后端，无fork型Maven/Gradle支持或原生LLM执行。

[执行文档](../docs/java-spring-workflow-plan.md) · [发布与验证结果](../docs/java-spring-workflow-results.md)

返回：[项目入口](../README.md)。

## 可信Spring构建

[执行合同](spring-build.md)消费专门构建职责与隔离Skill；[Maven标题](spring-build-title.json)、[Gradle标签](spring-build-tags.json)并行，[集成](spring-build-integration.json)在依赖成功后用两种工具验证同一合并候选。[完整案例](../examples/spring-build-graph/README.md)明确一次性Daemon opt-in与进程树边界。

## Docker构建

[容器Workflow合同](docker-spring.md)消费专门容器执行者职责；[Maven标题](docker-spring-title.json)、[Gradle标签](docker-spring-tags.json)并发，[集成](docker-spring-integration.json)精确合并后每工具8测试。对应[Docker案例](../examples/docker-spring-graph/README.md)分别标明实际宿主与Engine范围。
