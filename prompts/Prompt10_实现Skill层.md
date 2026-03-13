<!-- source: 提示词.md | id: hfw3cd -->
你正在为 Vision Butler v5 实现正式 Skill 层。

任务目标：
把项目中的标准问题类型写成正式 Skill 文件，并与 MCP tools / resources 对齐。

必须创建：
- skills/scene_query/SKILL.md
- skills/history_query/SKILL.md
- skills/last_seen/SKILL.md
- skills/object_state/SKILL.md
- skills/zone_state/SKILL.md
- skills/ocr_query/SKILL.md
- skills/device_status/SKILL.md

可选创建：
- src/skill_registry.py

项目背景（必须遵守）：
1. Skill 是正式能力层的一部分。
2. Skill 不是工具本身，而是“如何解决某类问题”的标准执行模板。
3. Skill 必须约束工具调用，而不是鼓励模型自由乱调工具。
4. Skill 必须表达 freshness 与 fallback 规则。
5. Skill 的内容要与项目的 MCP 工具清单一致。

每个 Skill 必须包含：
- name
- description
- trigger_patterns
- allowed_tools
- allowed_resources
- auth_policy
- freshness_policy
- memory_write_policy
- state_effects
- fallback_rules
- steps
- output_schema

各 Skill 的职责：
- scene_query：当前场景、当前画面
- history_query：最近事件、时间范围查询
- last_seen：对象最后出现
- object_state：对象当前大概率状态
- zone_state：区域当前状态
- ocr_query：简单 OCR 与结构化 OCR
- device_status：设备状态与健康信息

必须遵守：
1. Skill 不写数据库访问逻辑。
2. Skill 不重复实现工具逻辑。
3. Skill 内容必须简明、可读、可被模型用作执行模板。
4. scene_query、ocr_query 必须明确说明何时直接回答，何时调用工具。
5. object_state、zone_state 必须明确 stale/fallback 处理。

验收标准：
- 每个 Skill 文件都存在
- 每个 Skill 都包含必需字段
- allowed_tools 与 MCP tool 清单一致
- fallback_rules 有实际内容
- output_schema 明确

完成后请：
1. 总结每个 Skill 的职责
2. 标出各 Skill 允许调用的 tools
3. 说明 freshness_policy 与 fallback_rules 的最小集合
4. 如果创建了 skill_registry.py，说明其职责
