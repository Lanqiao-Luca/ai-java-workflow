# Docker Spring Graph真实结果

同一source、catalog与image ID，分别从macOS控制器与Linux VM内控制器实际运行。Linux容器的OS不用于冒充Linux宿主证据；本轮Linux宿主是自建测试VM，不是独立物理机器。实测arm64，Docker Engine29.5.2/cgroups v2，镜像JDK17.0.20.1+1、Maven3.9.11、Gradle8.14.3、Spring Boot3.5.16。

| 检查 | 两种宿主路径的真实结果 |
| --- | --- |
| 业务输入 | 原Java/POM/Gradle/MockMvc文件原字节；增加单一reflection MemberAccessor测试配置 |
| 并发 | title Maven与tags Gradle的容器Workflow及真实构建命令区间均重叠，作业峰值2 |
| 分支 | 两工具各3项目标测试，0失败/错误/跳过，并生成Boot可执行JAR |
| 集成 | 新worktree合入两精确提交，Maven和Gradle各8项完整测试及Boot JAR；源HEAD未变 |
| 实例 | 4套实例、7个探测/任务容器、12个独立命名卷；不bind宿主文件或socket |
| 内核探测 | 每实例18项通过，核root实际挂载为ro而不只依赖非root拒写，实际cgroup CPU/内存/PID、seccomp/NNP/cap-drop、宿主文件/Git/socket隔离、host-loopback隔离与自身IPC |
| Engine回归 | 每宿主13项全部通过、0跳过；含真实OOM、PID拒绝、整容器取消/setsid回收、内部timer独立截止、dirty host证据保留与2项明确host故障注入 |
| IO单元 | 每宿主8项通过，归档/路径/对象归属/策略检查，不能计作内核实跑 |
| 错误基线 | 每宿主3项测试中2项预期失败，后代阻断，无提升 |
| 缺依赖 | 每宿主关闭缓存种子后offline失败，后代阻断，无提升 |
| 回收 | 全部本次容器/卷、干净worktree与成功夹具回收；专用测试Engine过滤SDK labels复核剩余0容器/0卷 |

[macOS回执](evidence/runtime-darwin.json)、[Linux回执](evidence/runtime-linux.json)、[回归记录](evidence/tests.json)、[镜像/白名单上下文](evidence/image.json)与[环境](evidence/environment.json)分别记录。真实负例分别见[macOS](evidence/negative-darwin.json)、[Linux](evidence/negative-linux.json)。[最终文件清单](artifact-manifest.json)校核完整集合与字节。原8业务验收在不同工具/平台重复运行，不汇总成多个不同业务功能。

## 已处理的具体问题

独立复核关闭回收顺序问题：closed owner先拒绝，宿主漂移保留对应Docker输出，宿主确认安全移除后再删容器/卷，记录Docker待回收中间状态；定向3项独立回归通过。另独立确认无host watchdog时容器自身timer以124退出、PID0。未知响应保留ACTIVE与quarantine，不自动释放或重放。

初次实跑发现Docker私有PID是默认模式，CLI不接受--pid private；现在省略该参数并核inspect，拒绝host/container模式。日志驱动单文件配置显式禁压缩。归档mtime固定为非零时间，避免Maven跳过资源；Linux Mockito反射配置避免禁attach时产生重复线程转储。没有放宽文件/Git/socket/网络边界或提高日志上限来掩盖问题，原案例源码不改。

容器timer覆盖probe、缓存复制和命令，宿主另做超时/取消；PID命名空间结束停止setsid后代。创建/控制面不明时原路径、意图和资源保留；验证成功并全部回收后才删除夹具。已知合成负例由夹具显式丢弃停止输出，UNKNOWN不如此处理。

## 明确边界

Docker daemon、镜像、Linux内核与macOS VM是可信计算基，不保证消除所有漏洞或完整敌对多租户安全。命名卷无总磁盘硬配额，CPU/内存/PID为每容器限制，作业槽位不是JVM总数；跨宿主没有共享全局调度配额。API目前要求本地Unix socket、Linux Engine/cgroups v2、可验证配额与固定image ID，无旧后端或裸进程回退。

未验证独立物理Linux、amd64、rootless、Docker Desktop发行版、Windows容器或任意插件。源码仍受ASCII非隐藏、无链接/子模块/属性过滤器约束。未调用LLM、注册Agent、启动应用HTTP服务、访问数据库或部署；JAR结构/打包不等于应用启动和发布成功。在线镜像准备与network none的Graph执行分开，镜像/工具/缓存/原始日志/VM凭据不上传。

在已列明范围和检查方法下，候选中未发现未处理的问题；未检查或无法确认的内容已排除。
