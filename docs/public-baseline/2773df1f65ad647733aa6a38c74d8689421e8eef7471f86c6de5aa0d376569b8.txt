# Docker构建沙箱合同

目的：把可信Docker控制面与受限构建容器分开，用实际命名空间和cgroup限制承载Java子进程，不把目录或启动参数当作完成验收。

## 适用条件

Linux或macOS宿主已明确提供本地Unix socket的Linux Docker Engine、cgroups v2及已审阅内容地址镜像。macOS Engine运行在Linux VM中；容器OS不能代替宿主平台实测。

## 输入

冻结Git提交、具名Graph/Workflow、唯一run_id、独立运行根/CLI空配置、本地socket、已审核image ID、写集和有限预算。镜像在线预热与离线Graph分阶段。

## 操作步骤

1. 只用显式本地Engine及独立空Docker config，不继承个人上下文/认证、SSH agent或远程daemon。Docker控制面必须受信任，容器不接触其socket。
2. 宿主保存原worktree及Git管理；仅按白名单以有界tar传递无.git输入。拒绝路径穿越、隐藏路径、链接、设备、特权位与超量输出，不在宿主extractall任意容器归档。
3. 每实例独立容器及workspace/HOME/TMP命名volume，不bind宿主目录。只读root、非root、cap-drop ALL、no-new-privileges、默认seccomp；私有PID/IPC/cgroup命名空间，network none且不发布端口。自身loopback可用，宿主服务不可达。
4. 设置并核验实际内存/CPU/PID限制；拒绝host PID/network、特权、设备、额外cap/mount/port或无配额。命名volume没有总磁盘硬配额，不作相反承诺。
5. 先持久化名字/随机归属label，再分配Docker对象；作业取得共享租约才启动容器。所有inspect/stop/remove必须匹配本次ID及label，无docker prune或其他资源清理。
6. 超时/取消停止整个容器；容器内部也有独立墙钟截止。PID命名空间结束停止setsid后代；worker观察命名空间内残留并拒绝后台成功。daemon/响应/创建结果不明保留UNKNOWN、active占用与原根，不自动重试或释放。
7. 确认容器停止后读取报告/输出；比对worker与归档字节、宿主输入身份、完整逻辑写集，仅将声明源码写回。宿主再核HEAD/index/字节并提交，精确合入后重验。
8. 回收先核live owner、容器归属/停止及宿主工作树身份/干净状态。宿主确已安全回收后才删除对应Docker证据；漂移/失败默认保留。已知合成负例可由夹具显式丢弃停止输出，未知状态不能如此处理。

## 输出

实际宿主/Engine/镜像/来源身份、有效内核探测、JUnit/JAR摘要、候选提交、停止与回收及失败/未知。原始日志、控制状态、Docker配置、卷数据与构建上下文不自动公开。

## 角色职责

执行者通过Skill核输入与后端、交真实证据；可信宿主broker串行处理Git和Docker控制权限。角色文档不等于平台注册或AI模型已运行。

## 验收方法

每平台独立回执、真实Spring/Maven/Gradle并发与合并后验收；文件/Git/socket未暴露、宿主loopback隔离、自身IPC可用、实际cgroup限制及资源生命周期负例。mock API测试单独记录，不能代替内核/构建实跑。

## 异常与停止

缺Engine/镜像/配额或身份不符即拒绝，无裸进程/旧后端回退。未知保留占用与原始路径、禁止向旧PID发信号或自动重放。Docker daemon、镜像、Linux内核和macOS VM是可信计算基；不宣称绝对防逃逸或敌对多租户完整安全。当前复用broker仍限制ASCII非隐藏路径及无链接/子模块/属性过滤器输入。

返回：[Standards](README.md)。
