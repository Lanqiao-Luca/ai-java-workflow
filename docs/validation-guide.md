**目的**：按使用模式选择验证命令，区分当前结构检查、历史证据和真实运行验收。

**适用于**：本仓库使用者与维护者；执行模型、构建或容器前须分别满足环境与授权。

# 验证与运行指南

目的：按实际使用方式找到检查命令、运行前提与证据，不把静态通过等同于业务执行成功。

## 离线静态检查

从仓库根运行，需要 Python 3.9+，不下载依赖、不调用模型或连接业务服务：

```sh
python3 -B scripts/check_all.py
```

[总检查入口](../scripts/check_all.py)按下面的固定顺序运行八项检查，也可从其他工作目录通过脚本的绝对路径启动。每项最多 60 秒；失败立即停止并返回该子进程的非零退出码，信号终止映射为 shell 惯例的 `128 + 信号编号`，超时返回 124、启动失败返回 2、中断返回 130。未运行的后续项不会记为通过；正常结束才输出总 PASS。入口不是执行沙箱，也不覆盖真实模型、构建或容器测试。

修改总检查入口时，另运行 `python3 -B -m unittest discover -s tests -p test_check_all.py -v`，核失败不启动后续项、退出码、工作目录和超时等编排边界；这组测试不包含在默认八项检查中。

需要定位某一项问题时，可单独运行：

```sh
python3 -B scripts/check.py
python3 -B scripts/check_agent_cases.py
python3 -B scripts/check_workflow_cases.py
python3 -B scripts/check_graph_cases.py
python3 -B scripts/check_spring_build_cases.py
python3 -B scripts/check_docker_cases.py
python3 -B scripts/check_native_cases.py
python3 -B scripts/check_loop_cases.py
```

第一项同时消费只读文档声明工具，核正文首块目的/适用说明、全部 Markdown 的当前或保全分类，以及历史原件 SHA；它不理解业务目的或确认授权。可单独运行 `python3 -B tools/document_contracts.py`。

第一项核公开清单、隐藏文件/软链接、相对引用、方法字段、层级及早期案例身份。其余检查器校验各类案例的文件集合、声明和简化运行记录是否一致；它们不会重新构建 Spring、启动容器或调用真实模型。Loops 检查器另实际执行纯离线判定测试，覆盖模拟控制边界，不启动 Workflow 或业务操作。原始敏感性及公开权利仍需人工审阅。

## 持续回归与恢复

`python3 -B scripts/check_ci.py` 执行便携回归，包括受控原生协议、候选门禁与恢复/续跑。它与八项离线检查均进入 GitHub CI；另有 JDK 17 的实际公开 Spring 候选构建任务。具体入口、许可、检查点和未验边界见[恢复与 CI](native-recovery.md)。

## 技术设计到模块准备

责任 Agent 可在当前授权范围运行 `python3 -B workflows/examples/design-to-modules/run.py`，读取独立虚构设计/合同并实际核版本绑定、一个有效计划和四类拒绝。`python3 -B tools/module_plan.py --contract <独立设计合同.json> --plan <当前模块计划.json>` 只校验声明，成功返回 STRUCTURE_VALID，不代设计语义、真实仓库基线或实施许可。具体格式与未验范围见[案例](../workflows/examples/design-to-modules/README.md)。模块回归已进入便携 CI，不调用模型、Java 或外部服务。

## 按模式运行与核证

目标 Graph 的三条虚构路径及跨进程暂停/恢复由便携 CI 实际验证：

```sh
python3 -B graphs/examples/goal-loops/run.py
python3 -B scripts/run_goal_graph.py --run-root <仓库外全新私有目录>
```

第一条核三个预期控制结果，负例保留 PARTIAL/UNKNOWN；第二条仅 SUCCEEDED 才退出 0。暂停、接续、预算及读取权限见[案例说明](../graphs/examples/goal-loops/README.md)。程序使用真实墙钟和实际文件/Loop/Gate；业务、测试数字和审核上下文均为虚构，未运行新模型链或生产连接器。

新增两条虚构控制案例可直接运行，亦由便携 CI 实际调用：

```sh
python3 -B loops/examples/inspection/run.py
python3 -B loops/examples/defect/run.py
```

前者实际读取虚构日志、接口与构建文件，验证补证/缺口；后者运行整体验收与发现账本状态转换。两者的接口、测试数字、审核上下文和时钟均为模拟，不连接服务、不构建 Java，也不作为真实模型整改或业务验收证据。

| 模式 | 运行说明 | 已交付证据与限制 |
| --- | --- | --- |
| 纯 Java 角色案例 | [案例](../examples/bookmark-title/README.md)中的 `run.py`，需要 JDK 17+ | [结果](../examples/bookmark-title/result.md)保留原 NOT_RUN；不以其他案例覆盖 |
| SQL 局部回放 | `python3 -B examples/review-cursor-pagination/replay.py` | 虚构 SQLite 内存语义，不代表 MySQL 性能 |
| Spring 完整研发链 | [案例运行入口](../examples/workflow-bookmark-tags/README.md) | [发布记录](java-spring-workflow-results.md)：真实红绿测试、同候选审查 |
| 纯 Java 并发 Graph | [入口与参数](../examples/concurrent-java-graph/README.md) | [结果](../examples/concurrent-java-graph/result.md)：macOS 实验后端、并发及失败约束 |
| Maven / Gradle Graph | [入口与前提](../examples/spring-build-graph/README.md) | [结果](spring-build-sandbox-results.md)：公开依赖、显式工具及缓存、并发构建 |
| Docker Graph | [入口与前提](../examples/docker-spring-graph/README.md) | [结果](docker-sandbox-results.md)：双宿主运行、内核限制和未验范围 |
| 原生 Agent Graph | [入口与前提](../examples/native-spring-workflow/README.md) | [结果](native-agent-workflow-results.md)：真实原生上下文与 Spring 验证 |

需要实际运行时，按所选案例确认公开工程、JDK/构建工具、模型网络或 Docker Engine 条件。构建阶段只使用明确的公开或模拟配置，不继承公司私服、数据库或凭证。原生派工的模型网络及项目信任副作用见[派工接口](native-agent-adapter.md)，不与 Docker 离线构建边界混用。

## 如何报告结果

记录当前源码/候选身份、命令、环境、退出码和实际断言；明确 PASS、预期失败、mock、跳过及 NOT_RUN。输入或实现变化后重验受影响内容，旧回执不能直接覆盖新版本。构建打包不等于应用启动；静态检查通过不等于真实 Agent 完成；一个宿主通过不等于所有平台可用。

[项目入口](../README.md) · [案例目录](../examples/README.md)
