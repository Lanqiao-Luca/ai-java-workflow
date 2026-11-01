# ai-java-workflow

把一个 Java/Spring 需求交给 AI，按可复核的步骤形成代码候选与验证证据。

面向 Java/Spring 业务开发的 AI 研发工作流。当前聚焦 **Agent → Skill → Standards** 三层：Agent 对结果负责，Skill 适配当前任务，Standards 保存共用方法。提供可阅读的方法、空表和独立虚构代码案例，由使用者当前的 AI 助手与本地工具执行。

## 仓库里有什么

**15份规范 · 11项技能 · 10项角色职责 · 1条完整实现链路 · 3份空表**。

| 你想做什么 | 从这里进入 | 能拿到什么 |
| --- | --- | --- |
| 先看一个Agent怎样做事 | [实现者Agent](agents/implementer.md)、[完整案例](examples/bookmark-title/README.md) | 输入、决策、规范消费、Java前后差异、用例与交接 |
| 把需求交给AI开发 | [需求澄清](skills/requirement-clarification/SKILL.md)、[代码实现](skills/code-implementation/SKILL.md) | 可实施范围、保持项、最小改点和真实验证要求 |
| 审代码或排查失败 | [代码审查](skills/code-review/SKILL.md)、[证据诊断](skills/evidence-diagnosis/SKILL.md) | 可复核发现、反例、限定结论和恢复点 |
| 查方法与职责 | [规范目录](standards/README.md)、[技能目录](skills/README.md)、[角色目录](agents/README.md) | 当前问题需要的规范、输入输出和责任边界 |
| 直接记录本次任务 | [任务表](skills/resources/task.md)、[行为映射](skills/resources/behavior.md)、[验证与审查表](skills/resources/review.md) | 可复用的空表，不要求每次重建台账 |

仓库区分**方法文档、辅助脚本和代码示例**。Skill/Agent文档没有自动注册到平台，也不提供模型、数据库或外部服务客户端；不要求为简单任务启用所有角色。

## 先看一条完整链路：书签标题规范化

目标：允许书签所有者修改标题，对标题首尾空白做规范化，拒绝空结果，同时保留权限、版本冲突、标签、收藏序号和审计行为。

```text
任务与验收 → 实现者Agent → 代码实现Skill → 共用Standards
                                      ↓
                           最小Java差异 → 作者自查 → 交接
```

| 阅读顺序 | 实际内容 |
| --- | --- |
| [案例入口](examples/bookmark-title/README.md)与[任务](examples/bookmark-title/task.json) | 已决目标、写集、禁止动作、A1–A7验收 |
| [消费与行为映射](examples/bookmark-title/trace.md) | 为什么复用旧入口，哪些改变、哪些保持，如何选择用例 |
| [变更前](examples/bookmark-title/before/BookmarkService.java)、[变更后](examples/bookmark-title/after/BookmarkService.java)和[diff](examples/bookmark-title/change.diff) | 原有校验后引入规范化，复用写入与审计 |
| [12项契约检查](examples/bookmark-title/tests/BookmarkServiceTest.java) | 正常、拒绝、无变更及失败不写入的断言 |
| [验证与交接](examples/bookmark-title/result.md) | 已做检查、未验事项、同一候选的接续命令 |

所有对象、数据和规则独立虚构。示例是纯Java内存服务，可作为Spring业务层的独立单元；没有Spring容器、HTTP、数据库或真实认证。**Java用例尚未实跑**：整理环境没有可用JDK，运行入口已真实返回NOT_RUN；测试文件存在不代表12项通过。

## 复制给AI：从案例开始

用能读取本地文件的AI编程助手打开整个仓库，输入：

> 按 agents/implementer.md 承担实现者职责。先读 skills/code-implementation/example.md 和 examples/bookmark-title/task.json，再核变更前源码。通过代码实现Skill消费相关Standards，解释旧行为、最小改点和验收映射，对照候选与用例给出自查、待验项及交接。我现在只让你审阅这个虚构案例，不修改全局配置、不连接服务、不提交或发布。

用于自己的工程时，可以这样开场：

> 按实现者Agent处理我的Java/Spring需求。先确认实际工程、需求验收、允许写集和已有改动，再选择Skill读取必要规范。优先复用旧能力，列出保持行为与最小改点；只在已授权范围修改，记录真实测试和未验证项，交可审核候选。

请求需要结合你的实际工程与当前授权；方法不替业务方确认未知语义，也不保证平台自动发现或派发Agent。

## 本地检查与案例运行

文档检查需要Python 3.9+，不下载依赖、不连接网络：

```sh
python3 scripts/check.py
```

检查公开清单、相对引用、三层合同、案例源码SHA与实际diff。静态通过不代表公司敏感性、公开权利或业务运行全部得到证明。

本地有JDK 17+时，再运行：

```sh
python3 examples/bookmark-title/run.py
```

运行器先核源码身份，再在临时目录分别编译基线与候选。预期基线暴露4个指定差距、候选满足12项；它核精确退出码、完整且不重复的用例集合及汇总行，拒绝异常终止误判。缺JDK退出2并打印NOT_RUN，不会安装工具。

## 当前覆盖与边界

| 内容 | 已交付与验证范围 |
| --- | --- |
| 三层方法与空表 | 可阅读、手工采用；引用与结构检查通过 |
| 一个实现者Agent的完整案例 | 输入、规范消费、代码、diff、测试与交接齐备；文档/代码审阅完成 |
| Python辅助脚本 | 清单检查实跑通过；运行器8项模拟进程分支检查通过 |
| Java契约用例 | 已编写，尚未编译运行；模拟分支检查不代替Java测试 |
| Spring真实工程、数据库和模型接入 | 由使用者在自己的工程验证，仓库没有接通这些服务 |
| 平台Skill/Agent注册与自动调度 | 未提供自动安装、Workflow/Graph/Loop执行器或后台任务 |

方法不固定所有项目的JDK、Spring或数据库版本，按真实工程事实核适用性。源码身份变化后应刷新受影响证据；作者自查、独立审阅、真实运行和最终采用分别声明。

## 修改与扩展

新增方法先确定适用条件、输入输出、步骤、角色、验收和异常停止；已有方法保持单源。新增案例使用独立虚构数据，补保持映射、真实用例及未验范围。改动同步更新`public-manifest.json`并运行检查；不要把真实凭证、内部服务坐标、公司业务资料或原始会话带入仓库。

[协作约定](AGENTS.md) · [内容与许可边界](RIGHTS.md)

仓库中重新编写的文档、脚本和虚构示例采用 [MIT许可证](LICENSE)。该许可不扩展到使用者自己的公司代码、第三方资料或未纳入本仓库的素材。
