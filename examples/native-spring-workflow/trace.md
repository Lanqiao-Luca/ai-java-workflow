# 原生执行追踪

同一成功实例的真实派工与门禁如下；原始会话和本机路径保留在仓库外。

| 节点 | 原生角色 | 当前状态 | 输入候选 | 输出候选 |
| --- | --- | --- | --- | --- |
| requirements | workflow_requirements | SUCCEEDED | `eeb7121dd78a` | `eeb7121dd78a` |
| implementation | workflow_implementation | SUCCEEDED | `eeb7121dd78a` | `e995a29d2626` |
| verification | workflow_verification | SUCCEEDED | `e995a29d2626` | `2986559d3612` |
| code_review | workflow_code_review | SUCCEEDED | `2986559d3612` | `2986559d3612` |
| principle_review | workflow_principle_review | SUCCEEDED | `2986559d3612` | `2986559d3612` |
| delivery | workflow_delivery | SUCCEEDED | `2986559d3612` | `2986559d3612` |

需求后实际生成Java和作者测试；验证者在新worktree新增独立测试并执行冻结离线runner，宿主再次实跑。两项审查从同一base开始，写集不相交，调用区间真实重叠；这证明Workflow作业并发，不宣称模型服务内部硬件调度同时执行。

最终候选：`2986559d3612bcca8fa0d4c63bd6c1c70890856c1abe10f71d1773dc73dededf`。全部审查/交付首行身份、实际源码与PASSED回执逐项匹配；父会话只派工，所有六节点有真实spawn和完成对。原生身份通过父会话哈希与子路径哈希联合区分。

公开Markdown方法引用按可逆规则迁移，验证链接改指同候选宿主回执；实现说明与代码审查因原件含本机坐标而由发布整理职责独立编写公开摘要。case声明原生/公开SHA，私有审计保留原件与来源映射，不能把摘要冒称原生原始字节。代码、POM、测试和验证JSON原字节保留。未把原始会话、缓存、认证、工具路径或Git历史带入。

[回执](evidence/runtime.json) · [需求](final/requirements.md) · [验证](final/verification.md) · [代码审查](final/code-review.md) · [原则审查](final/principle-review.md) · [交付](final/delivery.md)
