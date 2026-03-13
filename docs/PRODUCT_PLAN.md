# Product Plan (T0 Skeleton)

## 产品定义
Nano Vision Butler v5 是一个通过 Telegram 交互的视觉管家系统。

系统由以下正式部分组成：
- Telegram Bot（唯一用户入口）
- nanobot Gateway（唯一主控宿主）
- 多模态模型（理解与决策）
- MCP / Skills（能力暴露与调用约束）
- RK3566 边缘前端（感知与上报）
- 后端 sidecar 服务（业务事实层）

## 总体目标
系统应支持以下核心问题：
- 现在看到了什么
- 最近发生了什么
- 对象最后一次出现在哪里
- 对象当前是否大概率仍在
- 区域当前状态是否异常
- 简单 OCR 与结构化信息抽取

## 边界与非目标
- 不做运动控制、3D 建图、多机器人协同
- 不做云端多租户 SaaS 与高并发分布式平台
- 不让前端承担长期记忆、状态推理、权限治理
- 不把业务逻辑硬编码进 Telegram 处理层

## T0 交付范围
- 仓库目录骨架建立
- 基础治理文档建立（README/ARCHITECTURE/TEST_PLAN/DEPLOYMENT）
- 任务与执行清单可追踪（TASKS/PROGRESS_CHECKLIST）
