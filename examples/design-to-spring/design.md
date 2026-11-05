**目的**：将阅读清单需求转为同候选的 Spring 接口、状态边界、模块责任与可执行验收。

**适用于**：本案例单 JVM 单清单虚构工程，需求以[requirements](requirements.md)为准；不扩展到分布式锁或持久化事务。

# 设计 v1

控制器负责 JSON 映射、请求 Header 和 HTTP 路由；服务持有顺序确定的内存清单、当前版本、所有者及不可变记录快照。响应不暴露内部可变 Map，记录字段为 id/title/archived。

`archive(listId, actor, request)` 在服务同一 synchronized 方法内先核清单存在与所有者，再核请求、版本、非空 ids、每项非空白和存在性。用 LinkedHashSet 去重并完成全部校验，随后才计算有无改变和提交。任何异常均发生在首次状态修改前；有效改变的版本加1，全已归档不变。GET 也在同一监视器内产生快照。

预期异常用 ResponseStatusException 映射400/403/404/409；框架缺 Header、无法解析 JSON 等由 Spring 处理，不声称业务所有者检查早于反序列化。没有真实授权、存储或网络。

模块：service 独占服务/记录文件（R1/R3/R4/R5），web 独占控制器与 Spring 入口（R2），acceptance 独占 pom 和测试（支撑验证，无单独业务需求）。web/acceptance 依赖 service，acceptance 同时依赖 web。R3–R5 不拆到不同状态写者。

验收包含 Spring 真实装配/MockMvc、有序快照保持、非法尾项不得部分写入、null/空输入、去重、stale no-op、真正并发两写者、调用方集合不变。构建复制到仓库外临时目录，使用独立 Maven 用户/全局设置和显式仓库，不继承私服/插件配置；回执列实际测试名称、候选摘要、退出码、未验边界。

返回：[案例](README.md)。
