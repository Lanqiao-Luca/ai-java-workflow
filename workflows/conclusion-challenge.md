**目的**：组织重要结论的候选冻结、取证、主动反证与限定交接，避免未经证实就实施修复。

**适用于**：已有技术判断需多阶段复核的单轮任务；重复补证沿当前实例与预算，不自动开启 Loop。

# 重要结论反证 Workflow

| 阶段 | 责任与产物 | 验收及失败返回 |
| --- | --- | --- |
| C00 冻结 | 当前协调者绑定原命题、候选、读集、预算和已有证据 | 缺前提只停依赖动作 |
| C10 核证据 | [证据采集者](../agents/evidence-collector.md)复用有效观察，按需补最小区分证据 | sample/complete、同源和未查分别说明；未知不重放 |
| C20 主动反证 | [结论复核者](../agents/conclusion-reviewer.md)建共同证据矩阵、反例检查和敏感性 | 缺证保留；新候选回首个失效项 |
| C30 核收与交回 | [诊断者](../agents/diagnostician.md)或原请求者核限定结论、残余和下一责任 | 结构自查、专业审查与实施许可分别表述 |

Brain 可选本 Workflow，阶段 Agent 经 Skill 使用原子与 Tools。按[报告空表](templates/conclusion-challenge.md)填实例；[本地案例](examples/conclusion-challenge/README.md)实际运行虚构缓存反例，推理部分为作者分析，没有独立模型审查或生产诊断。

返回：[Workflows](README.md)。
