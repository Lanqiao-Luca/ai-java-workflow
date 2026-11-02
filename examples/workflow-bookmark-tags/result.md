# 当前结果与真实交接

最终v2候选ID：`1d29c762b9b091a2416d16855b410d78a6312b6a9f43fbfbd4038f4054f9de71`。共享源包ID：`1d530e1f1dc472948abe1e87c462620a1121e6abe0455aab222b2351a7e6c468`。源码、测试、运行器与v1的逐文件SHA在[evidence/runtime.json](evidence/runtime.json)中，案例全文件身份另由artifact-manifest固定。

| 层次 | 实际结果 | 支持的结论 |
| --- | --- | --- |
| v1 Spring测试 | 进程退出1，13用例，恰好2失败，error/skip均0 | 只接受blankItemRejectsWholeRequest/nullItemRejectsWholeRequest为预期红灯 |
| v2 Spring测试 | 进程退出0，13用例，fail/error/skip均0 | 当前候选真实Spring装配、JSON请求/错误映射及服务状态断言通过 |
| 分离上下文文档/代码审查 | 真实只读复核覆盖29文件，1项输出隐私发现已定向关闭 | 代码/语义/原则/文档审阅，不声称复核者独立实跑 |
| SQL/数据库 | 无此实现，不触发查询分支，不连接数据库 | 不是SQL或生产性能通过 |
| GitHub源码发布 | 当前授权后由交付专员执行并另记远程结果 | 不代业务部署、现场验收或10原生Agent运行 |

实测使用Temurin17.0.21+9、Maven3.9.11、Spring Boot3.5.16；工具仅在本任务work，依赖仅从公开Central下载。回执只保留版本/源码ID/用例和返回状态，不含工具路径、原始日志、用户设置或凭证。没有系统安装、私服、数据库或生产连接。

复现命令见[README](README.md)。每个Maven阶段预算300秒，到限终止进程组并失败；没有为红灯重置预算或无条件重试。v1→v2是有依据修复，不是将同一写入重放。

当前候选代码已验证，实际分离复核与必要处置已完成，可交付该演示源码与回执；生产认证/数据库/分布式并发/部署明确范围外。旧角色教材的历史NOT_RUN保留，不被此次新案例覆盖。
