---
name: docker-build-isolation
description: 显式选择Docker构建后端，核白名单输入、容器限制、候选身份与资源停止，不继承私人Docker状态。
---

# Docker构建隔离

适用：明确授权的Java/Spring构建需要Linux容器；输入为冻结提交、本地Engine、内容地址镜像、写集、运行根及预算。

方法正文唯一来源：[Docker沙箱合同](../../standards/docker-sandbox.md)。宿主执行[Docker机制](../../tools/execution/docker_runtime.py)，输入输出由[有界归档机制](../../tools/execution/docker_io.py)处理。此Skill不启动Graph或发布GitHub。

核明确Engine/镜像及空配置，传递白名单，探测实际容器限制，再运行上游命令。确认停止后检查JUnit、JAR与输出身份，交宿主broker进行源码提升和集成验收；对未知/失败保留原资源，回收只作用已确认且归属一致的对象。

输出为资源归属、来源、真实运行结果、停止/回收和未验边界；平台标签必须来自实际宿主，不能用Linux容器替代Linux宿主实测。缺环境时交NOT_RUN，禁止借用旧macOS结果冒充Docker通过。

返回：[Skills](../README.md)。
