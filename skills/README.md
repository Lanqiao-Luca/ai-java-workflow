# Skills

本目录为方法指南，未注册为任何平台原生能力。角色负责选择，Skill 组合平级的 Standards 与 [Tools](../tools/README.md)，实际适配输入并交回结果。Brain 不直接调用 Skill 或基础资源。

- [执行计划与工具适配](task-execution/SKILL.md)：为已选 Workflow、Loop、Graph 绑定计划与实际执行接口。

- [需求澄清](requirement-clarification/SKILL.md)
- [代码实现](code-implementation/SKILL.md)
- [工作区隔离](workspace-isolation/SKILL.md)：准备/核验/回收实例资源，后端缺失即拒绝。
- [Java/Spring 检查](java-spring-check/SKILL.md)
- [测试验证](verification/SKILL.md)
- [代码审查与复核](code-review/SKILL.md)
- [需求语义核验](semantic-review/SKILL.md)
- [原则审查](principle-review/SKILL.md)
- [证据诊断](evidence-diagnosis/SKILL.md)
- [查询审查](sql-review/SKILL.md)
- [状态与交付规划](delivery-planning/SKILL.md)
- [文档审验](document-review/SKILL.md)

配套空表：[任务与验收](resources/task.md)、[行为保留](resources/behavior.md)、[审查记录](resources/review.md)。独立虚构演练：[书签标题修改](code-implementation/example.md)。完整角色案例见[十条案例目录](../examples/README.md)。

- [Java构建隔离](java-build-isolation/SKILL.md)：显式可信Maven/Gradle模式，公开缓存、子JVM与进程停止验收。

- [Docker构建隔离](docker-build-isolation/SKILL.md)：本地Engine/镜像、白名单输入输出、实际容器限制及停止验收。
