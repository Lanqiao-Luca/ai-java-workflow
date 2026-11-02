# Spring Boot并发构建Graph

独立虚构的两个接口需求：标题trim并拒绝空白，标签trim去重保序并拒绝空项。使用真正的Spring Boot 3.5.16、MockMvc、Maven 3.9.11、Gradle 8.14.3和JDK 17，不使用公司接口、账号、数据库、日志或私服。

| Workflow | 真实动作与验收 |
| --- | --- |
| title | 独立worktree实现标题接口；Maven verify；3项MockMvc测试与Spring Boot可执行JAR |
| tags | 独立worktree实现标签接口；Gradle test/build；3项MockMvc测试与Spring Boot可执行JAR |
| integration | 等两节点成功，在新worktree合入两个精确commit；Maven、Gradle分别重跑全部8项测试并各自打包 |

两个功能必须实际时间重叠，集成在两者结束后启动。Graph与3个Workflow共4套实例资源，每套独立分支、worktree、沙箱、HOME/TMP；缓存从显式封存公开种子逐份复制，不共享可写状态。构建产物和报告进入TMP，不进入候选源码提交；结果记录JAR摘要与结构，不能据结构检查宣称已部署或启动HTTP服务。

[Graph合同](../../graphs/spring-build.md) · [定义](../../graphs/spring-build.json) · [Workflow执行合同](../../workflows/spring-build.md) · [需求与过程](trace.md) · [真实结果](result.md) · [运行回执](evidence/runtime.json)

## 重跑步骤

前提：macOS可用sandbox-exec、Python 3.9+、Git、明确本地JDK17/Maven3.9.11/Gradle8.14.3目录。Apple sandbox-exec已弃用，没有跨平台或裸进程回退。工具从官方发行来源取得并核验摘要；本项目不自动安装工具或系统服务。具体已用来源见[工具证据](evidence/toolchain.json)。

1. 从项目根显式准备公开依赖。这一步会联网，仅访问构建文件声明的公开Maven Central，使用全新HOME，不读个人`.m2`或`.gradle`。输出目录必须不存在；工具路径和输出目录由使用者选择。

```sh
python3 -B examples/spring-build-graph/prepare.py \
  --java-home <JDK目录> --maven-home <Maven目录> --gradle-home <Gradle目录> \
  --output <仓库外全新预热目录>
```

允许显式传`--reuse-public-home <先前预热目录/home>`；只接受逐文件SHA一致的本案例公开缓存，不自动寻找个人缓存。缓存清单只是字节身份，使用者仍须确认来源。准备失败保留本地日志供检查，换新目录重做，不把失败记通过。

2. 运行完全离线的Graph。工具和种子显式挂载，外网被内核拒绝；缺依赖直接失败，不临时联网下载。

```sh
python3 -B examples/spring-build-graph/run.py \
  --java-home <JDK目录> --maven-home <Maven目录> --gradle-home <Gradle目录> \
  --prepared-home <预热目录/home> --output <仓库外新的摘要文件>
```

运行器只造临时虚构仓库；生成失败时会保留独立系统临时夹具并报告位置，原始日志不自动公开。成功验证后回收自身临时资源，不改项目main、不push、不继承现有业务仓库改动。测试使用MockMvc，不连接数据库或生产服务。

3. 负例可单独运行：

```sh
python3 -B examples/spring-build-graph/negative.py \
  --java-home <JDK目录> --maven-home <Maven目录> \
  --prepared-home <预热目录/home> --output <仓库外新的负例摘要>
```

预期：基线占位实现的3项测试中2项失败；空公开缓存导致offline依赖错误。两者都不提升候选，后代阻断。[负例回执](evidence/negative.json)与[构建回归](evidence/tests.json)分开记录，不能把预期失败包装成业务测试全绿。

## 构建模式的实际边界

显式可信构建模式允许fork，子进程继承Seatbelt文件/Git/外网限制。Gradle即使no-daemon也可能启动一次性Daemon；本案例显式允许**已观察且持续跟踪**的继承沙箱后代，客户端完成后最多3秒等待自行停止，仍残留则停止并拒绝。默认模式仍拒绝脱离会话，旧严格案例和来源身份保持不变。

Gradle IPC允许loopback，权限可接触同机其他服务，不是“只允许自身IPC”；案例仅使用自身进程和自造服务。为适配回环规则，夹具为所有构建/测试JVM设置固定IPv4、实例HOME/TMP并禁用attach，覆盖环境注入。Mockito使用subclass MockMaker，不依赖外部自附加进程；不承诺所有Mockito inline/native插件兼容。

宿主轮询PID/父子/组/启动元数据，不读取宿主进程环境或命令行；无法保证捕获瞬间恶意doublefork重归属，也不提供pidfd原子句柄、容器PID命名空间/cgroup或敌对多租户隔离。未知占用保持active并隔离池，不自动杀旧PID、释放或重放。只回收已确认停止且干净的资源。

额度为同运行根共享的Workflow作业槽位；本例Maven forkCount=1、Gradle max-workers=1，并不等于最多2个JVM。单文件256MiB与CPU/墙钟限制不等于总RAM/总磁盘硬限制。当前源快照仍只接受ASCII非隐藏相对路径，拒符号链接、子模块及属性过滤器；示例不是任意既有Spring仓库的一键接入器。

角色/Skill参与合同来源身份，执行器运行确定性夹具命令，没有调用LLM或注册平台Agent。未做应用启动、生产部署、真实数据库或Linux/Windows后端验证。

返回：[案例目录](../README.md)。
