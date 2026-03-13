# Test Plan (T0 Skeleton)

## 测试目标
确保系统在“感知 -> 记忆 -> 状态 -> 回答”链路下可验证、可回归、可审计。

## 三层测试策略

### 1. Unit Tests
- 范围：`src/schemas/`、`src/services/`、`src/security/`、工具函数
- 重点：状态推理、策略判断、配置校验、时间新鲜度计算
- 目标：关键函数可重复、边界条件明确

### 2. Integration Tests
- 范围：API 路由 + service + repository + SQLite
- 重点：observation/event/state 流程、telegram_updates 去重、audit_logs 写入
- 目标：跨模块协作正确，数据库约束生效

### 3. E2E Tests
- 范围：Telegram 输入到最终回复的主链路
- 重点：MCP 工具编排、Skill 执行顺序、失败回退
- 目标：核心用户场景端到端可用

## 质量门禁（后续阶段执行）
- 单元测试通过率满足核心模块覆盖要求
- 集成测试覆盖关键事实链路
- E2E 覆盖至少“当前问答/历史查询/OCR/设备状态”主场景
- 任何敏感动作必须可在 `audit_logs` 追踪
