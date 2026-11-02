# Spring Boot可信构建Graph交付结果

[先行计划提交](https://github.com/Lanqiao-Luca/ai-java-workflow/commit/502413e77650933614da765940055a08df6719c2)先于实现落地；[主交付提交](https://github.com/Lanqiao-Luca/ai-java-workflow/commit/0113724ebd95638aff2155581b4b7002d4d567b3)已普通推送main，远程ref与全树254个文件blob身份和公开清单逐项匹配。本文作为后续结果记录，不参与案例源码身份或假称自身提交早已被验证。

## 交付与真实验证

新增独立可信构建后端、公开缓存封存、专门构建职责/Skill/规范、3份Workflow定义、Graph和[完整Spring Boot案例](../examples/spring-build-graph/README.md)。全部为独立虚构代码与数据；没有复制公司工具、资料、原始日志或私有审计。旧严格runtime/catalog、旧角色与案例身份保持。

- Maven标题3项和Gradle标签3项Spring/MockMvc测试真实并发；集成合入精确提交后每种工具通过同一套8测试，0失败/错误/跳过。
- 4次构建分别打包Boot JAR并核结构/摘要，二进制未上传，未启动应用或部署；每次都有独立测试JVM。
- Graph加3Workflow共4实例，每实例9项继承沙箱/自造canary探测；依赖、合并祖先、源HEAD不变与干净资源回收均有回执。容量2是作业槽位，节点观察树峰5进程。
- 新18回归真实通过、0跳过，包含6项生命周期定向回归；独立复核先跑原12项与drain正例，修复后另跑新增6项。旧严格26回归的源码保持先前同字节实跑，0跳过。实际构建和回归来源匹配当前源码，不为发布重复执行同字节全套构建。
- 错误基线3测试中2失败及空缓存offline依赖失败均退出1、阻断后代且不提升候选。[真实运行与负例摘要](../examples/spring-build-graph/result.md)分别记录，不冒称业务全绿。

公开检查器5项全部通过，覆盖清单/引用/层间职责及4类案例显式分派。新增构建检查器核源码/catalog身份、双工具JUnit/子JVM/打包摘要、新旧回归、失败阻断及案例全文件SHA。另以临时副本验证有效输入、源码/合同漂移、探测失败、JUnit失败、缺独立JVM、错误提升、旧源码漂移、跳过回归及额外文件等控制，4个typed入口均拒绝未知类型；共17项检查通过（含预热树未停止回执拒绝）。这些是被动检查器验证，不等于重新运行Spring或证明任意输入安全。

主交付检查为254文件、541个本地引用；生命周期修复后255文件、542个本地引用。发布阶段发现新Workflow正文直链Skill与既有层间规则冲突，定向改为经Agent职责入口消费；该正文不在源码/catalog身份集，修后主引用与全部typed检查通过，没有改变实跑字节。

## 生命周期定向修复

主交付之后发现异常包装路径可能自动移除UNKNOWN原运行根、预热超时仅停止helper的问题；保留原历史，按[普通修复提交](https://github.com/Lanqiao-Luca/ai-java-workflow/commit/1f1e346ed0244216771d18e49dccb4b523669218)关闭具体缺陷。新helper保留异常/UNKNOWN的原目录身份，仅确认停止与成功验证后回收；预热监督已观察子树，异常不封存缓存，复用种子移除marker后再封存，构建复制后再核实际缓存身份。

修复后重新真实执行监督预热（Maven、Gradle各8测试与Boot JAR）、并发Graph、两失败负例及18项回归；最终源码身份为`dd45a59d3b6295aa5dd8001b18186a79bae3d3eecb175b6a219d8a07c85769e9`，catalog身份保持`ad01120e8ef4081e37b1b12e28f8d26869f91dc82143790ad70ff9ddba579969`。公开回执和完整案例清单均已刷新，旧严格历史没有被覆盖。发布阶段的被动检查通过后不重复同字节构建。

## 支持边界

旧严格前台模式保持deny fork；新模式是显式macOS实验可信构建，允许fork和较宽loopback，Graph阶段外网拒绝。预热单独从公开Central联网，空HOME、独立配置及封存缓存不继承个人私服。loopback可以接触其他同机服务，不是自身IPC隔离。

Gradle no-daemon仍可能产生一次性Daemon；默认拒脱离，案例明确opt-in已观察且持续跟踪后代，客户端完成后最多3秒drain，残留不提升。未知active保持占用并隔离池。轮询不能保证恶意快速doublefork或宿主SIGKILL后的任意后代回收，不提供容器PID/cgroup、总RAM/磁盘硬配额或敌对多租户保证。

仅已测macOS弃用sandbox-exec，源路径限ASCII非隐藏且无链接/子模块/属性过滤器；非任意现有Spring工程一键运行器。没有原生LLM调度、Linux/Windows后端、应用启动、真实数据库、生产部署、CI或Release。工具/缓存/运行根及私有核验留在仓库外。

在已列明范围和检查方法下，候选中未发现未处理的问题；未检查或无法确认的内容已排除。
