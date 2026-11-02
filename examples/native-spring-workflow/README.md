# 原生Agent完整Spring研发案例

一个独立虚构的标签规范化接口，由真实原生上下文依次澄清需求、生成Java与作者测试、独立验证、并行审查和形成交付报告。[Graph](../../graphs/native-java-spring.md)和[Workflow](../../workflows/native-java-spring.md)负责顺序、写集与同候选门禁，父调度器不代写业务代码。

## 输入与产物来源

- `seed/`只有确认需求、POM与公开测试SPI配置，没有生产Java。固定[13项合同测试](acceptance/LabelContractTest.java)由宿主预先独立编写，不能称为模型生成。
- 原生实现者生成三个生产类和自己的JUnit测试；独立验证者再编写自己的边界测试。最终来源与实际数量以结果和回执为准。
- 每个Workflow有独立worktree和实例内原生注册，两项审查使用分离上下文和同一个冻结候选。真实原生spawn/完成记录留在仓库外，公开仅有白名单摘要与身份哈希。
- 普通Markdown的方法引用可逆迁移到仓库单源，验证链接改指同候选宿主回执。两份原报告含本机坐标，实现说明与代码审查已由发布整理职责独立编写公开摘要，明示不是原生原始字节；原始/公开SHA分别核对，原件及来源映射留私有。Java、POM、测试和验证JSON原字节保留，不复制catalog或私人注册配置。

## 显式重跑

需要POSIX、Git、Python3.9+、可用的Codex CLI与本机正常登录、JDK17及Maven。运行会调用真实模型并下载公开依赖；先确认当前输入是本例公开虚构材料。使用者若需要代理，应为当前进程显式选择正常代理环境，不改全局配置或复用公司凭证。

```sh
python3 -B examples/native-spring-workflow/run.py \
  --public-synthetic-input \
  --run-root <仓库外全新私有目录> \
  --java-home <公开JDK17目录> \
  --maven-home <公开Maven目录>
```

入口只读取seed和固定验收，不把公开最终Java当seed。公开版本已经能看到上次生成的实现，后续模型行为可能不同；重跑仍须重新核实际文件、测试和审查，不能沿用本次绿灯。运行结果不会自动写回公开案例或推送GitHub；新结果需另行审阅与授权交付。

## 环境和失败边界

宿主先用空user/global settings及新缓存下载公开Central依赖并验证初始候选；原生验证者和最终宿主复验均离线。构建子进程的环境完全重建，不继承Spring、数据库、云、API凭证、代理或父PATH。日志、缓存、target、Git管理目录、原始会话及本机工具路径不上传。

本例显式选择Mockito的subclass MockMaker与reflection MemberAccessor，避免原生工具沙箱内JVM自附加。本例未使用或验证final/static mocking，其他项目不能直接照搬SPI；没有用mock替代实际Spring Bean。初次实跑因默认inline自附加失败而停止，业务断言未运行；记录该失败，不削弱断言或把宿主结果挪作沙箱通过。

[真实结果](result.md)：六个原生节点完成，最终25项离线Spring测试通过；详见[执行追踪](trace.md)、[回执](evidence/runtime.json)与[交付报告](final/delivery.md)。仅核Spring装配与MockMvc，不启动监听、不接数据库或生产身份、不部署。`DemoApplication`提供测试配置，未宣称可执行Boot JAR或服务启动。当前只在macOS arm64实跑；Linux原生链、任意现有工程和恶意多租户完整隔离未验。

返回：[案例目录](../README.md)。
