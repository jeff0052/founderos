# Session Manager 使用示例

## 基础使用

### 1. 显示 Session 选择器

```javascript
const { SessionSelector } = require('./scripts/session-selector');

async function showSessionSelector() {
    const selector = new SessionSelector();
    const info = selector.generateSessionInfo();
    const keyboard = selector.generateKeyboard();
    
    // 发送带按钮的消息
    await message.send({
        text: info,
        buttons: keyboard
    });
}

// 使用
showSessionSelector();
```

### 2. 智能状态检查

```javascript
const { checkSessionStatus } = require('./scripts/check-session-status');

async function smartReply(userMessage) {
    // 检查是否需要显示状态
    const statusText = await checkSessionStatus(userMessage);
    
    // 生成主要回复
    const mainReply = generateMainReply(userMessage);
    
    // 组合最终回复
    return statusText ? statusText + mainReply : mainReply;
}

// 示例对话
await smartReply("好的，谢谢");          // 不显示状态
await smartReply("我现在在哪个session？"); // 显示状态
```

## 实际场景

### 场景1：项目讨论专用空间

```javascript
// 用户点击 "新建1" 按钮后的处理
async function handleCreateSession(slotId, userInput) {
    const selector = new SessionSelector();
    
    // 解析用户输入
    const [name, description] = parseSessionInput(userInput);
    // "项目讨论 | 产品规划和战略决策"
    
    // 创建新 session
    const sessionId = await selector.createSession(name, description);
    
    // 切换到新 session
    await selector.switchSession(sessionId);
    
    // 确认切换成功
    const status = selector.generateStatusDisplay('switch_confirm');
    return `${status}欢迎来到 ${name} 空间！可以开始讨论了。`;
}

function parseSessionInput(input) {
    const parts = input.split('|');
    const name = `📋 ${parts[0].trim()}`;
    const description = parts[1]?.trim() || '用户自定义空间';
    return [name, description];
}
```

### 场景2：话题自动检测

```javascript
// 监听用户消息，自动检测话题跳转
async function onUserMessage(userMessage) {
    const selector = new SessionSelector();
    
    // 更新活动状态
    await selector.updateActivity(userMessage);
    
    // 检查是否需要提醒
    const shouldShow = selector.shouldShowStatus(userMessage);
    
    if (shouldShow === 'topic_change') {
        // 检测到话题跳转，建议切换
        const status = selector.generateStatusDisplay('topic_change');
        const suggestion = suggestSession(userMessage);
        
        return status + suggestion + generateReply(userMessage);
    }
    
    return generateReply(userMessage);
}

function suggestSession(userMessage) {
    if (userMessage.includes('代码') || userMessage.includes('bug')) {
        return "💡 检测到技术话题，建议切换到技术支持空间。输入 /sessions 选择。\n\n";
    }
    if (userMessage.includes('产品') || userMessage.includes('需求')) {
        return "💡 检测到项目话题，建议切换到项目讨论空间。\n\n";
    }
    return "";
}
```

### 场景3：长时间无活动提醒

```javascript
// Heartbeat 或定时任务中检查
async function checkInactiveUsers() {
    const selector = new SessionSelector();
    
    const now = Date.now();
    const lastActivity = selector.lastActivity;
    const timeDiff = now - lastActivity;
    
    // 超过2小时无活动
    if (timeDiff > 7200000) {
        const status = selector.generateStatusDisplay('long_inactive');
        await message.send({
            text: `👋 好久不见！\n\n${status}有什么可以帮你的吗？`,
            silent: true  // 静默发送，不打扰
        });
        
        await selector.markStatusShown();
    }
}
```

## 高级集成

### 与消息路由结合

```javascript
class MessageRouter {
    constructor() {
        this.selector = new SessionSelector();
    }
    
    async route(userMessage) {
        // 检查状态显示需求
        const statusText = await this.checkStatus(userMessage);
        
        // 根据当前 session 路由到不同处理器
        const currentSession = this.selector.currentSession;
        const handler = this.getHandler(currentSession);
        
        // 生成回复
        const reply = await handler.process(userMessage);
        
        // 组合最终消息
        return statusText + reply;
    }
    
    async checkStatus(userMessage) {
        const { checkSessionStatus } = require('./scripts/check-session-status');
        return await checkSessionStatus(userMessage) || '';
    }
    
    getHandler(sessionId) {
        const handlers = {
            'main': new GeneralHandler(),
            'tech': new TechSupportHandler(), 
            'project': new ProjectHandler(),
            'writing': new WritingHandler()
        };
        
        return handlers[sessionId] || handlers['main'];
    }
}
```

### 与 Context 管理结合

```javascript
async function manageContext(userMessage) {
    const selector = new SessionSelector();
    
    // 更新当前 session 的 context 大小
    const currentContext = await getCurrentContextSize();
    const current = selector.sessions.get(selector.currentSession);
    if (current) {
        current.contextSize = Math.round(currentContext / 1000); // 转换为 k
        await selector.saveState();
    }
    
    // 检查是否需要警告 context 过大
    if (currentContext > 100000) {
        const status = selector.generateStatusDisplay('context_warning');
        const warning = "⚠️ Context 已达 100k+，建议切换到新空间避免限流。\n\n";
        return status + warning;
    }
    
    // 正常的状态检查
    return await checkSessionStatus(userMessage) || '';
}
```

## 命令行工具

### 批量管理 Sessions

```bash
#!/bin/bash
# scripts/session-tools.sh

# 显示所有 sessions
show_all() {
    node scripts/session-selector.js
}

# 清理空 sessions
cleanup_empty() {
    node -e "
    const {SessionSelector} = require('./scripts/session-selector');
    const selector = new SessionSelector();
    
    for (const [id, session] of selector.sessions) {
        if (session.isEmpty) {
            selector.sessions.delete(id);
        }
    }
    
    selector.saveState();
    console.log('Cleaned up empty sessions');
    "
}

# 重置所有 context 大小
reset_context() {
    node -e "
    const {SessionSelector} = require('./scripts/session-selector');
    const selector = new SessionSelector();
    
    for (const [id, session] of selector.sessions) {
        session.contextSize = 0;
    }
    
    selector.saveState();
    console.log('Reset all context sizes');
    "
}

case $1 in
    show) show_all ;;
    cleanup) cleanup_empty ;;
    reset) reset_context ;;
    *) echo "Usage: $0 {show|cleanup|reset}" ;;
esac
```

### 状态监控脚本

```bash
#!/bin/bash
# scripts/session-monitor.sh

# 持续监控 session 状态
monitor() {
    while true; do
        echo "=== $(date) ==="
        node scripts/session-selector.js status
        echo "Context check needed: $(node scripts/check-session-status.js '')"
        echo ""
        sleep 300  # 每5分钟检查一次
    done
}

# 一次性状态报告
report() {
    echo "Session Manager Status Report"
    echo "============================="
    echo "Current time: $(date)"
    echo ""
    
    node scripts/session-selector.js
    echo ""
    
    echo "Recent activity:"
    cat memory/session-state.json | jq '.lastActivity, .lastTopicKeywords'
}

case $1 in
    monitor) monitor ;;
    report) report ;;
    *) echo "Usage: $0 {monitor|report}" ;;
esac
```

## 测试示例

```javascript
// test-session-manager.js
const { SessionSelector } = require('./scripts/session-selector');
const { checkSessionStatus } = require('./scripts/check-session-status');

async function runTests() {
    console.log('Testing Session Manager...');
    
    // 测试1：基础功能
    const selector = new SessionSelector();
    console.log('✓ SessionSelector created');
    
    // 测试2：状态检查
    let status = await checkSessionStatus("正常对话");
    console.log('Normal chat status:', status || 'none');
    
    status = await checkSessionStatus("/session");
    console.log('User request status:', status ? 'shown' : 'failed');
    
    // 测试3：创建 session
    const newId = await selector.createSession('🧪 测试', '测试专用空间');
    console.log('✓ Created test session:', newId);
    
    // 测试4：切换 session
    const switched = await selector.switchSession(newId);
    console.log('✓ Switched to test session:', switched);
    
    // 测试5：生成界面
    const keyboard = selector.generateKeyboard();
    const info = selector.generateSessionInfo();
    console.log('✓ Generated UI components');
    
    console.log('All tests passed!');
}

runTests().catch(console.error);
```

运行测试：
```bash
cd skills/session-manager
node test-session-manager.js
```