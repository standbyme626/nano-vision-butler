<!-- source: TASKS.md | id: local_t2_config -->
你正在为 Vision Butler v5 实现统一配置系统。

任务目标：
建立统一配置加载机制，集中管理 settings / policies / access / devices / cameras / aliases，并支持后端服务注入。

必须创建或补齐：
- config/settings.yaml
- config/policies.yaml
- config/access.yaml
- config/devices.yaml
- config/cameras.yaml
- config/aliases.yaml
- src/settings.py 或等价配置加载模块

最低要求：
- 支持一次性加载全部配置文件
- 配置缺失时抛出可读错误（指出缺哪个文件/字段）
- 配置对象可以被 app 与 services 注入复用

必须遵守：
1. 配置与业务代码分离，不要把策略硬编码在路由或服务里。
2. 不要在配置文件中写入真实敏感凭据，使用占位符。
3. 配置结构要贴合项目边界：Telegram 入口、nanobot 宿主、MCP/Skill 能力、edge 设备。
4. 不要跳过 access / devices 相关配置；安全与设备访问控制必须可配置。
5. 保持与现有目录职责一致，不做无关重构。

不要做的事情：
- 不要把数据库连接和配置解析耦合成单体脚本
- 不要引入与当前项目无关的复杂配置框架
- 不要把默认值散落在多个模块中互相覆盖

完成后请：
1. 列出新增/修改的配置文件清单
2. 说明每个配置文件职责与关键字段
3. 给出一条最小配置校验命令或示例调用
4. 标注哪些配置是正式可用，哪些仍是占位符
