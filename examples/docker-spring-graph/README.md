# Docker跨平台Spring Boot Graph

沿用[原Spring案例](../spring-build-graph/README.md)的标题/标签需求、Java/POM/Gradle与MockMvc测试。Nebula、Comet、blue/green均独立虚构；不使用公司接口、账号、数据库、日志、私服或私人Docker配置。

两个功能Workflow分别运行Maven、Gradle并实际时间重叠，各3项目标测试和Boot JAR；集成在两个精确提交合入后，两种工具各重跑8项完整测试与打包。原8项业务验收重复执行，不合计成16个不同验收点。

## 实现与来源

- [Graph合同](../../graphs/docker-spring.md)与[定义](../../graphs/docker-spring.json)、[Workflow合同](../../workflows/docker-spring.md)。
- 原[seed](../spring-build-graph/seed/build_task.py)保持原字节；仅新增[reflection SPI配置](overlay/src/test/resources/mockito-extensions/org.mockito.plugins.MemberAccessor)。这是Mockito公开扩展接口，用于避免Linux禁attach后MemberAccessor自动附加产生线程转储，不改变业务逻辑或放宽沙箱。
- [Docker机制](../../tools/execution/Docker.md)、[镜像Dockerfile](../../tools/docker/Dockerfile)与[不可变worker](../../tools/docker/worker.py)。
- [结果](result.md)记录两个实际宿主路径、来源/image ID、JUnit/JAR及真实限制与失败控制；[完整文件清单](artifact-manifest.json)核集合与字节。

4套实例各有worktree及3个独立volume，探测/任务使用分离容器，共7容器和12卷。宿主Git管理、Docker socket和个人目录不挂入容器；输入输出通过白名单有界tar，宿主仅写回声明源文件。原始日志、镜像、卷、工具包与上下文不上传。

## 重跑：明确准备与离线执行

前提：Linux或macOS上已有明确本地Unix socket的Linux Docker Engine、cgroups v2、Python3.9+、Git。后端不安装Docker或自动启动VM；缺环境不回退旧后端。本轮实测arm64：macOS CLI通过独立Lima VM Engine，另在同一Linux VM内运行Linux控制器；未实跑独立物理Linux、amd64、rootless Engine、Docker Desktop或Windows容器。

1. 在仓库外空CLI配置下，显式拉取[镜像证据](evidence/image.json)中的官方base_image完整digest。在线下载只针对公开镜像，不继承私人上下文：

```sh
<docker> --config <仓库外空CLI目录> --host <unix:///明确socket> pull <eclipse-temurin@sha256:完整摘要>
```

2. 显式准备本地构建镜像。Maven/Gradle工具归档从[原工具证据](../spring-build-graph/evidence/toolchain.json)的官方来源取得；脚本复核已公开摘要，只复制原案例清单的seed、SDK文件和两归档，不把整个目录当作build context。

```sh
python3 -B examples/docker-spring-graph/build.py \
  --docker <客户端绝对路径> --socket <unix:///明确socket> \
  --base-image <eclipse-temurin@sha256:完整摘要> \
  --maven-archive <Maven3.9.11.tar.gz> --gradle-archive <Gradle8.14.3.zip> \
  --output <仓库外新的镜像准备目录>
```

这个阶段允许公开APT/Maven Central联网，Docker build缓存可复用；只有成功镜像与context/image身份才记通过。输出保存image-receipt.json、image-id.txt和私有构建日志；镜像仅在本地，不push到registry。当前静态CLI使用Engine支持的classic builder；不支持该接口的Engine需另行适配，不静默安装插件。

3. 使用完整`sha256:...`本地image ID运行。network none保留容器自身loopback，隔离宿主服务和外网，Gradle一次性Daemon仍在同一PID命名空间。

```sh
python3 -B examples/docker-spring-graph/run.py \
  --docker <客户端绝对路径> --socket <unix:///明确socket> --image <sha256:完整imageID> \
  --host-description <macos-vm-engine或linux-vm-engine或linux-native-engine> \
  --output <仓库外新的摘要文件>
```

运行器创建独立临时Git与资源，不改SDK main、不stash现有改动、不推送。成功验证且Docker/宿主资源已回收才删除原临时根；失败或UNKNOWN保留原根/意图/卷并报告，不复制后删原根。自己的后台残留不能记成功；不明daemon响应保留active并隔离池，不自动重放或重用容量。

4. 真实负例与底层测试分别执行：

```sh
python3 -B examples/docker-spring-graph/negative.py --docker <客户端> --socket <unix:///socket> --image <sha256:ID> --output <仓库外新摘要>
python3 -B tests/test_docker_backend.py --docker <客户端> --socket <unix:///socket> --image <sha256:ID> -v
python3 -B tests/test_docker_io.py -v
```

错误基线3项中2项失败；不复制依赖种子时offline缺依赖失败；均阻断后代且不提升。负例夹具只在确认停止后显式丢弃自己的合成输出。默认Engine测试缺参数为NOT_RUN，不把纯单元/mock当成Docker实跑。

## 支持范围

每容器非root、只读root、cap-drop ALL、no-new-privileges、默认seccomp、私有PID/IPC/cgroup、network none、CPU/内存/PID限额均有实际探测。当前示例每容器2CPU/2GiB/256 PID；底层测试另用64MiB/32 PID触发真实OOM与fork拒绝。PID计数包含线程，作业槽位不是JVM总数。

没有命名volume总磁盘硬配额；Docker daemon/镜像/内核/VM是可信计算基，不承诺绝对防逃逸或敌对多租户完整安全。同宿主同运行根共用作业池，跨宿主不共享全局配额。输入仍限定ASCII非隐藏路径、无链接/子模块/属性过滤器，非任意已有Spring项目的一键兼容器。

源码/具体交接合同、image和两平台回执分别绑定；旧macOS案例保持独立历史，不改写为Docker通过。未调用LLM或注册Agent，未运行应用HTTP服务、生产数据库或部署；Boot JAR结构/打包不等于启动与发布验收。

返回：[案例目录](../README.md)。
