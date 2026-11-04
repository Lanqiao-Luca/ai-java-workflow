**目的**：组织可信 Java 构建任务的功能写集、工具输入和集成验证交接。

**适用于**：当前 macOS 可信构建后端的独立虚构工程；不沿用严格无 fork 模式的保证。

# Spring构建Workflow执行合同

Workflow消费[Java构建执行者职责](../agents/java-build-executor.md)，由该职责经构建隔离Skill取得规范；具体步骤由[Graph](../graphs/spring-build.md)组织。旧严格Workflow及其历史证据保持独立。

输入为冻结seed、来源明确的工具与公开缓存、独立实例资源、具体命令和源码写集。title/tags各只改一个接口文件，构建/缓存/测试报告全部进入HOME/TMP。接收方必须核精确commit与JUnit报告、JAR结构及摘要，不把仅存在文件当成已运行。

[构建任务](../examples/spring-build-graph/seed/build_task.py)是独立编写的确定性夹具，消费命令指定的Maven/Gradle与目标测试。它移除宿主注入选项，显式设置实例IPv4/HOME/TMP/JVM限制；offline与独立settings/cache为实际参数。Gradle测试选项绑定test任务，再运行build；不能把--tests错误地传给聚合build任务。

子JVM继承沙箱，外网拒绝但loopback允许范围较宽；只适合已审阅可信构建。可显式允许已观察一次性Daemon，禁止后台残留与未知进程被记为成功。取消/超时、异常停止和共享池隔离由宿主负责；无法确认时保留占用及资源。完整边界见Skill引用规范。

成功为退出0、准确成功行、目标JUnit数量且0失败/错误/跳过、独立测试JVM、Boot JAR结构有效、候选身份一致与观察到的树已停止。integration合入两个精确提交后，用两种工具各重跑全套验收。
