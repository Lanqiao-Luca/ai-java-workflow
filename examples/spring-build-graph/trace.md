# 需求到集成构建的链路

1. 需求：TitleApi trim并拒空白/缺参数；TagsApi trim、去重、保序、保留大小写并拒空项。Nebula、Comet、blue/green均独立编造。基线仅返回pending，真实红灯控制确认测试能识别错误。
2. 拆分：title与tags改不同Java文件，Graph定义依赖为空；integration依赖两者。Workflow引用明确Agent/Skill、argv、写集、成功行和180秒预算。
3. 来源：只有公开Spring依赖、官方工具和空HOME预热缓存。运行前核缓存逐文件SHA；每实例复制为私有可写副本，offline缺依赖不绕过。
4. 实例：冻结临时seed提交，Graph/三Workflow各有分支与worktree、沙箱、HOME/TMP。Graph本身探测后由可信宿主调度，不声称宿主调度器运行在子任务沙箱内。
5. 实现与验证：确定性夹具分别编写TitleApi/TagsApi，在各实例实际Maven verify/Gradle test+build、启动独立测试JVM，执行3项目标MockMvc测试并生成Boot可执行JAR。报告不能仅靠退出0。
6. 提升：确认观察到的树已停止、成功行、报告、JAR结构；宿主核HEAD/index/字节/写集后提交，仅提交功能源码。构建产物和缓存留TMP/HOME。
7. 集成：在新worktree串行合入两精确提交，核均为集成输入祖先；依次Maven和Gradle各重跑8项完整测试并打包。并发分支的绿灯不能代替合并后的验收。
8. 回收与交付：核时间重叠、依赖等待、来源身份、源HEAD未变和资源回收。异常/UNKNOWN保留原运行根与指针，不自动删除；成功验证后才移除夹具。公开仅审阅的汇总与内容摘要，工具/依赖/原始日志/运行根不上传。最终GitHub发布由独立交付职责执行。

失败控制、构建树回归、实际Spring构建与被动检查分别计数；未来扩展未知插件或平台须另行实测，不能沿用本例的通过结论。
