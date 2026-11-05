**目的**：实际运行虚构缓存反例，展示如何反驳初始判断并核挑战报告结构与候选身份。

**适用于**：本地 Python 3.9+、只读离线演练；分析由作者编写，不是模型独立审查或生产根因验收。

# 反证案例：旧读取是否表示写入丢失

原判断：“写后读到旧值，所以 store 丢失更新。”[行为合同](requirements.md)要求同实例顺序写后读取得新值。[虚构程序](cache_demo.py)刻意遗漏缓存失效；不修它来掩盖待诊断行为。

由[结论复核者](../../../agents/conclusion-reviewer.md)按[Workflow](../../conclusion-challenge.md)采用本案例。在仓库根运行：

```sh
python3 -B workflows/examples/conclusion-challenge/run.py
python3 -B -m unittest discover -s tests -p test_conclusion_challenge.py -v
```

运行器真正执行本地程序：初始 version-one；写后底层 store 为 version-two，但缓存读取为 version-one；清除缓存后读取为 version-two。因此“底层没保留写入”在本次运行被反例推翻；不能由此声称生产没有数据损失。没有外部请求，也没有修改仓库文件。

## 报告与判定边界

[review.json](review.json)为作者基于本地观察填写的三种解释、三项证据、九格矩阵、一次主动反证和两项决定性证据移除分析。运行器把本次观察与报告原观察逐字核对，再按固定名称、顺序与 NUL 分隔拼接 requirements.md 和 cache_demo.py 的原字节，计算复合 SHA-256，向工具传入独立的当前候选摘要。修改合同或程序必须新建/复核报告；不能把报告中的摘要反抄为当前摘要。

最小 JSON 合同由工具显式校验，报告直接展示完整格式：

| 字段 | 必需内容 |
| --- | --- |
| candidate_sha256 / scope / claim / preferred / conclusion | 当前摘要、适用范围、原判断、最初首选解释ID与限定结论 |
| hypotheses | 唯一 id 与 explanation；至少有真实竞争解释，重复文字拒绝 |
| evidence | 唯一 id、source_group、locator、observation、limits、critical 布尔值；同源观察保同组 |
| matrix | 每项 evidence×hypothesis 恰好一次，effect 为 support/oppose/neutral/strong_oppose，加 rationale |
| probes | 唯一 id、hypothesis、counterexample、state、evidence ID列表、result；首选须有反证尝试，DONE 必须有证据引用，NOT_RUN/UNAVAILABLE 不带结果证据 |
| sensitivity | 每项 critical 证据恰好一个 without、effect(changed/unchanged/unknown)、rationale |

工具返回 STRUCTURE_VALID，semantic_acceptance 与 action_authorization 均为 NOT_ASSESSED；未执行的反证保 pending_checks。理由和来源组都是声明，工具无法证明其真实性、独立性、因果或结论强度，也不以数量投票。报告文字虽说了结论，仍须责任者审阅其内容。

真实运行只覆盖内存、单线程、单实例、顺序调用；没有 Java/Spring、并发、持久化、真实服务、自动取证、新模型或专业分离审验。候选摘要绑定输入字节，不证明真实来源或权限；报告自身与工具的版本由交付候选固定。

返回：[案例目录](../README.md)。
