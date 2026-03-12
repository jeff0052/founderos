# Elon 系统备份指南

## 快速使用

```bash
# 创建备份
./scripts/elon-backup.sh backup

# 查看现有备份
./scripts/elon-backup.sh list

# 恢复系统
./scripts/elon-backup.sh restore elon-backup-20260312-203900.tar.gz
```

## 备份内容

✅ **包含**:
- 工作区完整内容 (SOUL.md, MEMORY.md, skills/ 等)
- 共享内存状态
- OpenClaw 配置文件
- 系统元数据

❌ **排除**:
- Git 历史记录 (减小体积)
- Node modules
- 日志和缓存文件

## 迁移场景

### 场景1: 换电脑
1. 在旧机器: `./elon-backup.sh backup`
2. 传输备份文件到新机器
3. 在新机器安装 OpenClaw
4. `./elon-backup.sh restore <backup-file>`
5. 更新 API keys 和本地路径

### 场景2: 系统重置
1. 先备份: `./elon-backup.sh backup` 
2. 重装系统后恢复
3. 检查配置更新

### 场景3: 定期备份
```bash
# 添加到 crontab
0 2 * * 0 /path/to/scripts/elon-backup.sh backup
```

## 安全提示

- 备份文件包含记忆和配置，妥善保管
- 恢复前会自动备份现有系统
- API keys 需要手动重新配置