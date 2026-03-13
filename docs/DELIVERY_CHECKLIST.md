# Delivery Checklist (T16)

## 1) 目录与关键文件检查
- [x] `AGENTS.md`
- [x] `README.md`
- [x] `docs/PRODUCT_PLAN.md`
- [x] `docs/ARCHITECTURE.md`
- [x] `docs/TEST_PLAN.md`
- [x] `docs/DEPLOYMENT.md`
- [x] `schema.sql`
- [x] `migrations/`
- [x] `config/*.yaml`
- [x] `config/nanobot.config.json`
- [x] `src/app.py`
- [x] `src/mcp_server/`
- [x] `skills/`
- [x] `tests/`
- [x] `scripts/init_db.sh`
- [x] `scripts/start_backend.sh`
- [x] `scripts/start_mcp.sh`
- [x] `scripts/start_gateway.sh`
- [x] `scripts/stack_ctl.sh`
- [x] `scripts/switch_ollama_ctx.sh`
- [x] `scripts/start_edge.sh`
- [x] `scripts/smoke_test.sh`

## 2) 当前可运行范围
- 后端 API：`src/app.py` + `routes_*` + SQLite 初始化可直接运行。
- Memory/Perception/State/Policy/Device/OCR/Security：均有可运行实现并有 unit/integration 覆盖。
- MCP Server tools/resources/prompts：可通过集成测试调用。
- Telegram 正式入口链路：`/telegram/update` 可处理命令、去重与错误回传。
- 三层测试矩阵：`unit/integration/e2e` 已落地，`pytest -q` 与 `unittest` 可通过。

## 3) 当前 stub / adapter 范围
- Telegram 与 nanobot 的真实外部网络对接依赖外部 token、进程与运行环境，仓库内以本地可测链路为主。
- Edge 侧为“可运行 CLI runtime + 可循环执行脚本”，未包含设备级守护进程/服务编排。
- 部署脚本以单机最小交付为目标，生产级进程托管（systemd/supervisor/k8s）需后续接入。

## 4) 建议首次启动顺序
1. `./scripts/init_db.sh`
2. `./scripts/start_backend.sh`
3. `./scripts/start_mcp.sh`
4. `NANOBOT_DRY_RUN=1 NANOBOT_INSTANCE=dev ./scripts/start_gateway.sh`
5. `EDGE_ACTION=heartbeat ./scripts/start_edge.sh`
6. `./scripts/smoke_test.sh`
