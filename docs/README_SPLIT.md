# Workspace Split Guide

当前整理规则：
- `AGENTS.md` 保留在仓库根目录（不归档到 docs）。
- `计划书.md` 保留在仓库根目录（便于直接调取）。
- 源文件（原版文档）统一放在 `docs/source/original/`（不含 `AGENTS.md`、`计划书.md`）。
- 拆分产物放在仓库根目录外层，便于直接调取：
  - `structured/`：按主题整理的工作副本
  - `extracted/`：按 `id="..."` 自动拆出的片段
  - `prompts/`：按 Prompt01~Prompt15 的主序列 + 补充 Prompt02B/Prompt11B
  - `PROGRESS_CHECKLIST.md`：可打勾的执行与验收清单

## 目录说明
- `docs/source/original/`：原版来源文档（归档）
- `structured/`：结构化副本（治理/项目/运维/数据）
- `extracted/`：代码块拆分结果 + 索引
- `prompts/`：可直接执行的提示词集合（主序列 + 补充）
- `PROGRESS_CHECKLIST.md`：项目进度打勾与验收规则
