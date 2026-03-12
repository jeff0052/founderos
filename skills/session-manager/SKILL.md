# Session Manager Skill

在 Telegram 等单一聊天界面中模拟多对话框体验，实现智能的 session 状态按需显示。

## 核心功能

### 🎯 多 Session 选择器
- 在 Telegram 内显示类似浏览器标签页的界面
- 6个独立对话空间（1个主对话 + 5个自定义）
- 每个空间独立的 context，避免话题混杂

### 💡 智能状态显示
- **按需显示原则**：99% 时间零 token 开销
- 只在真正需要时显示当前 session 状态
- 避免视觉噪音和不必要的成本

### 🔍 触发条件
1. **用户主动询问** - `/session`, `/where`, "在哪个空间"
2. **长时间无活动** - 超过1小时没有对话
3. **话题跳转检测** - 检测到话题关键词完全不同

## 快速开始

### 显示 Session 选择器
```javascript
const selector = new SessionSelector();
const keyboard = selector.generateKeyboard();
const info = selector.generateSessionInfo();

// 发送带按钮的选择界面
message.send({
    text: info,
    buttons: keyboard
});
```

### 检查是否显示状态
```javascript
const { checkSessionStatus } = require('./scripts/check-session-status');

async function beforeReply(userMessage) {
    const statusText = await checkSessionStatus(userMessage);
    return statusText || ''; // 可能为空
}
```

### 命令行使用
```bash
# 检查是否需要显示状态
cd skills/session-manager
node scripts/check-session-status.js "用户消息内容"

# 强制显示状态
node scripts/session-selector.js status

# 显示选择器
node scripts/session-selector.js keyboard
```

## 工作原理

### Session 状态文件
```json
{
  "sessions": {
    "main": {
      "name": "🏠 主对话",
      "contextSize": 21,
      "lastActivity": 1710188120,
      "description": "日常对话和任务"
    }
  },
  "currentSession": "main",
  "lastActivity": 1710188120,
  "lastTopicKeywords": ["context", "token"],
  "lastShowTime": 1710187800
}
```

### 智能检测逻辑
1. **关键词提取**：技术词汇、项目词汇、生活词汇
2. **话题跳转**：对比当前和上次的关键词重叠度
3. **时间间隔**：防止频繁显示的冷却机制

### 状态显示格式
```
📍 当前空间: 🏠 主对话 (21k) · 输入 /sessions 切换

[正常回复内容]
```

## 配置

### 调整检测敏感度
编辑 `scripts/session-selector.js`：

```javascript
// 长时间无活动阈值 (毫秒)
const INACTIVE_THRESHOLD = 3600000; // 1小时

// 重复显示间隔
const SHOW_COOLDOWN = 1800000; // 30分钟

// 话题关键词分类
const KEYWORDS = {
    tech: ['代码', 'bug', '数据库', 'API'],
    project: ['产品', '项目', '需求', '设计'],
    daily: ['吃饭', '天气', '时间', '心情']
};
```

### 自定义默认 Session
编辑 `config/default-sessions.json`：

```json
{
  "main": {
    "name": "🏠 主对话",
    "description": "日常对话和任务"
  },
  "project": {
    "name": "📋 项目讨论", 
    "description": "产品开发和战略规划"
  }
}
```

## 集成方式

### 方式1：回复前检查
```javascript
// 在生成回复前调用
const statusPrefix = await checkSessionStatus(userMessage);
const mainReply = generateReply(userMessage);
return statusPrefix + mainReply;
```

### 方式2：中间件模式
```javascript
async function sessionMiddleware(userMessage, next) {
    const statusText = await checkSessionStatus(userMessage);
    const reply = await next();
    return statusText ? statusText + reply : reply;
}
```

### 方式3：事件监听
```javascript
// 在特定事件触发检查
events.on('beforeReply', async (context) => {
    const status = await checkSessionStatus(context.userMessage);
    if (status) context.prefixText = status;
});
```

## 优势

### 🎯 解决痛点
- **Context 混杂**：不同话题挤在一个 session
- **无法定位**：不知道当前在讨论什么话题
- **成本浪费**：频繁显示状态消耗 token

### 💡 智能设计
- **按需显示**：只在真正需要时显示
- **成本控制**：日常对话零额外开销
- **用户体验**：清晰知道当前位置

### 🔧 技术优势
- **轻量集成**：一行代码即可使用
- **状态持久**：自动保存和恢复状态
- **可配置**：关键参数可自定义调整

## API 参考

详见 `references/api-reference.md`

## 使用示例

详见 `references/examples.md`

---

**作者**: Claude  
**版本**: 1.0.0  
**更新**: 2026-03-12