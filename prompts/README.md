# Prompts Index (Human-Readable)

主序列（保留 Prompt01~Prompt15）：
- Prompt01 初始化仓库与文档骨架
- Prompt02 实现数据库与迁移系统
- Prompt03 实现 Schema 与 Repository 层
- Prompt04 实现 FastAPI 后端骨架
- Prompt05 实现 memory 与 perception 服务
- Prompt06 实现 state 与 policy 服务
- Prompt07 实现 device 服务与媒体链路
- Prompt08 实现 OCR 双通道
- Prompt09 实现 MCP Server 层
- Prompt10 实现 Skill 层
- Prompt11 nanobot 集成与正式宿主配置
- Prompt12 RK3566 前端最小正式实现
- Prompt13 安全与访问控制落地
- Prompt14 测试矩阵落地
- Prompt15 最终联调收尾与交付

补充 Prompt：
- Prompt02B 实现配置系统（补齐 T2）
- Prompt11B Telegram 正式交互链路（对应 T12）
- Prompt12A RK3566 板级 bring-up 与基线测量（对应 T13A）
- Prompt12B 前端协议冻结（event/heartbeat/command，对应 T13B）
- Prompt12C 真实采集层替换（V4L2/GStreamer，对应 T13C）
- Prompt12D 真实 Snapshot 落地（JPEG，对应 T13D）
- Prompt12E 命令闭环最小打通（对应 T13E）
- Prompt12F RKNN 检测模型部署（主检测，对应 T13F）
- Prompt12G 跟踪/Zone/事件压缩质量提升（对应 T13G）
- Prompt12H Recent Clip 真实化（MP4 + ring buffer，对应 T13H）
- Prompt12I 可靠性/安全/压测验收（对应 T13I）

建议执行顺序：
- Prompt01 -> Prompt02 -> Prompt02B -> Prompt03 -> Prompt04 -> Prompt05 -> Prompt06 -> Prompt07 -> Prompt08 -> Prompt09 -> Prompt10 -> Prompt11 -> Prompt11B -> Prompt12 -> Prompt12A -> Prompt12B -> Prompt12C -> Prompt12D -> Prompt12E -> Prompt12F -> Prompt12G -> Prompt12H -> Prompt12I -> Prompt13 -> Prompt14 -> Prompt15

Prompt 与 TASKS 映射：
- Prompt01 -> T0
- Prompt02 -> T1
- Prompt02B -> T2
- Prompt03 -> T3
- Prompt04 -> T4
- Prompt05 -> T5
- Prompt06 -> T6
- Prompt07 -> T7
- Prompt08 -> T8
- Prompt09 -> T9
- Prompt10 -> T10
- Prompt11 -> T11
- Prompt11B -> T12
- Prompt12 -> T13
- Prompt12A -> T13A
- Prompt12B -> T13B
- Prompt12C -> T13C
- Prompt12D -> T13D
- Prompt12E -> T13E
- Prompt12F -> T13F
- Prompt12G -> T13G
- Prompt12H -> T13H
- Prompt12I -> T13I
- Prompt13 -> T14
- Prompt14 -> T15
- Prompt15 -> T16

模板：
- Template_AGENTS.md
- Template_TASKS.md
