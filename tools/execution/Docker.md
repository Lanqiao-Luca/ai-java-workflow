# Docker执行机制

[容器后端](docker_runtime.py)复用现有Graph的Git broker、依赖与候选提升；独立构造portable资源入口，不初始化Seatbelt。[有界IO](docker_io.py)仅连接明确本地Unix socket，使用全新空CLI配置，不继承个人Docker上下文/认证。

[容器入口与镜像](../docker/Dockerfile)使用私有PID/IPC/cgroup和network none，非root、只读root、cap-drop ALL、no-new-privileges、seccomp及CPU/内存/PID限制。Linux Docker中省略--pid表示默认private，inspect拒绝host/container模式；实际探测还验证隔离和有效内核限额。

输入为无.git的白名单tar，metadata使用固定非零时间戳，避免Maven忽略资源。每实例3个命名volume，不挂宿主目录或Docker socket；确认停止后仅导出有界普通文件，不在宿主extractall。对应宿主候选安全回收后才删除Docker输出，失败/漂移/未知保留。

容器内墙钟timer覆盖probe、缓存复制和命令；宿主也监视超时/取消。退出后PID命名空间结束，setsid后代不能留在该容器外。daemon/创建响应不明时保持active并隔离共享池，不自动重放或清理原根。Docker控制面、镜像、内核和macOS VM属于可信计算基；命名volume没有总磁盘硬配额。

入口：[run_docker_graph.py](../../scripts/run_docker_graph.py)。来源、预算和停止条件按上游Agent/Skill消费规范；此目录是实现机制，没有自动模型调用或平台注册。

[归档/策略单元测试](../../tests/test_docker_io.py)默认可运行；[真实Engine测试](../../tests/test_docker_backend.py)需要显式Docker/image，缺环境以NOT_RUN退出，不能冒充内核通过。旧严格与可信macOS后端保持独立历史。
