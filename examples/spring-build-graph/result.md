# Spring Graph实际结果

已在macOS arm64实际执行，工具为Temurin JDK17.0.21+9、Maven3.9.11、Gradle8.14.3、Spring Boot3.5.16。源码、API规则、Nebula/Comet/blue/green样例和Git仓库全部独立虚构。工具与公开依赖在空HOME准备，未接入公司服务/数据库/私服或个人构建缓存。

| 项目 | 实际结果 |
| --- | --- |
| 功能并发 | Maven title与Gradle tags执行时间重叠，Graph峰值2作业槽位 |
| 分支验收 | title：Maven3项；tags：Gradle3项；0失败/错误/跳过 |
| 集成输入 | 两份精确提交均为新实例集成候选祖先，源HEAD未变 |
| 集成验收 | Maven与Gradle各8项真实Spring/MockMvc测试；0失败/错误/跳过 |
| 打包 | 4次构建各生成1个Spring Boot可执行JAR，核JarLauncher/BOOT-INF与两接口class，保存大小及SHA；包未上传 |
| 测试进程 | 每次构建的测试JVM与构建launcher PID不同；摘要只保留事实 |
| 实例隔离 | Graph及3Workflow共4套资源，每套9项继承沙箱/自造canary/回环/停止探测通过 |
| 后代观察 | 每节点观察峰值5进程；Gradle含已观察脱离进程组的一次性Daemon，显式opt-in；最终观察到的树停止 |
| 回收 | 4份干净worktree、私有HOME/TMP移除；案例临时夹具清理 |
| 新构建回归 | 18项真实短回归通过、0跳过；独立复核分阶段实跑原12项与本次6项定向修复 |
| 旧严格回归 | 原26项全部重跑通过、0跳过；旧源码和历史案例字节保持 |
| 错误基线 | 3项测试中2项预期失败，exit1；后代BLOCKED，无候选提升 |
| 缺依赖 | 空公开缓存的offline构建exit1，无测试报告；后代BLOCKED，无候选提升 |

[运行回执](evidence/runtime.json)、[新回归](evidence/tests.json)、[旧严格回归](evidence/legacy-tests.json)、[真实负例](evidence/negative.json)、[工具校验](evidence/toolchain.json)分别记录。source_id绑定执行代码、seed、Graph/Workflow/Agent/Skill及构建规范；catalog_id绑定具体交接合同。[案例清单](artifact-manifest.json)校核完整文件集合与SHA。8项是每种工具运行的同一套完整业务测试，不将重复运行合计为16个不同业务验收点。

## 复核与实现范围

具体复核关闭了租约排队取消/截止状态丢失；缓存准入前置避免失败构造分配run；进程观察异常尽力停止自有组，但未知active仍隔离。显式一次性Daemon选项保留默认拒绝脱离会话，退出后只等待最多3秒；残留不提升。原始失败调试日志不上传，不将早期失败尝试记成最终通过。

收尾另定位并修复外层临时目录的生命周期遗漏：案例与负例仅在成功验证、观察树停止后显式删除原根；任意异常/UNKNOWN保留原路径及Git指针/策略/状态，不复制后删原根。依赖预热也监督本次子树与超时，异常保留UNKNOWN、不seal缓存；复用缓存先去旧marker，执行缓存复制后核实际副本身份。新增6项定向测试与真实监督预热、Graph及负例用最终同字节重新验证。

这个可信构建模式允许fork和较宽loopback访问，不等同旧严格模式的fork/网络全拒绝。测试夹具强制JVM IPv4回环、实例HOME/TMP和禁attach，Mockito使用subclass方式；未承诺inline/native插件或任意现有工程兼容。外网拒绝与离线缺依赖失败均有真实负例。

轮询不能保证抓到恶意瞬间doublefork重归属，启动时间检查不是pidfd；宿主强杀后不自动回收所有后代。未知容量隔离且不自动续跑。没有容器PID命名空间/cgroup、总RAM/总磁盘配额或Linux/Windows后端；只支持当前ASCII非隐藏源路径及无链接/子模块/属性过滤器的受限输入。作业容量2不等于JVM总数2。

当前没有原生LLM/Agent调用、应用启动/真实HTTP端口验收、数据库或生产部署。Boot JAR结构检查和真实打包不等于启动/发布成功。README中的公开依赖预热明确允许联网，Graph阶段保持offline与外网拒绝，二者不混淆。

在已列明范围和检查方法下，候选中未发现未处理的问题；未检查或无法确认的内容已排除。
