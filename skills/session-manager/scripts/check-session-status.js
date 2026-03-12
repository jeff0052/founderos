#!/usr/bin/env node

/**
 * Session Status Checker
 * 在回复前检查是否需要显示当前 session 状态
 */

const { SessionSelector } = require('./session-selector');

async function checkSessionStatus(userMessage = '') {
    try {
        const selector = new SessionSelector();
        await selector.updateActivity(userMessage);
        
        const shouldShow = selector.shouldShowStatus(userMessage);
        
        if (shouldShow) {
            const statusText = selector.generateStatusDisplay(shouldShow);
            await selector.markStatusShown();
            return statusText;
        }
        
        return null;
    } catch (error) {
        console.error('Session status check failed:', error.message);
        return null;
    }
}

// 导出函数供其他脚本使用
module.exports = { checkSessionStatus };

// CLI 使用
if (require.main === module) {
    const userMessage = process.argv[2] || '';
    
    checkSessionStatus(userMessage).then(result => {
        if (result) {
            console.log(result);
        } else {
            console.log(''); // 空输出，无需显示状态
        }
    }).catch(error => {
        console.error('Error:', error.message);
        process.exit(1);
    });
}