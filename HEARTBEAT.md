# HEARTBEAT.md

# Context 大小监控
检查 session_status，如果 context >100k 提醒用户新开 session 避免限流

# 话题切换建议
Context >50k 且对话超过30分钟时，建议切换话题避免混杂

# 可选：系统健康检查
- 检查是否有未处理的错误
- 检查内存使用情况
