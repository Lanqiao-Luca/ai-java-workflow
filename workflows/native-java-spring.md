# 原生Agent研发Workflow

本合同将[需求负责人](../agents/requirement-analyst.md)、[实现者](../agents/implementer.md)、[验证者](../agents/verifier.md)、[代码审查者](../agents/code-reviewer.md)、[原则审查者](../agents/principle-reviewer.md)和[交付规划者](../agents/delivery-planner.md)接成真实原生上下文；代码审查节点同时消费语义与文档审查职责。每个角色经自身Skill消费Standards，父调度器不代做业务任务。

## 阶段

| 阶段 | 原生配置 | 输出和门禁 |
| --- | --- | --- |
| 需求 | [定义](native-requirements.json) | 确认范围、语义和验收；不替未知业务决定 |
| 实现 | [定义](native-implementation.json) | 根据确认契约生成实际Java与作者测试；固定验收/POM不允许修改 |
| 验证 | [定义](native-verification.json) | 独立补边界测试，实际运行冻结工具；宿主再次实跑并绑定完整源码候选 |
| 代码/语义/文档审查 | [定义](native-code-review.json) | 读取冻结候选及真实验证，输出具体发现；不能修实现 |
| 原则审查 | [定义](native-principle-review.json) | 与代码审查并行，但拥有独立worktree和上下文，核范围、来源和完成声明 |
| 交付 | [定义](native-delivery.json) | 两项审查通过后形成同候选交付说明；不自动获得远程提交或部署权限 |

## 实例与失败

每个Workflow使用一个新的worktree和实例内原生角色配置。宿主检查真实文件变化必须属于声明写集；模型的JSON完成回复不能代替文件、编译、测试或冻结身份校验。运行配置、方法目录与工具入口不得被角色修改；日志、缓存、认证、Git管理目录和原始会话不进入交付。

验证、审查及交付的Markdown产物首行必须是`candidate_id: <当前候选摘要>`。宿主同时核文档声明、实际源码与验收回执；审查/交付派工前和提升前都重核，不能用正确标题掩盖旧验证证据。

失败阻断后代，保留首个断点、候选和私有证据，交回对应责任。当前参考实现不自动重试模型、不自动整改或续跑未知动作；修复后应由任务负责人核有效前缀和新的允许范围，再显式继续。不能声称已经实现无人值守的自动修复。

此组声明针对独立虚构标签API，不能不经准入改成任意公司工程。原生模型调用需要正常登录与网络；Spring构建的公开依赖预热和离线验收分别记录。方法合同、原生执行、系统沙箱、真实构建与远程交付各自说明。

完整研发方法仍见[原Workflow](java-spring-development.md)，执行顺序由[原生Graph](../graphs/native-java-spring.md)控制。提交/推送需当前明确授权及使用者项目专用原生提交角色，业务Agent不直接操作真实仓库Git。

[完整Spring实跑案例](../examples/native-spring-workflow/README.md)保留固定验收、原生生成的Java/作者测试、独立验证与公开交付报告；发布摘要与原生原件的来源分别声明，不上传原始会话或本机坐标。

返回：[Workflows](README.md)。
