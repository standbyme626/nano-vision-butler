<!-- source: 提示词.md | id: xywuhl -->
你正在为 Vision Butler v5 做最终联调与交付打包。

任务目标：
在不重构核心边界的前提下，对整个仓库做一次“可运行、可验收、可交付”的最终收尾。

需要完成：
- 检查目录结构是否与 AGENTS.md / PRODUCT_PLAN.md 一致
- 检查 config/ 是否齐全
- 检查 scripts/ 是否齐全
- 检查 docs/ 是否齐全
- 检查 tests/ 是否齐全
- 补齐遗漏的 README / 使用说明
- 补齐最小启动脚本
- 跑 smoke test
- 输出交付摘要

项目背景（必须遵守）：
1. 不要趁联调阶段大改架构。
2. 不要顺手做无关优化。
3. 所有补丁必须服务于“让项目能启动、能测试、能理解”。
4. 不要改动 nanobot 的核心外部依赖方式。
5. 所有正式入口、正式能力、正式文档都必须可被定位。

必须检查的交付项：
- AGENTS.md
- README.md
- docs/PRODUCT_PLAN.md
- docs/ARCHITECTURE.md
- docs/TEST_PLAN.md
- docs/DEPLOYMENT.md
- schema.sql
- migrations/
- config/*.yaml
- config/nanobot.config.json
- src/app.py
- src/mcp_server/
- skills/
- tests/
- scripts/init_db.sh
- scripts/start_backend.sh
- scripts/start_gateway.sh
- scripts/start_edge.sh
- scripts/smoke_test.sh

必须遵守：
1. 只做“让交付完整”的修改。
2. 缺文档就补文档，缺脚本就补脚本，缺占位就补占位。
3. 不要因为联调而把 TODO 伪装成 DONE。
4. 对尚未完全实现的部分，必须在 README 或 DEPLOYMENT.md 中诚实标注。
5. 输出必须包含“当前可运行范围”和“后续待接真实适配器范围”。

验收标准：
- 仓库结构完整
- 启动脚本存在
- smoke test 可运行
- 文档可指导第一次启动
- 明确哪些地方仍是 stub / adapter

完成后请：
1. 给出交付清单
2. 标出当前已真实可运行的模块
3. 标出当前仍为 stub / adapter 的模块
4. 给出建议的第一次启动顺序
