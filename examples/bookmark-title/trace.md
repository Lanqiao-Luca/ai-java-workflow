# 已填写的 Agent → Skill → Standards 消费记录

这是本次作者对虚构案例的实际分析与文件构造记录；不是伪造的独立 Agent 调用日志。需求和输入是独立设计的演示条件，不是外部业务方的真实批准。

## 1. Agent 接收与选择

实现者接收[任务](task.json)：本次变化是标题规范化及空白拒绝，保持条件已决；业务改动写集只含候选服务和测试。选代码实现 Skill 做基线/保持/差异/自查，选 Java/Spring 检查 Skill 核语言环境。没有Bean、事务配置或外部依赖变化，Spring装配不适用；不为案例创建额外角色或调度层。

## 2. Skill 消费规范后交回什么

| 消费规范 | 本案例输入与判断 | 实际输出 |
| --- | --- | --- |
| 实现基线 | 读变更前服务；当前是合成基线，不伪造提交号 | 基线按文件SHA固定，原件保持独立，修改限定候选服务 |
| 旧行为保留 | 追`rename → get → owner → version → title → write → audit` | 下表列保持项；沿用原方法、锁、记录与写入，不新增第二套入口 |
| 共享规则 | 只有一个标题写入入口，没有展示/预检消费者 | 不适用；不为一次trim新增公共框架或服务 |
| 风险驱动验证 | A1–A7映射到正常、拒绝、无写入及旧行为检查 | 独立编写12项契约用例，前后服务使用同一用例 |
| Java/Spring检查 | 源码用Java record；本地JDK探测失败 | 用JDK17作为示例运行前提；当前Java未验证，不启动Spring或连接数据库 |

## 3. 保持与变化映射

| 行为 | 处理 | 源码落点与检查 |
| --- | --- | --- |
| 不存在引用拒绝 | 保持 | `get`；missing |
| 只有所有者可改 | 保持 | `owner`比较；owner、owner-before-title |
| 权限先于标题校验 | 保持 | 校验顺序不变；owner-before-title |
| 版本冲突拒绝 | 保持 | `expectedVersion`；stale、stale-after-success |
| null标题拒绝 | 保持 | 原null检查；null |
| 标题首尾空白 | 明确变更 | 校验后`trim`，保存规范化值；trim |
| 空/空白标题 | 明确变更 | 规范化后`isEmpty`拒绝；blank、empty |
| 同标题不写入 | 保持并适配新语义 | 比较规范化结果；plain-noop、normalized-noop |
| owner、tags、savedSequence | 保持 | 原字段复制；preserved-fields-and-audit |
| 版本、审计 | 保持 | 真变更各增一次；成功/无变更/拒绝场景检查 |
| 失败不写入 | 保持 | 所有拒绝检查都比较完整对象及审计计数 |

这些是代码与用例映射，尚非Java测试通过证据。具体运行状态单列在结果记录中。

## 4. 实施取舍

继续复用`rename`。在所有者和版本校验之后保留原null检查，再规范化及判空，避免改变错误优先级。规范化值同时用于无变更判断和写入，防止预检与执行使用不同含义。没有改锁、存储、审计或字段模型；差异可直接核对。

## 5. 验收映射与交接

| 验收 | 用例ID |
| --- | --- |
| A1 | trim |
| A2 | blank、empty、null |
| A3 | owner、owner-before-title |
| A4 | stale、stale-after-success |
| A5 | preserved-fields-and-audit及各拒绝用例 |
| A6 | normalized-noop、plain-noop |
| A7 | missing |

无新增未决业务语义；真实缺项为JDK环境和实际Java运行。实现者交代码候选、差异和用例；下一接收者取得JDK后运行并核实际断言，再按当前任务选择审查。作者不自签功能验收、Spring通过或独立业务审核。

返回：[案例入口](README.md)。
