**目的**：贯通虚构设计编制、专业发现、定向修订与模块规划，区分静态推演和真实结构执行。

**适用于**：学习 Agent→Skill→Standards/Tools 能力线的使用者；不代真实工程设计、分离审验或实施验收。

# 设计到模块：书签虚构案例

## 输入、方法与产物

本例所有需求、设计、模块及数据均独立构造。角色名称说明责任，不表示启动了模型或独立 Agent。

| 阶段 | 入口与实际材料 | 当前状态 |
| --- | --- | --- |
| 编制 | [方案作者](../../../agents/design-author.md)；[需求](requirements.md)与[初始设计](design-v1.md) | 作者构造的文档推演 |
| 专业发现 | [设计复核者](../../../agents/design-reviewer.md)；[发现记录](review.json) | 检出“边校验边写入”违反R3；没有真实分离上下文 |
| 修订 | [修订设计](design-v2.md) | 改为写入前完整校验、同边界提交；未执行代码验证 |
| 模块规划 | [模块规划者](../../../agents/module-planner.md)；[独立设计合同](contract.json)与[单一模块计划](plan.json) | 四模块、五需求、共享文件唯一写者；仅为实施准备 |
| 结构控制 | [离线程序](run.py) | 实际结果见[验证记录](result.md)，不签设计/实施通过 |

[技术方案 Workflow](../../technical-design.md)和[模块规划 Workflow](../../design-to-modules.md)组织责任与交接。实际消费的原子与工具均从相应 Agent 的 Skill 进入，Brain 不直接调用。

## 执行

责任 Agent 在确认本地示例授权后，从仓库根运行：

```sh
python3 -B workflows/examples/design-to-modules/run.py
python3 -B tools/module_plan.py --contract workflows/examples/design-to-modules/contract.json --plan workflows/examples/design-to-modules/plan.json
```

第一条实际读取本例设计/合同，核 SHA 绑定，并执行一个正例和四个负例。第二条只核显式传入的合同与计划声明；调用者必须独立核设计合同来源和实际设计SHA，不得从计划自造一个相同合同自证。

baseline_sha256 是本例虚构仓库快照指纹，不是本地 Git 提交；工具核声明身份一致，不访问真实仓库、调用模型、编译 Java、操作 Git 或启动 Graph。

## 边界与恢复

本例假设与当前实例均不能作为生产默认。合同支持精确文件写集与唯一写者，不支持通配符写集或同文件多模块串行补丁协议；需要那类模型时先扩展合同和验收，不能绕过工具拒绝。

设计或基线变化需新绑定并复核相交模块。专业接受、用户实施许可、真实代码和测试全部保持 NOT_RUN/未取得，STRUCTURE_VALID 只证明内部声明一致。

返回：[执行文件目录](../README.md)。
