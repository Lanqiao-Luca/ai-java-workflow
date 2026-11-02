# Docker容器沙箱与跨平台Spring Graph执行计划

状态：先行执行计划，未预填实跑结论。目标仓库Lanqiao-Luca/ai-java-workflow，分支main，基线7221255e7d03a3b017cef727990699900cfd5ea3。目标是在现有项目新增Docker后端，保留旧严格/macOS可信构建模式与历史字节，沿用同一Spring Boot虚构需求/源码和Maven、Gradle验收，验证后普通提交至现有main。

## 范围与环境

不读取或修改原私有框架；不使用公司数据、账号、服务、私服、日志或个人Docker配置。仅使用现有公开项目及独立代码。工具、镜像、依赖、运行根、密钥和原始日志留在项目外，不推镜像仓库、不建Release/CI、不改系统服务/全局配置或历史。

当前macOS没有Docker客户端/Engine。先尝试在任务临时目录创建隔离测试VM：不挂个人目录/SSH agent，不用现有Docker上下文或凭证，VM仅用于本次验证，完成后停止。从macOS客户端与Linux guest分别真实运行；Linux VM结果不表述为独立物理机验证。若虚拟化或引擎不可用，明确登记真实验证阻塞，不用mock或Mac旧后端冒充Docker成功。

## 实施顺序

1. 先保存本计划，再实施。核官方Docker/Lima接口、发行摘要与镜像身份；只连接明确的本地Unix socket，拒绝隐式远程上下文/凭证继承。安装/配置均限独立任务目录；超出授权才集中询问。
2. 新Docker后端与入口，不修改旧source/catalog覆盖的历史源。复用Graph依赖、Git串行broker、候选HEAD/index/字节/写集核验与共享作业租约；避免Linux入口先初始化macOS专用后端。
3. 每Graph/Workflow实例独立容器及命名volume，固定内容地址镜像。使用只读根、非root用户、cap-drop ALL、no-new-privileges、默认seccomp、独立PID/IPC/cgroup namespace、network none，无端口发布、host网络、特权、设备或Docker socket挂载。配置CPU/内存/PID限制，并实测有效性，不把CLI参数存在视为生效。
4. 不将带.git的host worktree直接RW挂进容器。明确白名单导出无Git的输入，经受限归档复制到本次容器；依赖来自只读公开种子，各实例复制到自己的HOME。容器确认退出后审阅输出集合/类型/身份，只将声明源码写回host候选，宿主再核精确提交。拒链接、特殊文件、路径穿越与未声明输出，不解压任意tar到host目录。
5. 先持久化资源意图/归属，再创建容器/卷；所有停止/删除仅针对本次已验证label和ID。超时/取消作用于整个容器；确认stopped后才释放租约或回收。daemon离线/CLI中断/创建结果不明保留UNKNOWN与active占用，不自动重放或删除原运行根。禁止docker prune、清理其他容器或以名称猜资源。
6. 公开工具与依赖的在线镜像构建/预热，与network none的离线Graph分开。build context必须白名单，仅合成应用、bootstrap/Dockerfile和已校验公开工具；不发送源.git、审计、用户HOME、socket、私有缓存或原始材料。镜像仅本地测试，不推registry。
7. 沿用标题/标签两个虚构需求：Maven title与Gradle tags实际并发，各3项目标测试和Boot JAR；集成节点合入两精确提交后两种工具各8项测试与JAR。独立JVM、合并后重验、来源/镜像/平台身份、停止与回收均有回执。macOS与Linux宿主分别验证，不把Linux容器OS等同Linux宿主实跑。
8. 实际负例覆盖容器外文件/Git/socket缺失、只读root、网络隔离但自身loopback可用、子进程及setsid无法跨容器存活、CPU/内存/PID生效、超时/取消/未知daemon不提升、资源归属、防路径穿越/链接、缺依赖与错误基线。模拟API测试明确标mock，不能替代真实内核/构建结果。缺环境则真实执行安全可做部分并报告未实测。
9. 私有审阅清单/总结外置；新公开内容及最终候选全树复查。独立复核只针对实际新增边界和最终身份。GitHub交付专员更新类型检查/索引/能力边界与结果，普通push并核远程ref/全树、About实值；旧案例保持历史事实，不反写成Docker通过。

## 验收与停止

需要可核对的镜像内容地址与在线准备身份、macOS/Linux宿主结果、实际Spring Graph并发/精确合并/两工具测试打包、内核限制负例、退出后无本次活容器、独立volume及回收、失败不提升与UNKNOWN保留。镜像/引擎/配额/资源身份不明均fail closed，无裸进程或旧后端自动回退。Docker daemon是受信任控制面，宿主/内核/VM及镜像漏洞不由本项目消除；命名volume无统一磁盘硬配额须明确。仅支持明确本地Engine与所验证Linux容器，不宣称Windows容器、任意远程daemon或不可信多租户绝对安全。

## 官方参考

- https://docs.docker.com/engine/containers/run/
- https://docs.docker.com/reference/cli/docker/container/run/
- https://docs.docker.com/engine/network/
- https://lima-vm.io/docs/installation/
- https://lima-vm.io/docs/config/vmtype/vz/

## 交付顺序

本计划先行本地提交；当前不修改实现、历史案例或About，也不将计划当成Docker支持已可用。实际验证完成后再提交实现、完整案例与结果，统一普通push并读回核验。
