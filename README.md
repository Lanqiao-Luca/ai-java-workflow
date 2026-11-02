# ai-java-workflow

把一个 Java/Spring 需求交给 AI，按可复核的步骤形成代码候选与验证证据。

面向 Java/Spring 业务开发的 AI 研发工作流。按需要使用 **Graph → Workflow → Agent → Skill → Standards**：Graph控制依赖与实例并发，Workflow串阶段与交接，Agent对结果负责，Skill适配当前任务，Standards保存共用方法。简单任务不要求启用Graph或全部角色。提供可阅读的方法、空表和独立虚构代码案例，由使用者当前的 AI 助手与本地工具执行。

## 仓库里有什么

**2条并发Graph · 1条完整研发Workflow · 6份可执行Workflow定义 · 18份规范 · 13项技能 · 11项角色职责 · 10条角色案例 · 3条集成案例**。

| 你想做什么 | 从这里进入 | 能拿到什么 |
| --- | --- | --- |
| 并发构建Spring Boot | [可信构建Graph](graphs/spring-build.md)、[Maven/Gradle完整案例](examples/spring-build-graph/README.md) | 2作业实际并发、合并后每工具8项测试与Boot JAR；显式macOS可信模式 |
| 并发运行隔离的Workflow | [Graph合同](graphs/concurrent-java.md)、[完整Java并发案例](examples/concurrent-java-graph/README.md) | 每run_id独立worktree与已探测前台sandbox，2功能并发后串行集成/8断言；仅macOS实验后端 |
| 跑通一个完整研发案例 | [Java/Spring Workflow](workflows/java-spring-development.md)、[书签标签集成案例](examples/workflow-bookmark-tags/README.md) | 同一需求与候选、真实Spring/MockMvc红绿13测试、诊断修复及同候选审查 |
| 先看一个Agent怎样做事 | [实现者Agent](agents/implementer.md)、[完整案例](examples/bookmark-title/README.md) | 输入、决策、规范消费、Java前后差异、用例与交接 |
| 把需求交给AI开发 | [需求澄清](skills/requirement-clarification/SKILL.md)、[代码实现](skills/code-implementation/SKILL.md) | 可实施范围、保持项、最小改点和真实验证要求 |
| 审代码或排查失败 | [代码审查](skills/code-review/SKILL.md)、[证据诊断](skills/evidence-diagnosis/SKILL.md) | 可复核发现、反例、限定结论和恢复点 |
| 查方法与职责 | [规范目录](standards/README.md)、[技能目录](skills/README.md)、[角色目录](agents/README.md) | 当前问题需要的规范、输入输出和责任边界 |
| 直接记录本次任务 | [任务表](skills/resources/task.md)、[行为映射](skills/resources/behavior.md)、[验证与审查表](skills/resources/review.md) | 可复用的空表，不要求每次重建台账 |

仓库区分**方法文档、辅助脚本和代码示例**。Skill/Agent文档没有自动注册到平台，也不提供模型、数据库或外部服务客户端；不要求为简单任务启用所有角色。

## 按执行实例分配资源：Graph调度多个Workflow

[完整并发案例](examples/concurrent-java-graph/README.md)由真实[Graph JSON](graphs/concurrent-java.json)引用3份Workflow JSON，宿主读取合同、角色与Skill身份，再执行已声明的本地argv；不是把10个原生LLM Agent自动派工。共享[执行机制](tools/execution/README.md)是Python标准库实现，不是新的方法层或私有企业Tools。

Graph自身及title/tags/integration共4个实例，每个有独立branch/worktree、受限策略、HOME/TMP和证据。两个功能JVM实际重叠，峰值2；集成等待两项成功，在自己的worktree合入精确commit后重新编译并通过8项Java断言，源HEAD保持不变。每实例10项探测验证自身写、仓库外canary读写、Git管理canary读写、网络、硬链接创建、符号链接读、fork和脱离会话派生拒绝；另外26项真实回归通过、无跳过。

当前**仅macOS已弃用sandbox-exec的实验前台后端**，deny fork、默认拒网络，无裸subprocess回退。Java用JavaCompiler API在同JVM编译，不能宣传Maven/Gradle等fork型任务可在此后端运行。旧Spring案例的临时Maven配置隔离与这里的内核权限限制是不同范围，不用旧13测试冒充并发Spring验证。

```sh
python3 -B examples/concurrent-java-graph/run.py --java-home <JDK目录>
```

需要macOS、可用sandbox-exec、Python3.9+、Git、显式JDK17+；不安装工具或下载依赖，运行根是临时虚构仓库。源路径限ASCII且拒所有隐藏路径（含.gitignore/.github）、链接、子模块和属性过滤器；此seed定义不能直接套任意工程。详情见[限制与真实结果](examples/concurrent-java-graph/result.md)。

宿主单写状态与Git管理；共享同一runtime_root的Graph使用持久额度池。脏/UNKNOWN资源不force清理，被强杀宿主留下未知active租约时隔离池，不自动复用或向旧PID发信号。只提供审计恢复，不自动续跑。允许必要系统metadata/根目录枚举及明确工具根只读，没有总RAM/总磁盘、全机器外部进程配额或恶意多租户完全防护保证。

[先行执行文档](docs/concurrent-execution-plan.md) · [发布与验证结果](docs/concurrent-execution-results.md) · [隔离Skill](skills/workspace-isolation/SKILL.md) · [Graph目录](graphs/README.md)

## 可信构建模式：Maven与Gradle并发Spring Boot Graph

新增[完整Spring Boot构建案例](examples/spring-build-graph/README.md)使用独立虚构接口，显式选择[可信构建后端](tools/execution/build_runtime.py)。title用Maven运行3项测试，tags用Gradle运行3项测试，两个Workflow实际重叠；integration合入精确提交后，两种工具各通过同一套8项Spring/MockMvc测试并打包。4次Boot JAR结构、大小和SHA已核，二进制未上传，未启动应用或部署。

此模式允许fork与较宽loopback，外网在离线Graph阶段拒绝；loopback可以接触同机其他服务，不是自身IPC隔离。预热单独联网下载公开Central依赖，空HOME/显式配置及封存缓存不继承个人私服。旧严格前台模式继续deny fork，与新模式分别选择，历史源码与证据不改写。

每实例独立worktree、分支、HOME/TMP和可写缓存；Graph及3Workflow共4实例，每实例9项继承限制探测。容量2计Workflow作业，实测节点树峰5进程，不是JVM总数2。默认拒绝脱离会话；案例显式允许已观察、持续跟踪的一次性Gradle Daemon，客户端结束后最多3秒等待停止，残留不得提升。未知占用隔离池；轮询不能保证恶意快速doublefork约束，非容器级或多租户强沙箱。

新增18项回归、原严格26项真实通过且0跳过；错误基线与缺依赖两项实际失败均阻断后代及候选提升。仅macOS已弃用Seatbelt实验后端、可信源码/插件与受限ASCII非隐藏路径；没有跨平台回退或任意Spring工程一键兼容。

[先行执行计划](docs/spring-build-sandbox-plan.md) · [交付与验证结果](docs/spring-build-sandbox-results.md) · [Graph定义](graphs/spring-build.json) · [真实结果与重跑边界](examples/spring-build-graph/result.md)

Docker容器后端见[先行执行计划](docs/docker-sandbox-plan.md)：当前仅计划，Linux/macOS真实支持以后续验证回执为准；不会用旧macOS后端结果代替Docker实跑。

## 从需求到交付：一条完整Java/Spring研发Workflow

[Workflow合同](workflows/java-spring-development.md)组织现有Agent，贯通需求确认、设计实现、验证、冻结审查、整改复验和交付。诊断、SQL和文档审验按真实条件选择；方法仍由各Agent经Skill消费Standards，不把角色说明顺序排列当自动执行。

[书签标签替换集成案例](examples/workflow-bookmark-tags/README.md)是同一个独立虚构需求：v1刻意静默过滤无效标签，真实Spring装配与MockMvc测试暴露两项指定失败；仅修normalize后，v2同一13项测试全部通过。请求经过Controller和Service，断言实际状态、版本、审计及错误映射。

| 链路环节 | 具体产物 |
| --- | --- |
| 需求与方案 | [确认口径](examples/workflow-bookmark-tags/requirements.md)、[设计](examples/workflow-bookmark-tags/design.md)、[保持映射](examples/workflow-bookmark-tags/behavior-mapping.md) |
| 红灯、诊断、修复与绿灯 | [v1](examples/workflow-bookmark-tags/fixtures/TagService-v1.java)、[v2](examples/workflow-bookmark-tags/app/src/main/java/example/workflow/TagService.java)、[差异](examples/workflow-bookmark-tags/change.diff)、[运行回执](examples/workflow-bookmark-tags/evidence/runtime.json) |
| 冻结审查与接续 | [阶段记录](examples/workflow-bookmark-tags/trace.md)、[真实分离复核](examples/workflow-bookmark-tags/reviews/independent.md)、[交付](examples/workflow-bookmark-tags/delivery.md) |

真实结果只覆盖该新增Spring案例：v1为13测试、2指定失败、退出1；v2为13测试、0失败/错误/跳过、退出0。回执绑定运行器、源包、编译工程与最终候选。旧10个角色教材的历史未运行状态没有被改写。

业务角色由作者分阶段手动采用，一名真实分离上下文审阅者覆盖代码、语义、原则和文档范围；没有10个原生Agent自动调度。测试用MOCK环境，不启动监听、不连接数据库或外部服务；合成身份头不是生产认证，不代表部署、压力或多实例验收。

[先行执行文档](docs/java-spring-workflow-plan.md)记录本轮范围与步骤，[发布与验证结果](docs/java-spring-workflow-results.md)列实际主提交、真实运行和未验边界。具备POSIX、Python3.9+、JDK17+、Maven3.6.3+及公开Central网络条件时，可从项目根重跑：

```sh
python3 examples/workflow-bookmark-tags/run.py
```

可用`--java-home <jdk-home> --maven-home <maven-home>`选择本地工具。运行器隔离Maven配置/依赖缓存并只下载公开依赖；工具、缓存、target及原始构建日志不进Git。不安装系统工具、不改全局配置，缺环境明确NOT_RUN；下载受阻或断言失败不能报成功。

## 十个Agent分别怎样做事

从[十条完整案例](examples/README.md)选择角色：需求、实现、验证、代码审查、语义、原则、诊断、查询、交付规划与文档审验。每条都有输入、职责决策、Skill/Standards消费、具体产物、验收证据与停止/恢复。九个新增案例已按[执行文档](docs/agent-publication-plan.md)逐个独立提交，真实提交与验证见[发布结果](docs/agent-publication-results.md)。

查询案例提供独立虚构SQLite内存回放，已验证分页边界反例；它不证明MySQL执行计划或性能。其余新增案例是文档/静态分析，不是业务Agent自动运行。

## 先看一条完整链路：书签标题规范化

目标：允许书签所有者修改标题，对标题首尾空白做规范化，拒绝空结果，同时保留权限、版本冲突、标签、收藏序号和审计行为。

```text
任务与验收 → 实现者Agent → 代码实现Skill → 共用Standards
                                      ↓
                           最小Java差异 → 作者自查 → 交接
```

| 阅读顺序 | 实际内容 |
| --- | --- |
| [案例入口](examples/bookmark-title/README.md)与[任务](examples/bookmark-title/task.json) | 已决目标、写集、禁止动作、A1–A7验收 |
| [消费与行为映射](examples/bookmark-title/trace.md) | 为什么复用旧入口，哪些改变、哪些保持，如何选择用例 |
| [变更前](examples/bookmark-title/before/BookmarkService.java)、[变更后](examples/bookmark-title/after/BookmarkService.java)和[diff](examples/bookmark-title/change.diff) | 原有校验后引入规范化，复用写入与审计 |
| [12项契约检查](examples/bookmark-title/tests/BookmarkServiceTest.java) | 正常、拒绝、无变更及失败不写入的断言 |
| [验证与交接](examples/bookmark-title/result.md) | 已做检查、未验事项、同一候选的接续命令 |

所有对象、数据和规则独立虚构。示例是纯Java内存服务，可作为Spring业务层的独立单元；没有Spring容器、HTTP、数据库或真实认证。**这个早期纯Java角色案例尚未重跑**：原整理环境缺JDK的NOT_RUN记录保留；不以新增Spring案例的13项实跑覆盖这里的12项用例。

## 复制给AI：从案例开始

用能读取本地文件的AI编程助手打开整个仓库，输入：

> 按 agents/implementer.md 承担实现者职责。先读 skills/code-implementation/example.md 和 examples/bookmark-title/task.json，再核变更前源码。通过代码实现Skill消费相关Standards，解释旧行为、最小改点和验收映射，对照候选与用例给出自查、待验项及交接。我现在只让你审阅这个虚构案例，不修改全局配置、不连接服务、不提交或发布。

用于自己的工程时，可以这样开场：

> 按实现者Agent处理我的Java/Spring需求。先确认实际工程、需求验收、允许写集和已有改动，再选择Skill读取必要规范。优先复用旧能力，列出保持行为与最小改点；只在已授权范围修改，记录真实测试和未验证项，交可审核候选。

请求需要结合你的实际工程与当前授权；方法不替业务方确认未知语义，也不保证平台自动发现或派发Agent。

## 本地检查与案例运行

文档检查需要Python 3.9+，不下载依赖、不连接网络：

```sh
python3 scripts/check.py
python3 scripts/check_agent_cases.py
python3 scripts/check_workflow_cases.py
python3 scripts/check_graph_cases.py
python3 scripts/check_spring_build_cases.py
```

检查公开清单、相对引用、方法层交接、案例源码SHA与实际diff。新增Workflow检查器核阶段声明、源包/编译候选与运行回执一致性；它不重跑测试，也不代语义审查。Graph检查器还核源码/catalog身份、26回归和4实例回执一致性，不执行沙箱或Java。未知案例类型或目录报错，不静默跳过。构建Graph检查器核新旧回归身份、双工具JUnit/子JVM/打包摘要与失败阻断回执；四类显式分派，不实际构建。静态通过不代表公司敏感性、公开权利或业务运行全部得到证明。

本地有JDK 17+时，再运行：

```sh
python3 examples/bookmark-title/run.py
```

SQL局部语义回放可单独运行`python3 examples/review-cursor-pagination/replay.py`，只使用进程内虚构夹具。

Java运行器先核源码身份，再在临时目录分别编译基线与候选。预期基线暴露4个指定差距、候选满足12项；它核精确退出码、完整且不重复的用例集合及汇总行，拒绝异常终止误判。缺JDK退出2并打印NOT_RUN，不会安装工具。

## 当前覆盖与边界

| 内容 | 已交付与验证范围 |
| --- | --- |
| 三层方法与空表 | 可阅读、手工采用；引用与结构检查通过 |
| 十个角色的完整案例 | 各有输入、规范消费、分析/代码产物、证据与交接；案例目录逐项标注真实状态 |
| Python辅助脚本 | 清单与9个新增案例身份检查实跑通过；原Java运行器8项模拟分支通过 |
| SQL局部回放 | 仅虚构SQLite内存语义实跑，不连接外部数据库或代表MySQL性能 |
| 早期纯Java角色案例 | 12项契约用例未重跑，保留原NOT_RUN；不被新Spring实例覆盖 |
| 新增Spring集成案例 | 真实上下文/MockMvc红绿各13测试；同候选审查完成，范围见案例记录 |
| 生产Spring工程、数据库和模型接入 | 新案例仅本地MOCK上下文；生产系统、真实认证和数据库等由使用者另行验证 |
| Graph与实例资源 | 旧严格前台和新可信Maven/Gradle模式显式区分；真实worktree/继承沙箱/失败阻断，非原生LLM调度、跨平台或容器级任意后代隔离 |

方法不固定所有项目的JDK、Spring或数据库版本，按真实工程事实核适用性。源码身份变化后应刷新受影响证据；作者自查、独立审阅、真实运行和最终采用分别声明。

## 修改与扩展

新增方法先确定适用条件、输入输出、步骤、角色、验收和异常停止；已有方法保持单源。新增案例使用独立虚构数据，补保持映射、真实用例及未验范围。改动同步更新`public-manifest.json`并运行检查；不要把真实凭证、内部服务坐标、公司业务资料或原始会话带入仓库。

[协作约定](AGENTS.md) · [内容与许可边界](RIGHTS.md)

仓库中重新编写的文档、脚本和虚构示例采用 [MIT许可证](LICENSE)。该许可不扩展到使用者自己的公司代码、第三方资料或未纳入本仓库的素材。
