<!-- source: readme参考.md | id: m2pwjk -->
# Vision Butler v5

基于 nanobot 的视觉管家系统 v5。  
正式入口为 Telegram，正式宿主为 nanobot，正式认知核心为 Qwen3.5 多模态模型，正式能力层为 MCP + Skills，正式前端为 RK3566 单目前端，正式事实层为 backend sidecar services。

---

## 1. 项目简介

Vision Butler v5 是一个通过 Telegram 进行交互的视觉管家系统。  
它不是普通“看图聊天机器人”，也不是传统安防 NVR，而是一个能够：

- 回答当前画面里有什么
- 回答最近发生了什么
- 回答某个对象最后一次在哪里出现
- 回答某个对象现在大概率还在不在
- 回答某个区域当前像不像有人或有物
- 对图片、快照和局部内容做简单 OCR / 结构化 OCR
- 主动拍照、回传最近视频片段
- 查询设备在线状态、负载、心跳与异常

的完整视觉管家系统。

---

## 2. 系统正式组成

系统由以下部分组成：

### 2.1 Telegram Bot
唯一正式用户入口，负责接收文本、图片、命令与媒体请求。

### 2.2 nanobot
唯一主控入口与 Agent 宿主，负责：
- 会话管理
- 模型调用
- Skill 加载
- MCP 工具挂载
- 最终回复生成

### 2.3 Qwen3.5 多模态模型
负责：
- 理解用户问题
- 理解图片与短视频
- 执行简单 OCR
- 判断是否调用工具
- 整合工具结果并输出回答

### 2.4 MCP Server 层
负责把正式业务能力暴露为：
- Tools
- Resources
- Prompts

### 2.5 Skills
负责定义标准执行模板：
- 何时调用哪些工具
- 哪些工具可用
- freshness 策略
- fallback 规则
- 输出结构要求

### 2.6 Backend Sidecar Services
负责：
- perception_service
- memory_service
- state_service
- policy_service
- security_guard
- device_service
- ocr_service

### 2.7 RK3566 单目前端
负责：
- 相机采集
- 轻量检测
- 轻量跟踪
- 事件压缩
- 快照缓存
- 最近视频片段缓存
- 设备心跳
- 响应拍照和取 clip 命令

---

## 3. 正式能力

本项目首发即纳入正式范围的能力包括：

1. 当前观察
2. 最近事件
3. last_seen
4. object_state
5. zone_state
6. world_state 摘要
7. take_snapshot
8. get_recent_clip
9. 简单 OCR
10. 结构化 OCR
11. 设备状态查询
12. 主动通知
13. 权限控制与审计

---

## 4. 核心设计原则

### 4.1 入口统一
Telegram 是正式唯一入口。

### 4.2 主控统一
nanobot 是唯一主控宿主，但不是业务真相层。

### 4.3 能力分层
- 模型负责理解与决策
- 工具负责事实与动作
- 前端负责事件感知
- 后端负责状态真相

### 4.4 单目前端边界清晰
RK3566 单目前端不是完整智能体。  
它只负责边缘感知，不负责长期记忆、复杂状态聚合、Telegram 交互和权限控制。

### 4.5 状态显式化
系统不只回答“最后一次看到”，还要回答“现在大概率还在不在”，因此必须有 state / policy 层。

---

## 5. 明确非目标

当前版本明确不做：

- 运动控制
- ROS / ROS2 集成
- 3D 建图
- 多机器人协同
- 云端多租户 SaaS
- 高并发分布式部署
- 多摄像头空间拓扑重建
- 单目前端精确三维定位
- 完整 Web 管理后台

---

## 6. 仓库结构

推荐仓库结构如下：

```text
vision_butler/
├─ AGENTS.md
├─ README.md
├─ schema.sql
├─ migrations/
├─ docs/
├─ config/
├─ gateway/
├─ edge_device/
├─ src/
├─ skills/
├─ tests/
└─ scripts/
