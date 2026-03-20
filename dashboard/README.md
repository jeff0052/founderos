# FounderOS FPMS Dashboard 📊

实时项目管理和任务状态可视化界面。

## 🌐 在线访问

**GitHub Pages**: https://jeff0052.github.io/founderos/dashboard/

## 📱 本地运行

### 静态版本
```bash
# 直接在浏览器打开
open fpms-dashboard.html
```

### 动态服务器版本
```bash
# 启动本地服务器 (需要访问 FPMS 数据库)
python3 dashboard-server.py

# 访问: http://localhost:8080
```

### 实时数据更新
```bash
# 导出最新数据
python3 fpms-data-export.py fpms-data.json

# 刷新浏览器页面
```

## 🎯 功能特性

- ✅ **实时数据** — 直接从 FPMS SQLite 数据库读取
- ✅ **项目概览** — Goals/Projects/Tasks 状态统计  
- ✅ **任务分布** — inbox/active/done 可视化
- ✅ **记忆系统** — Fact/Judgment/Scratch 统计
- ✅ **活动时间线** — 最近更新记录
- ✅ **响应式设计** — 支持手机和桌面访问

## 📂 文件说明

| 文件 | 说明 |
|------|------|
| `index.html` | GitHub Pages 静态演示版本 |
| `fpms-dashboard.html` | 完整功能版本 (本地使用) |
| `fpms-data-export.py` | 数据导出脚本 |
| `dashboard-server.py` | 本地动态服务器 |

## 🔧 技术架构

```
FPMS SQLite DB → Python Export → JSON Data → HTML Dashboard
              ↘ 
                Python Server → HTTP API → Live Updates
```

## 🚀 V4 集成预览

Dashboard 包含了即将到来的 V4 GitHub 集成功能预览：
- 📋 GitHub Issues 创建和同步
- 🔄 状态双向同步  
- 📊 GitHub Projects 集成

## 📊 数据模型

Dashboard 展示的核心数据：

```json
{
  "overview": {
    "goals": 2,
    "projects": 7, 
    "tasks": 49,
    "completion_rate": 28.6
  },
  "task_distribution": {
    "inbox": 34,
    "active": 1, 
    "done": 14
  },
  "memory_system": {
    "facts": 11,
    "judgments": 13,
    "scratch": 2
  }
}
```

---

**FounderOS V4** — 一人公司操作系统  
🚀 让 AI Office 体系管理整家公司