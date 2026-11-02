# Docker沙箱交付与验证结果

按业务目的拆分交付，先[执行计划](docker-sandbox-plan.md)，再后端安全机制、完整案例与类型检查，最后结果和展示；不按文件数机械拆分。

| 业务目的 | 实际提交 |
| --- | --- |
| 先行计划 | [7e5534a](https://github.com/Lanqiao-Luca/ai-java-workflow/commit/7e5534a6cba064f30eefb67a00d187084f36af81) |
| 后端、资源、安全输入输出、镜像worker、契约和测试 | [3d271ec](https://github.com/Lanqiao-Luca/ai-java-workflow/commit/3d271ecd85fb5fa40ecaa2186ee9d9aff3732625) |
| 双宿主Spring Graph、完整案例与第五类检查接入 | [0a6c87d](https://github.com/Lanqiao-Luca/ai-java-workflow/commit/0a6c87df29144a59b72a6d19ce37f83a7315873a) |

## 实际运行

[完整案例](../examples/docker-spring-graph/README.md)保留原公开Spring seed字节，仅新增公开Mockito reflection MemberAccessor配置；不使用公司数据、服务、私服、账号或私人Docker上下文。固定source、catalog、image ID分别绑定执行输入、角色交接和本地构建镜像。

同一arm64 Linux Engine29.5.2/cgroups v2，分别从macOS控制器与同一Lima Linux VM内控制器真实执行；Linux guest不是独立物理机器。两条功能Workflow及实际命令窗口重叠，Maven标题3项、Gradle标签3项；精确合入后每工具8项相同Spring/MockMvc测试及Boot JAR打包，0失败/错误/跳过。每平台4实例、7容器/12卷，每实例18项实际探测，核非root、只读root真实挂载、cap/NNP/seccomp、CPU/内存/PID限额与宿主文件/Git/socket/loopback隔离。

每宿主13项Engine回归通过，含2项明确宿主故障注入；8项IO单元通过，单元检查不计内核证据。两平台错误基线3项中2失败、无缓存offline缺依赖失败均阻断后代且不提升。专用Engine按SDK标签核剩余0容器/0卷，独立VM正常停止。镜像/JAR/工具/缓存/上下文/日志/VM状态均未上传；Boot JAR结构与打包不等于应用启动或部署。

[实际结果](../examples/docker-spring-graph/result.md)与[环境来源](../examples/docker-spring-graph/evidence/environment.json)区分已验和未验；macOS静态CLI摘要仅是官方HTTPS下载后本地记录，未宣称取得供应商独立摘要。回归和负例image ID按最终实跑launcher参数补记，provenance明确说明collector补充；IO单元不绑定为镜像测试。

## 发布检查

后端提交时公开清单269文件/560引用、旧5检查器、CLI help及8项IO单元通过；案例提交时292文件/591引用、6检查器通过。新增被动Docker检查核source/catalog/image/context白名单、双宿主回执、AST13+8用例名、18探测、失败阻断、资源关闭与完整案例SHA；五类显式分派拒绝未知目录/类型。

在临时公开副本运行24项有效/变异控制，覆盖源码/合同/image/context/宿主漂移、探测失败、命令不重叠、JUnit失败、缺独立测试JVM、回归跳过、错误提升、资源未清理和五入口未知类型拒绝。发布阶段没有重启VM或重复已匹配同字节的真实构建/Engine回归。静态检查不替代业务语义、来源权限或任意恶意代码隔离证明。

## 支持边界

明确本地Unix socket与Linux Engine/cgroups v2，内容地址镜像，非root/只读root/network none及独立命名空间；输入输出有界白名单tar，不bind宿主目录/socket，不任意extractall。超时/取消停止整个容器，控制面未知保留原根/active与资源归属，不自动重放或清理其他对象；无Seatbelt或裸跑回退。

Docker daemon、镜像、Linux内核与macOS VM是可信计算基，不保证绝对防逃逸或敌对多租户完整安全。命名卷无总磁盘硬配额，作业槽不是JVM总数，跨宿主不共享全局额度。仍限ASCII非隐藏源路径及无链接/子模块/属性过滤器；未验amd64/rootless/Docker Desktop/Windows容器/独立物理Linux。无原生LLM调度、应用启动、真实数据库或部署，旧后端与历史案例结论保持原义。未创建Release、CI、远程VM或长期服务，未修改全局配置或重写历史。

在已列明范围和检查方法下，候选中未发现未处理的问题；未检查或无法确认的内容已排除。
