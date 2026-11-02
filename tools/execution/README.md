# 本地执行机制

这里是新编写的共享执行代码，不是另一层方法或私有企业Tools副本。

- [runtime.py](runtime.py)：快照/worktree、实际Seatbelt、持久额度/状态、DAG调度与回收。
- [catalog.py](catalog.py)：将Graph引用解析为具名Workflow合同，拒绝未知字段、路径越界及缺来源。
- [命令入口](../../scripts/run_graph.py)：显式执行/取消/审计检查，不推送、不注册平台。
- [真实回归](../../tests/test_execution.py)：仅临时虚构Git与自造canary，不读真实凭证。

旧严格前台模式的平台：仅macOS sandbox-exec实验后端。目录/环境变量清理本身不作为沙箱证明。默认deny-by-default，允许必要系统/工具读、文件metadata及根目录枚举，拒相邻内容/写入、Git管理目录、网络、fork和脱离会话。不是恶意多租户安全产品。

资源：每Graph额度+同运行根跨Graph租约；墙钟/CPU及单文件8MiB，日志超过64KiB拒收。没有总RAM、总磁盘或机器上所有外部进程的统一配额。池的active标记先持久化再派发；宿主退出留下未知占用时隔离，不能换ID清零。只支持审计恢复，不自动续跑。

调用者须信任并授权仓库与只读工具根，禁止把个人根目录或凭证目录当工具挂载。不同runtime_root的池独立，实际使用应由宿主统一选择运行根。Git钩子、全局配置/属性和终端认证禁用，源属性过滤器/子模块/符号链接不支持；本引擎不自动安装依赖、联网或发布。

源快照准入目前仅接受ASCII相对路径，并拒绝所有隐藏路径（包括常见的`.gitignore`、`.github`）；不支持符号链接、子模块和属性过滤器。此受限参考实现验证的是独立虚构案例，不能宣称可直接运行任意干净Java工程。

## 显式可信构建模式

[build_runtime.py](build_runtime.py)在旧严格机制旁新增可信构建树后端，[build_cache.py](build_cache.py)封存/复制显式公开缓存，[构建入口](../../scripts/run_build_graph.py)解析[Spring Graph](../../graphs/spring-build.md)。旧runtime/catalog字节与历史ID保持。

新模式允许fork和较宽loopback，外网拒绝；不隔离同机其他loopback服务。默认拒脱离，案例显式opt-in已观察一次性Daemon并最多3秒drain；未知占用隔离。作业槽位不等于所有JVM总数，轮询无法保证恶意快速doublefork、宿主强杀后的任意后代回收或容器级多租户边界。只适用可信源码/工具/插件与当前ASCII非隐藏源准入，不支持任意现有Spring仓库。

[完整Spring案例](../../examples/spring-build-graph/README.md)真实Maven/Gradle测试与Boot JAR打包通过，未启动应用或部署。依赖预热联网与Graph离线分开，工具/缓存/日志不进Git；不自动安装系统工具或启动后台服务。

[build_fixture.py](build_fixture.py)保留异常/UNKNOWN的原运行目录；公开依赖预热同样监督已观察子树并等待停止，未确认停止不封存缓存。仅成功验证且确认停止后回收。

## Docker容器模式

[Docker机制](Docker.md)与[显式CLI](../../scripts/run_docker_graph.py)新增本地Linux Engine/cgroups v2后端，不初始化Seatbelt；Linux/macOS控制器分别实测，范围见[完整Docker案例](../../examples/docker-spring-graph/README.md)。network none隔宿主loopback，私有PID结束停止setsid后代；有界tar代替宿主目录/socket挂载。控制面未知保留原根/租约；Engine/镜像/内核/VM是可信边界，命名卷无总磁盘硬配额。在线镜像准备与离线Graph分开，无注册、自动模型调用或裸跑回退。
