<!-- source: 提示词.md | id: ctr75k -->
你正在为 Vision Butler v5 完成 nanobot 集成。

任务目标：
将 nanobot 作为正式唯一主控宿主接入 Telegram、Qwen3.5、多实例 workspace 和 MCP servers。

必须创建或补齐：
- config/nanobot.config.json
- gateway/nanobot_workspace/
- scripts/start_gateway.sh
- docs/DEPLOYMENT.md 中关于 nanobot 的启动说明

项目背景（必须遵守）：
1. Telegram 是正式唯一用户入口。
2. nanobot 是唯一主控宿主，但不是业务真相层。
3. 所有业务能力优先通过 MCP servers 暴露给 nanobot。
4. 不要深改 nanobot 核心代码。
5. 要支持正式实例和开发实例分离。

配置至少应覆盖：
- Telegram channel enabled
- Telegram token 占位
- allowFrom 配置
- model provider / model name
- tools.mcpServers
- workspace 路径
- runtime 相关目录
- 可选：tool timeout / concurrency

必须遵守：
1. 所有敏感配置用占位符，不要填真实 token。
2. config 文件结构要尽量贴近 nanobot 正式能力边界。
3. 不要把 MCP server 逻辑写进 nanobot 配置之外的 hack 脚本。
4. start_gateway.sh 要能表达完整启动意图。
5. DEPLOYMENT.md 要说明正式实例 / 开发实例的区别。

验收标准：
- nanobot.config.json 结构清晰
- 可以看出 Telegram、模型、MCP、workspace 四部分配置
- start_gateway.sh 有清晰命令和环境变量说明
- DEPLOYMENT.md 说明正式与测试实例如何隔离

完成后请：
1. 解释 nanobot 配置结构
2. 说明 allowFrom、workspace、mcpServers 的作用
3. 给出正式实例和开发实例的配置差异建议
4. 说明为什么此任务不应通过深改 nanobot 完成
