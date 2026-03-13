<!-- source: 提示词.md | id: wc8q37 -->
你正在为一个新仓库实现 Vision Butler v5 的正式代码骨架。

任务目标：
建立正式仓库目录结构，并创建以下基础文件：
- AGENTS.md
- README.md
- docs/PRODUCT_PLAN.md
- docs/ARCHITECTURE.md
- docs/TEST_PLAN.md
- docs/DEPLOYMENT.md
- config/ 空模板文件
- scripts/ 空模板文件

必须遵守：
1. Telegram 是正式唯一用户入口。
2. nanobot 是唯一主控宿主，但不是业务真相层。
3. MCP / Skill 是正式能力层。
4. RK3566 单目前端只负责边缘感知，不负责长期记忆、状态聚合和 Telegram 交互。
5. 不要写业务实现代码，只做仓库骨架与文档初始化。
6. 不要引入无关框架或 Docker 编排。

目标目录结构：
- docs/
- config/
- gateway/
- edge_device/
- src/
- skills/
- tests/
- scripts/

输出要求：
- 所有文件内容必须与 Vision Butler v5 的最终方案一致。
- README 需要清晰说明项目定位、核心组成和启动顺序。
- AGENTS.md 需要明确写出目标、非目标、禁止事项、目录职责和完成定义。
- docs/ARCHITECTURE.md 需要包含分层架构说明。
- docs/TEST_PLAN.md 需要包含 unit / integration / e2e 三层测试规划。

完成后请：
1. 列出新建文件清单
2. 简要说明每个文件用途
3. 不要额外重构目录
