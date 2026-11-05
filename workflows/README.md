**目的**：按任务导航单轮阶段与角色交接，保留正式入口与能力边界。

**适用于**：采用本仓库单轮阶段与角色交接的助手与维护者；实际调用须经责任 Agent 并核具体前提。

# Workflows

[重要结论反证](conclusion-challenge.md)组织候选、取证、矩阵和限定交接；[实际离线反例](examples/conclusion-challenge/README.md)区分初始判断与直接观察。

[证据采集](evidence-collection.md)组织命题定界、事实取得、覆盖核查和解释交接；[离线八场景](examples/evidence-coverage/README.md)不连接实际来源。

[技术方案编制与专业复核](technical-design.md) → [设计到模块](design-to-modules.md)，提供从输入到准备包的完整责任链；[贯通案例](examples/design-to-modules/README.md)含实际离线结构控制，未运行工程实现。

[文档维护与审验](document-maintenance.md)组织文档定界、维护、检查与同候选审验。

## 模板与执行文件

- [templates：复用模板](templates/README.md)，由责任 Agent 填写为本次计划，不保存真实进度。
- [examples：执行文件与案例](examples/README.md)，包含已填计划及其实际运行或 NOT_RUN 状态。

Brain 可以直接选择并调取 Workflow 作为任务入口，由本层合同组织下层职责，实际协调者、宿主和阶段 Agent 按真实执行方式承接。每层都可单独采用，无需强制启用更高层。方法合同由 Agent 手动组织，已有程序仅执行其支持的定义格式；填好 Markdown 模板不等于自动运行。

真实工程计划与进度存放于使用者授权的位置；examples 只放适合公开的执行文件和独立虚构案例。沿当前实例接续，不复制既有证据或用空目录冒充完成。具体合同见 [Workflow 合同](java-spring-development.md)。

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

## 只读观察

[来源观察 Workflow](service-inspection.md)按已准入来源取得候选绑定证据，由巡检 Loop 控制补证和 PARTIAL 退出；不自动部署、轮询或连接真实服务。

## 整体缺陷目标

[缺陷整体验收 Workflow](defect-completion.md)把代码准入、业务行为、必要制品/操作结果和交接证据交回原目标；单项测试通过不代替完整任务验收。
