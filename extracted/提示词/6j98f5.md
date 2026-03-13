<!-- source: 提示词.md | id: 6j98f5 -->
你正在为 Vision Butler v5 实现正式安全与访问控制层。

任务目标：
实现统一的 security_guard / access_policy，使 Telegram 用户、设备、tools、resources 和媒体访问都受控，并可审计。

需要创建或补齐：
- src/security/security_guard.py
- src/security/access_policy.py
- src/schemas/security.py
- tests/unit/test_security_guard.py
- tests/integration/test_access_control_flow.py

项目背景（必须遵守）：
1. nanobot 的 allowFrom 是入口层白名单，不等于系统内部完整权限模型。
2. 系统内部还需要：
   - user_allowlist
   - device_allowlist
   - tool_allowlist_per_skill
   - resource_scope_per_skill
   - media_visibility_scope
3. 所有拒绝行为都必须进入 audit_logs。
4. 安全层要独立，不允许把权限规则散落在路由和服务里。

必须实现的能力：
- validate_user_access(user_id / telegram_user_id)
- validate_device_access(device_id, api_key or equivalent)
- validate_tool_access(skill_name, tool_name)
- validate_resource_access(skill_name, resource_uri)
- validate_media_visibility(user_id, media_id)
- audit_allow / audit_deny

必须遵守：
1. security_guard 只负责校验和审计，不负责业务回答。
2. 不要把配置写死在代码里，应从 access.yaml / devices.yaml 等配置加载。
3. 拒绝必须返回明确 reason。
4. 所有工具调用前必须有 validate_tool_access 的接入点。
5. 所有资源读取前必须有 validate_resource_access 的接入点。

建议输出：
- access policy 数据模型
- guard 层服务
- 与 repository / audit_repo 的集成
- 示例 access.yaml 结构
- 测试覆盖 allow / deny / missing policy / unauthorized device

验收标准：
- 非 allowlist 用户会被拒绝
- 非 allowlist 设备会被拒绝
- Skill 调未授权 tool 会被拒绝
- 读取未授权 resource 会被拒绝
- 读取未授权 media 会被拒绝
- 所有拒绝行为有 audit 记录

完成后请：
1. 说明安全模型结构
2. 列出至少 5 个 reason_code / denial reason
3. 说明 allowFrom 与内部 security_guard 的边界区别
4. 给出 access.yaml 示例
