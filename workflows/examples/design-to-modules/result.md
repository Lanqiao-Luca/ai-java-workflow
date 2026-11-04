**目的**：记录本例实际离线结构检查与未执行范围，不把静态设计推演当实施验收。

**适用于**：核对本轮公开能力线验证的使用者；仅覆盖合成文件与确定性程序。

# 当前验证范围

已在当前作者上下文实际运行 `python3 -B workflows/examples/design-to-modules/run.py`：正例返回 STRUCTURE_VALID（四模块、五需求、execution=not_started）；漏需求、写集冲突、依赖环、旧设计绑定四类负例均实际拒绝。工具 CLI 的成功/拒绝退出码及其他边界由本轮便携回归另行核验，不把预期结果当真实设计接受。

专业发现与修订由作者构造，不是独立 Agent 审验；Java实现、真实构建、生产接入、发布与部署均未执行。读取公开旧案例的历史通过不改变本例状态。

[模块规划者](../../../agents/module-planner.md)只交准备包，具体单轮沿[模块规划 Workflow](../../design-to-modules.md)。

返回：[案例入口](README.md)。
