#!/usr/bin/env node

/**
 * 简单的话题切换检查器
 * 检测是否应该建议开新 session
 */

const fs = require('fs');
const path = require('path');

// 简单的关键词检测
function extractKeywords(text) {
    const techKeywords = ['API', '代码', 'bug', '数据库', '系统', '部署', '配置'];
    const businessKeywords = ['合作', '谈判', '商务', '价格', '协议', '客户', '市场'];
    const personalKeywords = ['薪水', '个人', '生活', '健康', '时间', '计划'];
    
    const found = {
        tech: techKeywords.filter(k => text.includes(k)),
        business: businessKeywords.filter(k => text.includes(k)),
        personal: personalKeywords.filter(k => text.includes(k))
    };
    
    return found;
}

function shouldSuggestSwitch(userMessage, contextSize = 0) {
    // 明确的切换请求
    const switchTriggers = [
        '换个话题', '新问题', '另外一个', '还有个事', 
        '顺便问', '对了', '再问', '新的问题'
    ];
    
    if (switchTriggers.some(trigger => userMessage.includes(trigger))) {
        return {
            should: true,
            reason: '检测到话题切换意图',
            priority: 'high'
        };
    }
    
    // Context 过大
    if (contextSize > 80000) {
        return {
            should: true,
            reason: `Context 已达 ${Math.round(contextSize/1000)}k，建议切换避免限流`,
            priority: 'high'
        };
    }
    
    if (contextSize > 50000) {
        return {
            should: true,
            reason: `Context 已达 ${Math.round(contextSize/1000)}k，考虑切换话题`,
            priority: 'medium'
        };
    }
    
    return {
        should: false,
        reason: '暂无切换建议'
    };
}

function generateSwitchSuggestion(analysis) {
    if (!analysis.should) return '';
    
    const suggestions = [
        '💡 **话题切换建议**',
        `📊 ${analysis.reason}`,
        '',
        '🚀 **选择**:',
        '• 继续当前对话',
        '• `/new` 开新话题讨论',
        ''
    ];
    
    return suggestions.join('\n');
}

// CLI 使用
if (require.main === module) {
    const userMessage = process.argv[2] || '';
    const contextSize = parseInt(process.argv[3] || '0');
    
    const analysis = shouldSuggestSwitch(userMessage, contextSize);
    
    if (analysis.should) {
        console.log(generateSwitchSuggestion(analysis));
    } else {
        console.log(''); // 无建议时返回空
    }
}

module.exports = {
    shouldSuggestSwitch,
    generateSwitchSuggestion,
    extractKeywords
};