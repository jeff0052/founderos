# HEARTBEAT.md

# FPMS 项目扫描
运行 `python3 ~/fpms/spine.py heartbeat`
- 如果输出不是 FPMS_HEARTBEAT_OK → 报告告警给用户
- 如果有 🔴/🟠 级别告警 → 立即通知

# Context 大小监控
检查 session_status，如果 context >100k 提醒用户新开 session 避免限流

# 话题切换建议
Context >50k 且对话超过30分钟时，建议切换话题避免混杂
