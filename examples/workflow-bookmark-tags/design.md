# 实现者设计与范围

新建单体教学模块：DemoApplication → TagController → TagService。Service的synchronized方法在本进程内保护版本检查、内容比较、写入与审计；不宣称数据库/跨实例事务。数据存于Map，Bookmark不可变且复制tags。

版本v1刻意将无效标签filter掉，作为可复现的初始错误候选；不是复用真实事故。v2改为校验每个元素，先构造完整规范化集合，再一次性更新。故障原件在fixtures/TagService-v1.java，最终代码在app，二者共享其余工程与同一套测试。

选择最小改点normalize：保留get→owner→version→normalize→无变更→写入→审计。没有新增第二套权限/版本规则；单一入口无其他展示/预检计算消费者，因此不引入公共微服务或额外层。

示例使用Spring Boot3.5.16、Java17、Maven。版本来自公开官方文档和Central元数据；不声称仓库所有项目必须采用或这是全局最新。构建仅下载公开依赖，不把依赖二进制/工具包纳入本库。

临时运行器使用独立settings/global-settings/localRepository、禁用mavenrc及JVM/Maven注入参数，构建和报告都在系统临时目录。默认每个Maven阶段300秒，到限终止进程组；不自动重试、不改系统安装和配置。

部署不在本例；X-Demo-Actor只是合成身份输入，接入真实工程需从可信认证上下文取得actor。server配置限制loopback，实跑测试使用MOCK而不启动监听。
