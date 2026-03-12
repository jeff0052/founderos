# Session 状态按需显示系统

## 功能说明

自动检测何时需要显示当前 session 状态，避免不必要的 token 消耗。

## 触发条件

1. **用户主动询问** - `/session`, `/where`, "在哪个空间", "当前session"
2. **长时间无活动** - 超过1小时没有对话
3. **话题跳转** - 检测到话题关键词完全不同（30分钟内没显示过）

## 使用方法

### 在回复前检查
```bash
node scripts/check-session-status.js "用户的消息内容"
```

返回：
- 如果需要显示：输出状态文本
- 如果不需要：空输出

### 强制显示状态
```bash
node scripts/session-selector.js status
```

### 示例集成
```javascript
const { checkSessionStatus } = require('./scripts/check-session-status');

async function generateReply(userMessage) {
    const statusText = await checkSessionStatus(userMessage);
    const reply = generateMainReply(userMessage);
    
    return statusText ? statusText + reply : reply;
}
```

## 状态格式

```
📍 当前空间: 🏠 主对话 (21k) · 输入 /sessions 切换

[正常回复内容]
```

## 配置

在 `scripts/session-selector.js` 中可调整：
- 长时间无活动阈值 (默认1小时)
- 话题检测关键词
- 重复显示间隔 (默认30分钟)

## 优势

- 99% 时间零 token 开销
- 智能检测真实需求
- 用户体验清晰
- 实现简单可靠