# Session Manager API 参考

## SessionSelector 类

### 构造函数
```javascript
const selector = new SessionSelector();
```

自动从 `memory/session-state.json` 加载状态，如果不存在则创建默认 sessions。

### 方法

#### `generateKeyboard()`
生成 Telegram inline keyboard 格式的按钮数组。

**返回**: `Array<Array<ButtonObject>>`

```javascript
[
  [
    {"text": "🏠 主对话 ✓", "callback_data": "switch_main"},
    {"text": "➕ 新建 1", "callback_data": "create_slot_1"}
  ]
]
```

#### `generateSessionInfo()`
生成当前 session 状态的文本描述。

**返回**: `string`

```javascript
const info = selector.generateSessionInfo();
// 输出：
// 📂 **Session 选择器**
// 当前空间: 🏠 主对话
// 活跃空间数: 1/6
// ...
```

#### `shouldShowStatus(userMessage)`
检测是否需要显示 session 状态。

**参数**:
- `userMessage` (string): 用户输入的消息

**返回**: `string|false`
- `'user_request'`: 用户主动询问
- `'long_inactive'`: 长时间无活动  
- `'topic_change'`: 话题跳转
- `false`: 无需显示

```javascript
const reason = selector.shouldShowStatus("现在在哪个session？");
// 返回: 'user_request'
```

#### `generateStatusDisplay(reason)`
生成状态显示文本。

**参数**:
- `reason` (string): 显示原因，影响图标选择

**返回**: `string`

```javascript
const text = selector.generateStatusDisplay('user_request');
// 输出: "📍 当前空间: 🏠 主对话 (21k) · 输入 /sessions 切换\n\n"
```

#### `async updateActivity(userMessage)`
更新活动状态和话题关键词。

**参数**:
- `userMessage` (string): 用户消息，用于提取关键词

```javascript
await selector.updateActivity("我想讨论产品规划");
```

#### `async markStatusShown()`
标记已显示状态，用于冷却机制。

```javascript
await selector.markStatusShown();
```

#### `async switchSession(sessionId)`
切换到指定 session。

**参数**:
- `sessionId` (string): 要切换的 session ID

**返回**: `boolean` - 是否成功切换

```javascript
const success = await selector.switchSession('project');
```

#### `async createSession(name, description)`
创建新的 session。

**参数**:
- `name` (string): session 显示名称
- `description` (string): session 描述

**返回**: `string` - 新创建的 session ID

```javascript
const id = await selector.createSession('💰 财务分析', '讨论财务和投资');
```

## 独立函数

### `checkSessionStatus(userMessage)`
检查是否需要显示状态的便捷函数。

**参数**:
- `userMessage` (string): 用户消息

**返回**: `Promise<string|null>`
- 需要显示时返回状态文本
- 不需要显示时返回 `null`

```javascript
const { checkSessionStatus } = require('./scripts/check-session-status');

const statusText = await checkSessionStatus("我现在在哪？");
if (statusText) {
    console.log(statusText);
}
```

## 配置对象

### Session 对象结构
```javascript
{
  "name": "🏠 主对话",           // 显示名称
  "contextSize": 21,            // Context 大小 (k)
  "lastActivity": 1710188120,   // 最后活动时间戳
  "description": "日常对话和任务", // 描述文本
  "isEmpty": false              // 是否为空槽位
}
```

### State 文件结构
```javascript
{
  "sessions": {                 // 所有 session 映射
    "main": { /* session对象 */ },
    "slot_1": { /* session对象 */ }
  },
  "currentSession": "main",     // 当前活跃 session
  "lastActivity": 1710188120,   // 最后活动时间
  "lastTopicKeywords": [],      // 上次话题关键词
  "lastShowTime": 0             // 上次显示状态时间
}
```

## 错误处理

所有异步方法都使用 Promise，可以用 try-catch 捕获错误：

```javascript
try {
    await selector.updateActivity(userMessage);
    const status = selector.shouldShowStatus(userMessage);
    if (status) {
        console.log(selector.generateStatusDisplay(status));
        await selector.markStatusShown();
    }
} catch (error) {
    console.error('Session status check failed:', error);
    // 继续正常流程，不影响主要功能
}
```

## 性能注意事项

- 文件 I/O 操作（saveState/loadState）是异步的，避免频繁调用
- 关键词提取是简单字符串匹配，性能开销很小
- Session 状态文件通常 < 5KB，加载速度很快

## 扩展点

### 自定义关键词分类
```javascript
// 在 extractKeywords 方法中添加新的分类
const customWords = ['区块链', '智能合约', 'DeFi'];
if (customWords.some(word => text.includes(word))) {
    keywords.push('blockchain');
}
```

### 自定义触发条件
```javascript
// 在 shouldShowStatus 方法中添加新的检测逻辑
if (userMessage.includes('切换') && userMessage.includes('模式')) {
    return 'mode_switch';
}
```

### 自定义状态格式
```javascript
// 在 generateStatusDisplay 方法中修改显示格式
return `🎯 [${current?.name}] ${contextDisplay} | /sessions`;
```