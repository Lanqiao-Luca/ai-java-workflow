# 实现者的一条完整链路

[书签标题规范化案例](../../examples/bookmark-title/README.md)是本能力的完整演示，包含已填写输入、Agent 决策、Skill/Standards 消费结果、变更前后 Java 源码、验收用例和交付记录。

它演示纯 Java 服务层的局部变更，可作为 Spring 业务层的独立单元；没有 Spring 依赖或容器装配，不声称 Spring 运行通过。所有对象、数据与规则均为案例独立构造。

按案例入口顺序阅读即可；运行需要本地 JDK 17+。当前真实结果见[验证与交接](../../examples/bookmark-title/result.md)，不能用文档或测试文件存在替代实跑。

返回：[代码实现 Skill](SKILL.md)。
