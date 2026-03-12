#!/usr/bin/env node

/**
 * Session Manager 集成助手
 * 提供简单的 API 供其他脚本调用
 */

const { SessionSelector } = require('./session-selector');
const { checkSessionStatus } = require('./check-session-status');

/**
 * 主要集成函数：在回复前检查是否需要显示状态
 */
async function beforeReply(userMessage = '', options = {}) {
    try {
        const statusText = await checkSessionStatus(userMessage);
        
        return {
            needsStatus: !!statusText,
            statusText: statusText || '',
            sessionInfo: await getCurrentSessionInfo()
        };
    } catch (error) {
        console.error('Session Manager error:', error);
        return {
            needsStatus: false,
            statusText: '',
            error: error.message
        };
    }
}

/**
 * 获取当前 session 信息
 */
async function getCurrentSessionInfo() {
    const selector = new SessionSelector();
    await selector.loadState(); // 确保状态已加载
    const current = selector.sessions.get(selector.currentSession);
    
    return {
        id: selector.currentSession,
        name: current?.name || '未知',
        description: current?.description || '',
        contextSize: current?.contextSize || 0,
        lastActivity: current?.lastActivity || 0
    };
}

/**
 * 强制显示 session 选择器
 */
async function showSessionSelector() {
    const selector = new SessionSelector();
    await selector.loadState(); // 确保状态已加载
    
    return {
        text: selector.generateSessionInfo(),
        buttons: selector.generateKeyboard(),
        currentSession: await getCurrentSessionInfo()
    };
}

/**
 * 处理 session 切换回调
 */
async function handleSessionCallback(callbackData, userContext = {}) {
    const selector = new SessionSelector();
    
    if (callbackData.startsWith('switch_')) {
        const sessionId = callbackData.replace('switch_', '');
        const success = await selector.switchSession(sessionId);
        
        if (success) {
            const status = selector.generateStatusDisplay('switch_confirm');
            const sessionInfo = await getCurrentSessionInfo();
            
            return {
                success: true,
                message: `${status}已切换到 ${sessionInfo.name}`,
                sessionInfo: sessionInfo
            };
        } else {
            return {
                success: false,
                message: '切换失败，session 不存在'
            };
        }
    }
    
    if (callbackData.startsWith('create_')) {
        const slotId = callbackData.replace('create_', '');
        
        return {
            success: true,
            action: 'request_session_info',
            message: '请提供新空间的信息：\n\n' +
                    '**格式**：名称 | 描述\n' +
                    '**示例**：项目讨论 | 产品规划和战略决策\n\n' +
                    '或者选择模板：\n' +
                    '1. 📋 项目讨论\n' +
                    '2. 🔧 技术支持\n' +
                    '3. ✍️ 文档写作\n' +
                    '4. 💰 财务分析\n' +
                    '5. 🔍 研究调研',
            slotId: slotId
        };
    }
    
    return {
        success: false,
        message: '未知的回调操作'
    };
}

/**
 * 创建新 session
 */
async function createSession(name, description, slotId = null) {
    const selector = new SessionSelector();
    
    try {
        // 如果提供了 slotId，替换对应的空槽位
        if (slotId && selector.sessions.has(slotId)) {
            const slot = selector.sessions.get(slotId);
            slot.name = name;
            slot.description = description;
            slot.isEmpty = false;
            slot.lastActivity = Date.now();
            slot.contextSize = 0;
            
            await selector.saveState();
            
            return {
                success: true,
                sessionId: slotId,
                message: `✅ 已创建 ${name} 空间`
            };
        } else {
            // 创建全新的 session
            const sessionId = await selector.createSession(name, description);
            
            return {
                success: true,
                sessionId: sessionId,
                message: `✅ 已创建 ${name} 空间`
            };
        }
    } catch (error) {
        return {
            success: false,
            error: error.message,
            message: '创建空间失败'
        };
    }
}

/**
 * 更新当前 session 的 context 大小
 */
async function updateSessionContext(contextSize) {
    const selector = new SessionSelector();
    const current = selector.sessions.get(selector.currentSession);
    
    if (current) {
        current.contextSize = Math.round(contextSize / 1000); // 转换为 k
        await selector.saveState();
        
        // 检查是否需要警告
        if (contextSize > 100000) {
            return {
                warning: true,
                message: '⚠️ Context 已达 100k+，建议切换到新空间避免限流'
            };
        }
    }
    
    return { warning: false };
}

/**
 * 中间件模式：包装原始回复函数
 */
function withSessionManager(originalReplyFunction) {
    return async (userMessage, ...args) => {
        // 检查是否需要显示状态
        const { needsStatus, statusText } = await beforeReply(userMessage);
        
        // 生成原始回复
        const originalReply = await originalReplyFunction(userMessage, ...args);
        
        // 组合最终回复
        return needsStatus ? statusText + originalReply : originalReply;
    };
}

/**
 * Express 中间件版本
 */
function expressMiddleware(req, res, next) {
    req.sessionManager = {
        beforeReply: beforeReply,
        showSelector: showSessionSelector,
        handleCallback: handleSessionCallback,
        createSession: createSession,
        updateContext: updateSessionContext,
        getCurrentInfo: getCurrentSessionInfo
    };
    
    next();
}

// 导出所有功能
module.exports = {
    beforeReply,
    getCurrentSessionInfo,
    showSessionSelector,
    handleSessionCallback,
    createSession,
    updateSessionContext,
    withSessionManager,
    expressMiddleware
};

// CLI 使用示例
if (require.main === module) {
    const command = process.argv[2];
    const args = process.argv.slice(3);
    
    switch (command) {
        case 'check':
            beforeReply(args[0] || '').then(result => {
                console.log(JSON.stringify(result, null, 2));
            });
            break;
            
        case 'selector':
            showSessionSelector().then(result => {
                console.log('Text:', result.text);
                console.log('Buttons:', JSON.stringify(result.buttons, null, 2));
            });
            break;
            
        case 'info':
            getCurrentSessionInfo().then(info => {
                console.log(JSON.stringify(info, null, 2));
            });
            break;
            
        case 'create':
            const name = args[0];
            const description = args[1] || '';
            createSession(name, description).then(result => {
                console.log(JSON.stringify(result, null, 2));
            });
            break;
            
        default:
            console.log('Usage: node integration.js <command> [args...]');
            console.log('Commands:');
            console.log('  check [message]    - Check if status should be shown');
            console.log('  selector          - Get session selector UI');
            console.log('  info             - Get current session info');
            console.log('  create <name> [desc] - Create new session');
    }
}