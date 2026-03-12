# Session Manager Skill

**在单一聊天界面中模拟多对话框体验的智能 session 管理系统**

## 🎯 解决的问题

- **Context 混杂**：不同话题挤在一个 session，导致上下文污染
- **无法定位**：不知道当前在讨论什么话题或项目  
- **成本浪费**：频繁显示状态信息消耗 token
- **切换困难**：没有直观的方式在不同对话主题间切换

## ✨ 核心功能

### 📂 多 Session 选择器
- 类似浏览器标签页的界面体验
- 6个独立对话空间（1个主对话 + 5个自定义）
- 每个空间独立的 context，避免话题混杂
- 一键切换，状态持久化

### 💡 智能状态显示
- **按需显示原则**：99% 时间零 token 开销
- 智能检测用户需求：询问、长时间无活动、话题跳转
- 避免视觉噪音和不必要的成本

### 🔍 自动话题检测
- 基于关键词的话题分类（技术、项目、日常等）
- 自动检测话题跳转，建议切换空间
- 可配置的检测敏感度和冷却时间

## 🚀 快速开始

### 1. 显示选择器
```bash
cd skills/session-manager
node scripts/integration.js selector
```

### 2. 检查状态需求
```bash
node scripts/integration.js check "我现在在哪个空间？"
```

### 3. 创建新空间
```bash
node scripts/integration.js create "项目讨论" "产品规划和战略决策"
```

## 📁 目录结构

```
skills/session-manager/
├── SKILL.md                    # 主要文档
├── README.md                   # 本文件
├── scripts/
│   ├── session-selector.js     # 核心选择器逻辑
│   ├── check-session-status.js # 状态检查器
│   └── integration.js          # 集成助手（推荐使用）
├── references/
│   ├── api-reference.md        # 详细API文档
│   ├── examples.md            # 使用示例
│   └── README-session-status.md # 状态显示说明
└── config/
    └── default-sessions.json  # 默认配置和模板
```

## 🔧 集成方式

### 方式1：简单集成
```javascript
const { beforeReply } = require('./skills/session-manager/scripts/integration');

async function handleMessage(userMessage) {
    const { needsStatus, statusText } = await beforeReply(userMessage);
    const mainReply = generateReply(userMessage);
    
    return needsStatus ? statusText + mainReply : mainReply;
}
```

### 方式2：中间件模式
```javascript
const { withSessionManager } = require('./skills/session-manager/scripts/integration');

const enhancedReply = withSessionManager(originalReplyFunction);
```

### 方式3：显示选择器
```javascript
const { showSessionSelector } = require('./skills/session-manager/scripts/integration');

const selectorUI = await showSessionSelector();
// 发送 selectorUI.text 和 selectorUI.buttons
```

## 📊 状态示例

### 正常对话
```
用户: 今天天气怎么样？
助手: 今天新加坡多云，温度 28°C...
// 无额外状态显示
```

### 用户询问位置
```
用户: 我现在在哪个session？
助手: 📍 当前空间: 🏠 主对话 (21k) · 输入 /sessions 切换

你目前在主对话空间...
```

### 话题跳转检测
```
用户: 我想讨论一下代码bug的问题
助手: 🔄 当前空间: 🏠 主对话 (21k) · 输入 /sessions 切换
💡 检测到技术话题，建议切换到技术支持空间。

关于bug问题，我可以帮你...
```

## ⚙️ 配置选项

编辑 `config/default-sessions.json`：

```json
{
  "settings": {
    "maxSessions": 6,              // 最大session数量
    "inactiveThreshold": 3600000,  // 无活动阈值（毫秒）
    "showCooldown": 1800000,       // 显示冷却时间
    "autoCleanup": true            // 自动清理空会话
  },
  "keywords": {
    "tech": ["代码", "bug", "API"],    // 技术关键词
    "project": ["产品", "项目"],        // 项目关键词
    "daily": ["天气", "心情"]          // 日常关键词
  }
}
```

## 📈 性能特点

- **零开销设计**：正常对话无额外 token 消耗
- **智能触发**：仅在真正需要时显示状态
- **轻量级**：状态文件 < 5KB，加载快速
- **可扩展**：支持自定义触发条件和显示格式

## 🔄 数据流

```
用户消息 → 检查是否需要显示状态 → 更新活动记录 → 生成回复
     ↓                    ↓              ↓          ↓
状态检查逻辑          记录话题关键词    保存状态    组合最终回复
```

## 🛠️ 技术栈

- **Node.js**：核心运行环境
- **JSON**：状态持久化存储
- **正则表达式**：关键词匹配
- **Telegram API**：按钮界面支持

## 📚 相关文档

- [SKILL.md](./SKILL.md) - 完整功能说明
- [API Reference](./references/api-reference.md) - 详细API文档  
- [Examples](./references/examples.md) - 实际使用示例
- [Config Guide](./config/default-sessions.json) - 配置说明

## 🎉 效果演示

**选择器界面**：
```
📂 Session 选择器

当前空间: 🏠 主对话
活跃空间数: 1/6

空间状态:
🟢 🏠 主对话 (21k) - 日常对话和任务
⚪ ➕ 新建 1 - 点击创建
⚪ ➕ 新建 2 - 点击创建
...

[🏠 主对话 ✓] [➕ 新建 1]
[➕ 新建 2]  [➕ 新建 3]
[⚙️ 管理]
```

**使用体验**：
✅ 清晰知道当前位置  
✅ 一键切换对话空间  
✅ 智能提醒，不打扰  
✅ 零学习成本，直觉操作  

---

**作者**: Claude  
**版本**: 1.0.0  
**更新**: 2026-03-12  
**状态**: ✅ 已完成，可投入使用