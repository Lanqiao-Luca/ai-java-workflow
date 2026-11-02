candidate_id: 2986559d3612bcca8fa0d4c63bd6c1c70890856c1abe10f71d1773dc73dededf

# 公开实现说明

本说明由发布整理职责根据已完成的原生实现报告和最终代码独立编写，绑定首行最终候选身份。原始报告包含本机执行坐标，留在私有审计中；本文件不是原生报告的原始字节，也不把后续测试结果冒称作者阶段已执行。

## 问题、条件与输入输出

适用于本例确认的标签规范化需求。输入为[任务](task.md)、[确认需求](requirements.md)、[POM](app/pom.xml)及固定合同测试；初始seed没有生产Java。原生实现者生成三个生产类、七项作者测试和实现说明，不修改固定验收、POM或测试资源。

## 实现步骤与保持项

1. [DemoApplication](app/src/main/java/example/nativeflow/DemoApplication.java)提供Spring测试配置；[LabelController](app/src/main/java/example/nativeflow/LabelController.java)通过构造注入调用唯一服务，POST成功返回labels，服务拒绝映射HTTP400。
2. [LabelService](app/src/main/java/example/nativeflow/LabelService.java)依次trim、ROOT小写、检查最终UTF-16长度，用局部LinkedHashSet保留首次顺序并在去重后检查四项上限；完整校验成功后返回独立列表。
3. 服务只读取调用者列表，所有中间状态在单次调用内；拒绝不返回部分结果，不新增数据库、审计、鉴权或其他业务假设。错误体与异常类型属于实现选择，不扩成新的外部契约。
4. [作者测试](app/src/test/java/example/nativeflow/ImplementationTest.java)补充精确trim、Unicode空白、补充字符、大小写扩长、顺序及失败保持等边界。固定验收保持独立来源。

## 职责、方法与验收

实现者消费[代码实现Skill](../../../skills/code-implementation/SKILL.md)、[Java/Spring检查](../../../skills/java-spring-check/SKILL.md)及[工作区隔离方法](../../../skills/workspace-isolation/SKILL.md)，据实际基线选择最小实现和保持映射。资源管理由宿主负责；作者没有自行创建或发布Git提交。

作者阶段只做静态阅读、文件和散列自查，未运行编译、JUnit、MockMvc或打包。后续独立验证及宿主复验的25项通过属于[验证阶段](verification.md)与[宿主回执](validation.json)，不能回写成作者阶段的运行事实。

## 异常与停止

需求未知或写集冲突交回任务负责人；运行失败交验证/诊断，不能删除固定测试造绿灯。代码或POM变化使相关验证和审查失效，需要定向复验。未启动服务、连接数据库或部署；配置类不代表可执行Boot JAR。公开提交由获授权的专门职责执行。
