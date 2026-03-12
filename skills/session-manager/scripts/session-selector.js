#!/usr/bin/env node

/**
 * Session Selector - Telegram 多对话框模拟器
 * 让用户在 Telegram 中选择不同的 session 空间
 */

const fs = require('fs').promises;
const path = require('path');

// Session 状态文件和配置文件  
const SESSION_STATE_FILE = path.join(__dirname, '..', '..', '..', 'memory', 'session-state.json');
const DEFAULT_CONFIG_FILE = path.join(__dirname, '..', 'config', 'default-sessions.json');

class SessionSelector {
    constructor() {
        this.sessions = new Map();
        this.currentSession = 'main';
        this.lastActivity = Date.now();
        this.lastTopicKeywords = [];
        this.lastShowTime = 0;
        this.config = this.getDefaultConfig();
        this.loadState();
    }

    getDefaultConfig() {
        return {
            settings: {
                maxSessions: 6,
                inactiveThreshold: 3600000,
                showCooldown: 1800000
            },
            keywords: {
                tech: ['代码', 'bug', '技术', 'API', 'token', 'session'],
                project: ['产品', '项目', '需求', '设计', '战略', '规划'],
                daily: ['吃饭', '天气', '心情', '时间', '生活']
            }
        };
    }

    async loadState() {
        try {
            const data = await fs.readFile(SESSION_STATE_FILE, 'utf8');
            const state = JSON.parse(data);
            this.sessions = new Map(Object.entries(state.sessions || {}));
            this.currentSession = state.currentSession || 'main';
            this.lastActivity = state.lastActivity || Date.now();
            this.lastTopicKeywords = state.lastTopicKeywords || [];
            this.lastShowTime = state.lastShowTime || 0;
            
            // 如果没有 sessions，初始化默认的
            if (this.sessions.size === 0) {
                this.initDefaultSessions();
                await this.saveState();
            }
        } catch (err) {
            // 初始化默认 sessions
            this.initDefaultSessions();
            await this.saveState();
        }
    }

    initDefaultSessions() {
        this.sessions.set('main', {
            name: '🏠 主对话',
            contextSize: 21,
            lastActivity: Date.now(),
            description: '日常对话和任务'
        });
        // 预留空位，由用户自己创建
        for (let i = 1; i <= 5; i++) {
            this.sessions.set(`slot_${i}`, {
                name: `➕ 新建 ${i}`,
                contextSize: 0,
                lastActivity: null,
                description: '点击创建新的对话空间',
                isEmpty: true
            });
        }
    }

    async saveState() {
        const state = {
            sessions: Object.fromEntries(this.sessions),
            currentSession: this.currentSession,
            lastActivity: this.lastActivity,
            lastTopicKeywords: this.lastTopicKeywords,
            lastShowTime: this.lastShowTime
        };
        await fs.mkdir(path.dirname(SESSION_STATE_FILE), { recursive: true });
        await fs.writeFile(SESSION_STATE_FILE, JSON.stringify(state, null, 2));
    }

    generateKeyboard() {
        const buttons = [];
        const sessionEntries = Array.from(this.sessions.entries());
        
        // 两列布局
        for (let i = 0; i < sessionEntries.length; i += 2) {
            const row = [];
            const [id1, session1] = sessionEntries[i];
            
            if (session1.isEmpty) {
                row.push({
                    text: session1.name,
                    callback_data: `create_${id1}`,
                    style: 'primary'
                });
            } else {
                row.push({
                    text: `${session1.name} ${id1 === this.currentSession ? '✓' : ''}`,
                    callback_data: `switch_${id1}`,
                    style: id1 === this.currentSession ? 'success' : 'primary'
                });
            }
            
            if (i + 1 < sessionEntries.length) {
                const [id2, session2] = sessionEntries[i + 1];
                
                if (session2.isEmpty) {
                    row.push({
                        text: session2.name,
                        callback_data: `create_${id2}`,
                        style: 'primary'
                    });
                } else {
                    row.push({
                        text: `${session2.name} ${id2 === this.currentSession ? '✓' : ''}`,
                        callback_data: `switch_${id2}`,
                        style: id2 === this.currentSession ? 'success' : 'primary'
                    });
                }
            }
            buttons.push(row);
        }

        // 管理按钮
        buttons.push([
            { text: '⚙️ 管理', callback_data: 'manage_sessions' }
        ]);

        return buttons;
    }

    generateSessionInfo() {
        const current = this.sessions.get(this.currentSession);
        const activeCount = Array.from(this.sessions.values()).filter(s => !s.isEmpty).length;
        
        let info = `📂 **Session 选择器**\n\n`;
        info += `当前空间: ${current?.name || '未知'}\n`;
        info += `活跃空间数: ${activeCount}/6\n\n`;

        // 显示所有 session 状态
        info += `**空间状态:**\n`;
        for (const [id, session] of this.sessions) {
            if (session.isEmpty) {
                info += `⚪ ${session.name} - 点击创建\n\n`;
            } else {
                const isActive = id === this.currentSession ? '🟢' : '⚪';
                const lastActivity = session.lastActivity ? 
                    new Date(session.lastActivity).toLocaleString('zh-CN') : 
                    '未使用';
                info += `${isActive} ${session.name}\n`;
                info += `   Context: ${session.contextSize}k | ${session.description}\n`;
                info += `   最后活动: ${lastActivity}\n\n`;
            }
        }

        return info;
    }

    async switchSession(sessionId) {
        if (this.sessions.has(sessionId)) {
            this.currentSession = sessionId;
            await this.saveState();
            return true;
        }
        return false;
    }

    async createSession(name, description) {
        const id = name.toLowerCase().replace(/[^a-z0-9]/g, '_');
        this.sessions.set(id, {
            name: name,
            contextSize: 0,
            lastActivity: Date.now(),
            description: description || '用户自定义空间'
        });
        await this.saveState();
        return id;
    }

    // 检测是否需要显示 session 状态
    shouldShowStatus(userMessage = '') {
        const now = Date.now();
        const timeSinceLastShow = now - this.lastShowTime;
        const timeSinceLastActivity = now - this.lastActivity;
        
        const settings = this.config?.settings || {};
        const inactiveThreshold = settings.inactiveThreshold || 3600000;
        const showCooldown = settings.showCooldown || 1800000;

        // 1. 用户主动询问
        if (/\/(session|where|status)/.test(userMessage) || 
            /在哪个|当前|现在.*session|空间/.test(userMessage)) {
            return 'user_request';
        }

        // 2. 长时间无活动
        if (timeSinceLastActivity > inactiveThreshold && timeSinceLastShow > inactiveThreshold) {
            return 'long_inactive';
        }

        // 3. 话题可能跳转 (简单关键词检测)
        const currentKeywords = this.extractKeywords(userMessage);
        if (this.lastTopicKeywords.length > 0 && currentKeywords.length > 0) {
            const overlap = currentKeywords.filter(k => this.lastTopicKeywords.includes(k));
            if (overlap.length === 0 && timeSinceLastShow > showCooldown) {
                return 'topic_change';
            }
        }

        return false;
    }

    // 简单关键词提取
    extractKeywords(text) {
        const keywords = [];
        const keywordCategories = this.config?.keywords || {};
        
        for (const [category, words] of Object.entries(keywordCategories)) {
            for (const word of words) {
                if (text.includes(word)) {
                    keywords.push(word);
                }
            }
        }
        
        return keywords;
    }

    // 生成状态显示文本
    generateStatusDisplay(reason = '') {
        const current = this.sessions.get(this.currentSession);
        const contextDisplay = current?.contextSize ? `${current.contextSize}k` : '0k';
        
        let prefix = '';
        switch (reason) {
            case 'user_request':
                prefix = '📍 ';
                break;
            case 'long_inactive':
                prefix = '👋 ';
                break;
            case 'topic_change':
                prefix = '🔄 ';
                break;
            default:
                prefix = '📍 ';
        }

        return `${prefix}当前空间: ${current?.name || '未知'} (${contextDisplay}) · 输入 /sessions 切换\n\n`;
    }

    // 更新活动状态
    async updateActivity(userMessage = '') {
        this.lastActivity = Date.now();
        this.lastTopicKeywords = this.extractKeywords(userMessage);
        await this.saveState();
    }

    // 标记已显示状态
    async markStatusShown() {
        this.lastShowTime = Date.now();
        await this.saveState();
    }
}

module.exports = { SessionSelector };

// CLI 使用
if (require.main === module) {
    const selector = new SessionSelector();
    
    // 处理命令行参数
    const args = process.argv.slice(2);
    const command = args[0];
    
    switch (command) {
        case 'check':
            const userMessage = args[1] || '';
            selector.updateActivity(userMessage);
            const shouldShow = selector.shouldShowStatus(userMessage);
            if (shouldShow) {
                console.log(selector.generateStatusDisplay(shouldShow));
                selector.markStatusShown();
            } else {
                console.log('NO_STATUS_NEEDED');
            }
            break;
            
        case 'status':
            console.log(selector.generateStatusDisplay('user_request'));
            selector.markStatusShown();
            break;
            
        case 'keyboard':
            console.log(JSON.stringify(selector.generateKeyboard(), null, 2));
            break;
            
        default:
            console.log(selector.generateSessionInfo());
    }
}