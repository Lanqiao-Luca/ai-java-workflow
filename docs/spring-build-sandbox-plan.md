# Maven/Gradle真实构建与Spring Boot并发Graph执行计划

状态：已先行提交的执行计划；以下保留实施顺序并补充最终落地边界。目标仓库为Lanqiao-Luca/ai-java-workflow，分支main，基线d412fa7cbb64604a18293240463dc4839f294e95。真实通过情况以后续回执为准，不在计划中预填成功。

## 目标和边界

在现有实例隔离机制旁新增显式构建模式，支持可信Java/Spring项目的Maven测试子JVM及Gradle受控构建。旧的禁止fork模式与历史案例字节/证据保留。全部代码和数据独立构造，不读取公司框架、业务、账号、私服或真实环境配置。原私有框架不读取、不修改。

不安装系统服务、改全局配置、注册Agent或启动长期后台任务。构建工具/公开依赖只下载到本机任务临时目录，不进入公开仓库。先记录本计划，再实现，验证后普通push至现有main，不建Release/CI或重写历史。

## 实施顺序

1. 核现有仓库、可用后端与公开工具。当前主机macOS，有sandbox-exec；无已安装Docker/Podman，不能声称容器已实测。
2. 保留现有严格后端；新增显式受信任构建后端。子进程继承文件/网络沙箱；宿主跟踪本次存活子进程、进程组、取消/超时及退出后的残留，未确认停止不得提升候选或复用占用。构建模式不宣称恶意多租户安全或任意恶意双重fork必可回收；具体平台局限须在结果说明。优先使用前台构建、禁复用Daemon、固定worker/fork数量；不能仅放开fork后继续宣称旧模式的拒绝派生保证。
3. JDK、Maven、Gradle及依赖必须来自官方公开来源并校验分发摘要；独立空HOME、空settings/init和独立缓存，不读用户.m2/.gradle。预热和离线执行分阶段：仅预热允许公开仓库联网，Graph执行外网拒绝，loopback按构建IPC需要显式放行且范围较宽，缺依赖即失败。
4. 每Workflow独立worktree/branch/sandbox/HOME/TMP/构建缓存与输出；只读工具根明确。构建产物不误提交为源码。固定base与精确候选提交，合并后重跑集成测试。共享额度限制Workflow作业而非假称所有JVM总数；内部并行显式限制。进程树追踪不是内核级任意后代容器：已知树/组与残留可核，无法可靠确认的脱离会话、异常退出或强杀情形保持UNKNOWN及占用，不按旧PID盲杀或自动复用。
5. 独立构造Spring Boot应用和两条功能Workflow；两个节点分别实现不同接口/规则并通过真实Spring/MockMvc测试，集成Workflow在合并后执行全套测试。真实记录依赖、峰值、时间重叠、JUnit报告、子JVM事实、源码/合同身份与回收结果。至少Maven完整Spring Graph，并对Gradle进行真实构建验证，不用文件存在冒充兼容。
6. 新增有效回归：子进程继承读写/Git/网络拒绝、同级缓存隔离、正常fork成功、超时/取消及残留不提升、失败阻断与合并后验收、依赖缺失失败。旧26项验证不被弱化。无需重复所有历史不变的业务用例。
7. 完成来源/公开内容扫描、引用/typed案例/清单检查，必要时针对具体边界独立复核。修复后重验受影响内容，不无限审计。保存私有运行日志与来源映射在项目外；公开仅审阅后的虚构摘要。
8. GitHub交付专员更新索引/能力边界/结果，按授权提交推送，核远程ref/全树字节、README/About。未实测能力明确列出。

## 验收与停止

须同时具备真实Maven与Gradle构建结果、Spring Graph两节点实际并发、集成后真实测试、子进程继承沙箱负例、独立缓存、失败不提升及最终来源身份一致。后端/工具/依赖缺失不裸跑回退；未知进程状态保留资源/占用并报告。若Gradle/特殊插件需要额外本机IPC或loopback，必须说明所需最小授权及实测范围，不能悄然开放外网。旧案例保持历史来源ID，不用旧Spring13结果替代新Graph结果。

## 参考

- Maven Surefire fork说明：https://maven.apache.org/surefire/maven-surefire-plugin/examples/fork-options-and-parallel-execution.html
- Gradle Daemon与no-daemon限制：https://docs.gradle.org/current/userguide/gradle_daemon.html

这些公开说明只用于技术设计，不替代本机运行证据。

## 发布与接续

本计划先行本地提交，后续实现和案例另行提交；最后统一普通push并核远程。不以本计划的设计目标预先声明Maven/Gradle或构建沙箱可用。只复核实际变化与必要验收；旧严格运行器、历史实跑回执、源ID和已公开案例原义保持。执行结果另写独立文档指向真实主提交，避免自身哈希循环。

## 最终落地约束

实际新增独立build_runtime/build_cache，不改变旧严格runtime/catalog与历史案例身份。两个功能分别采用Maven/Gradle，集成按顺序用两种工具各执行同一套8测试并打包Boot JAR；包结构检查不是应用启动/部署。新18回归与旧26回归、两真实构建失败及4实例继承探测分别留回执。

Gradle no-daemon仍生成一次性Daemon，因此默认拒绝detach保持，案例显式allow_observed_daemon，仅容许已观察且持续跟踪的继承沙箱后代，客户端结束最多3秒drain，残留拒绝提升。夹具固定IPv4/HOME/TMP/禁attach，Mockito用subclass方式。loopback可接触同机其他服务，非自身IPC隔离；Graph容量2是作业槽，节点实测树峰5进程。

只读官方工具/空HOME/独立配置与逐文件封存缓存；外网拒绝的离线Graph和联网预热分开。轮询不是pidfd或容器PID/cgroup，恶意瞬间doublefork与宿主SIGKILL不保证全后代回收，未知容量保持隔离。仅macOS可信构建、ASCII非隐藏路径及无链接/子模块/属性过滤器，不能宣称普通Spring工程可无条件直接运行。
