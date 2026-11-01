# Agent逐项发布结果

已有实现者1例，加本轮其他9例，共10条角色案例。

本记录在九个逐Agent主提交远程核验后填写。各角色原有文档已公开，本轮补齐责任合同和独立案例；没有创建多个仓库。当前记录不填写自身提交SHA，避免自哈希循环。

| 顺序 | Agent与案例 | 已核主提交 | 实际验证与未验边界 |
| --- | --- | --- | --- |
| 1 | [需求负责人](../agents/requirement-analyst.md) · [案例](../examples/clarify-bookmark-tags/README.md) | [7db4353](https://github.com/Lanqiao-Luca/ai-java-workflow/commit/7db43535440a9f752327a8e65a8cbe18db7bf4a0) | 清单/引用/合同/案例身份通过；文档或静态分析不代业务运行 |
| 2 | [验证者](../agents/verifier.md) · [案例](../examples/verify-bookmark-title/README.md) | [fdeb4a2](https://github.com/Lanqiao-Luca/ai-java-workflow/commit/fdeb4a288f88d636c8ba7193541f0f96b8748ef3) | 清单/引用/合同/案例身份通过；文档或静态分析不代业务运行 |
| 3 | [代码审查者](../agents/code-reviewer.md) · [案例](../examples/review-bookmark-rename/README.md) | [03e76da](https://github.com/Lanqiao-Luca/ai-java-workflow/commit/03e76da60e66bbbad11412b4ae84341e1357a767) | 清单/引用/合同/案例身份通过；文档或静态分析不代业务运行 |
| 4 | [语义审查者](../agents/semantic-reviewer.md) · [案例](../examples/compare-title-semantics/README.md) | [7b2316d](https://github.com/Lanqiao-Luca/ai-java-workflow/commit/7b2316d045affd4240276f34cdec195d65bfc46d) | 清单/引用/合同/案例身份通过；文档或静态分析不代业务运行 |
| 5 | [原则审查者](../agents/principle-reviewer.md) · [案例](../examples/review-scope-and-evidence/README.md) | [39f0caf](https://github.com/Lanqiao-Luca/ai-java-workflow/commit/39f0caf760a128b8acdfa8a564d75e040bcf9cf5) | 清单/引用/合同/案例身份通过；文档或静态分析不代业务运行 |
| 6 | [诊断者](../agents/diagnostician.md) · [案例](../examples/diagnose-version-conflict/README.md) | [43f2695](https://github.com/Lanqiao-Luca/ai-java-workflow/commit/43f2695ca3c51bfda81a5e5debd3681d325b23e8) | 清单/引用/合同/案例身份通过；文档或静态分析不代业务运行 |
| 7 | [查询审查者](../agents/query-reviewer.md) · [案例](../examples/review-cursor-pagination/README.md) | [166b23f](https://github.com/Lanqiao-Luca/ai-java-workflow/commit/166b23f35a0ada871b3f18fab2cc675efb8268f5) | 通用检查通过；SQLite内存实际回放before=[4]、after=[1,4]；无外部DB/MySQL性能结论 |
| 8 | [交付规划者](../agents/delivery-planner.md) · [案例](../examples/plan-evidence-gated-delivery/README.md) | [22f35eb](https://github.com/Lanqiao-Luca/ai-java-workflow/commit/22f35eb72e19abddbb3fe065e07745803422f7b2) | 清单/引用/合同/案例身份通过；文档或静态分析不代业务运行 |
| 9 | [文档审查者](../agents/document-reviewer.md) · [案例](../examples/review-draft-runbook/README.md) | [5a4d25f](https://github.com/Lanqiao-Luca/ai-java-workflow/commit/5a4d25fc2cd9d3806ffb3558d57c40487c455876) | 清单/引用/合同/案例身份通过；文档或静态分析不代业务运行 |

前置[计划与检查器提交](https://github.com/Lanqiao-Luca/ai-java-workflow/commit/5c9a1c4e1ed96e39fedf546d69d47f20712f7b84)先于所有新案例保存与发布。发布中发现验证者可选Java/Spring入口遗漏，以[687e609定向修正](https://github.com/Lanqiao-Luca/ai-java-workflow/commit/687e6090dd6e9b3022f0a6eaad30bb528745a570)补回；没有改写fdeb4a2或其他已推历史。

第7项同时允许具名local_sqlite_memory_only结构声明，要求replay.py/fixture.json存在并另行实际执行；不以字段存在代语义或执行通过。SQL结果中“数据库变更”已限定为“外部数据库变更”，进程内构造如实保留。

九包全部显式暂存、各自主提交、普通push并读取远程SHA及相交blob核验。新增内容仅来自公开仓库与独立虚构材料，没有读取或上传原私有框架/审计。逐文件内容与引用独立复核的两个集成发现（验证者入口、SQL声明兼容）已定向关闭；该复核不是外部公司权利审计或真实业务验收。

案例中保留的OPEN/缺证项是针对独立构造的植错输入或模拟未决所形成的教学审查结论，不代表所有案例业务已经修复；也不能将明确保留的教学问题自动改名为通过。

原实现者Java仍NOT_RUN，未安装JDK；没有Spring现场、平台原生Agent调用、Release、CI、后台流程或外部服务连接。计划中的模拟批准、日志和输入不代表实际操作授权。

[执行文档](agent-publication-plan.md) · [完整案例目录](../examples/README.md)
