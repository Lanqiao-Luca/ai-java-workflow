# 原生派工适配器

当前交付最小原生调用机制；完整业务阶段随后按[执行计划](native-agent-workflow-plan.md)接入。[实现](../tools/native_agents.py)与[离线协议测试](../tests/test_native_agents.py)分别保存运行机制和可复现的协议反例。

## 一次调用

调用`dispatch(cwd, role, task, run_dir, codex="codex", session_root=None, timeout=600)`。`cwd`必须是已获授权且确认可以发送给模型的公开/独立虚构工程；`role`必须已在原生Agent目录注册。`run_dir`为工程外全新私有目录，不能复用旧运行结果。

父会话只允许真实spawn、等待和读取原生Agent状态。子Agent使用全新上下文并消费自己的职责与方法，最终只返回`status`、`summary`、`outputs`的JSON；业务文件仍须由上层检查最终字节和必要功能验证，不能仅凭结构化回复报业务通过。

该版本适配实测Codex CLI原生collaboration协议。CLI普通JSON输出不完整展示spawn，因此根据本次`thread.started`的UUIDv7，仅定位对应日期内唯一同ID的本机rollout，核实际`spawn_agent`调用/成功输出与`list_agents`中的同子Agent完成状态。角色错误、父会话自行用工具、缺结果、非JSON结果和仅父会话宣称成功都拒绝。协议不兼容必须明确失败，不能降级为扮演角色。

可以显式运行[真实探测入口](../scripts/probe_native_agent.py)：`python3 -B scripts/probe_native_agent.py --run-root <仓库外全新私有目录>`。它只在新实例中注册探测角色，读取随机生成的虚构输入并核返回值，不改全局Agent/Skill注册、不提交代码；宿主项目信任登记是另需明确许可的平台副作用。需要当前Codex CLI、正常登录与可达模型服务；原生真实探测不属于离线测试。

实测：macOS arm64、Codex CLI 0.166.0-alpha.5.1完成最小环境版真实探测；15项离线协议/边界测试通过。两项独立复核发现已修复并有定向回归。[简化结果](native-agent-adapter-results.json)绑定实际适配器与探测入口字节，不含原始会话；Linux运行和完整Spring链路在本步未验。

## 隐私、权限与失败

需要使用者已有Codex本机登录和模型网络；不创建、复制或打印API key与登录状态。子进程只保留正常登录定位、工具路径、临时目录和显式代理等最小环境，不透传业务/数据库/云凭证或环境API key；正常认证由Codex既有登录机制处理。本项目不主动改写全局规则、Git身份、权限或系统代理，但实测Codex 0.166 CLI及App Server的thread/start会自动保存新目录项目信任。启动前必须取得该平台登记许可；若任务要求全局配置零写入，当前后端不兼容，不能调用或用其他角色绕过。临时登记完成后只能按确证归属还原本任务新增项，不得覆盖其他配置变化。凭证与原始会话禁止进入公开回执。

子任务使用CLI的workspace-write沙箱及非交互拒绝新增审批。它是可信公开工程的原生Agent执行适配器，不是旧Docker离线构建沙箱；不得声称对恶意Agent或所有可读私人目录形成完整隔离。不要把公司工程作为探测输入。

超时/日志越界终止本次CLI进程组、保留私有状态为UNKNOWN，不自动重试。原生远端子Agent与它启动的外部进程是否停止仍需宿主查明，不能因CLI退出释放未知占用或重复有副作用的动作。已开始的提交/推送更不能自动重放。

原始日志有界保存在`run_dir`和Codex自己的会话目录；公开项目仅纳入经审查的简化运行结果，不复制原始会话。此适配器本身不执行Git提交或推送；提交仍按使用者当前项目路由委派。

返回：[项目入口](../README.md)。
