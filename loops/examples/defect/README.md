# 虚构缺陷的整体交付

本例实际运行[整体目标控制器](../../../tools/defect_loop.py)和[发现账本原语](../../../tools/finding_ledger.py)，输入为独立构造的本地 JSON，不调用模型、业务接口、Java 构建或部署。

```sh
python3 -B loops/examples/defect/run.py
```

示例先为原缺陷建立发现，绑定模拟失败、修复和三个分离审核上下文的回执，执行 REPAIRED → CLOSED。这些上下文只是控制测试数据，不是真实子 Agent 审查；制品 SHA 对应实际 fixture 字节，测试数字与行为结果均为模拟记录。

| 场景 | 输入 | 实际控制结果 |
| --- | --- | --- |
| tests_only | 模拟测试已通过，代码发现已有关闭证据，但业务行为与交接缺证 | PARTIAL，仍列 behavior/handoff |
| complete | 首轮只有测试，下一轮补业务行为与交接；保留原测试回执和发现历史 | 第二轮 COMPLETE |
| unknown_effect | 三类验收都 PASS，但原 demo-effect 受理结果未知 | HOLD，仅执行一轮，不重放操作 |

候选来自前后两个候选文件的真实 SHA；需求身份来自原三类验收，规则身份来自当前控制器字节。时钟 1000–1025 为虚构控制时间。`evidence.json` 是模拟证据包，不能当作真实测试、业务状态或外部审核证明。

[证据包](evidence.json) · [方法](../../defect-convergence.md) · [Loops](../../README.md)
