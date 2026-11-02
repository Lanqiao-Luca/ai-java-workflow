# 完整Workflow案例：书签标签替换

一个独立虚构需求，串起需求→设计/实现→验证失败→诊断→修复→复验→代码/语义/原则审查→文档与交付。所有代码、数据、规则和请求均为新编写，不含公司资料。

本例提供真实Spring Boot应用、13项SpringBootTest/MockMvc请求链测试及可重跑的红绿对照。它没有生产认证、数据库、外部服务或部署；不是10个原生Agent自动运行。

## 从输入到交付

| 先看什么 | 文件与结果 |
| --- | --- |
| 完整流程合同 | [Java/Spring Workflow](../../workflows/java-spring-development.md) |
| 原始请求与确认 | [request](request.md)、[requirements](requirements.md)，A1–A7 |
| 方案与保持 | [design](design.md)、[behavior-mapping](behavior-mapping.md) |
| 代码与真实变化 | [app工程](app/pom.xml)、[初始v1服务](fixtures/TagService-v1.java)、[最终v2服务](app/src/main/java/example/workflow/TagService.java)、[diff](change.diff) |
| 验证与恢复 | [13项测试](app/src/test/java/example/workflow/TagWorkflowTest.java)、[真实回执](evidence/runtime.json)、[诊断](diagnosis.md) |
| 审查 | [代码](reviews/code.md)、[语义](reviews/semantic.md)、[原则](reviews/principles.md)、[真实分离复核](reviews/independent.md) |
| 文档、接续与交付 | [文档审验](reviews/document.md)、[阶段接续](trace.md)、[交付](delivery.md)、[结果](result.md) |

case.json声明阶段与产物，artifact-manifest固定案例全部文件身份；运行回执另固定编译源，不靠时间戳或文件存在证明执行。工具和依赖的公开来源见sources.json。

## 重跑

需要POSIX系统、Python3.9+、本地JDK17+和Maven3.6.3+，并可下载公开Maven Central依赖。在仓库根运行：

```sh
python3 examples/workflow-bookmark-tags/run.py
```

可显式选本机工具目录：`--java-home <jdk-home> --maven-home <maven-home>`。每个Maven阶段默认300秒；`--timeout`可给正整数，超时终止进程组并失败，不自动重试。可用`--output <案例目录之外的文件>`保存脱离机器路径的JSON摘要，案例本身保持不可变。

运行器先核所有案例SHA，再在系统临时目录分别编译v1/v2，使用同一13测试。v1必须只有blankItemRejectsWholeRequest和nullItemRejectsWholeRequest失败，v2必须13项全满足，无error/skip且精确进程状态匹配；编译失败、未执行用例、异常终止均不能冒充预期红灯。

不读取用户Maven配置/mavenrc，不继承JVM/Maven注入参数；settings、global-settings和localRepository隔离且镜像只指向公开Central。只下载公开依赖，不上传源代码；工具、缓存和target不进案例或Git。网络/环境缺失明确失败或NOT_RUN，不声称完全离线可跑。

## 使用边界

X-Demo-Actor是虚构身份输入，不是生产鉴权。Map与synchronized只说明本进程行为；没有数据库、消息、跨实例一致性或压测。测试加载真实Spring装配和MockMvc链路但不启动监听或部署。旧10个角色教材的历史NOT_RUN状态不因本例实跑而被改写。

返回：[案例目录](../README.md)。
