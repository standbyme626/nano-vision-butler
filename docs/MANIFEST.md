# Split Manifest

## Source of Truth
- `AGENTS.md` (root): 运行时主规范（保留在根目录）
- `TASKS.md` (root): 可变任务板（保留在根目录）
- `计划书.md` (root): 当前主计划书（便于直接调取）
- `docs/source/original/`: 其余原版来源文档

## Source Files Archived in docs/source/original
- `原稿计划书.md`
- `意义.md`
- `任务.md`
- `提示词.md`
- `readme参考.md`
- `skill参考.md`
- `数据库.md`
- `迁移版本草案.md`

## Split Outputs (outside docs)
- `structured/`
- `extracted/`
- `prompts/`
- `PROGRESS_CHECKLIST.md`

## Notes
- 本次重排不修改原文内容，只调整位置和索引。
- 提示词执行目录 `prompts/` 采用主序列 `Prompt01~Prompt15`，并补充 `Prompt02B`（配置系统）与 `Prompt11B`（Telegram 链路）用于与任务板对齐。
