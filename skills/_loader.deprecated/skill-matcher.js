#!/usr/bin/env node

/**
 * Skill Matcher - 第一阶段轻量匹配器
 * 不加载完整skill描述，仅基于注册表进行快速匹配
 */

const fs = require('fs').promises;
const path = require('path');

class SkillMatcher {
    constructor() {
        this.registry = null;
        this.cache = new Map();
        this.stats = {
            totalMatches: 0,
            cacheHits: 0,
            avgConfidence: 0
        };
    }
    
    async init() {
        if (!this.registry) {
            await this.loadRegistry();
        }
    }
    
    async loadRegistry() {
        try {
            const registryPath = path.join(__dirname, 'skill-registry.json');
            const data = await fs.readFile(registryPath, 'utf8');
            this.registry = JSON.parse(data);
            
            if (this.registry.settings.logMatching) {
                console.log(`📋 Loaded ${Object.keys(this.registry.skills).length} skills for matching`);
            }
        } catch (err) {
            console.error('❌ Failed to load skill registry:', err.message);
            this.registry = { 
                skills: {}, 
                fallback: ['self-improvement'],
                settings: {
                    maxConcurrentSkills: 2,
                    confidenceThreshold: 0.5,
                    enableAutoLoad: false
                }
            };
        }
    }
    
    /**
     * 主匹配函数：轻量级判断是否需要技能
     */
    async matchSkills(userMessage, options = {}) {
        await this.init();
        
        // 缓存检查
        const cacheKey = userMessage.toLowerCase().trim();
        if (this.registry.settings.enableCaching && this.cache.has(cacheKey)) {
            this.stats.cacheHits++;
            return this.cache.get(cacheKey);
        }
        
        const normalizedMessage = this.normalizeMessage(userMessage);
        const matches = [];
        
        // 遍历所有技能进行匹配
        for (const [skillName, skillConfig] of Object.entries(this.registry.skills)) {
            // 跳过被禁用的技能
            if (options.disabledSkills?.includes(skillName)) continue;
            
            const confidence = await this.calculateSkillConfidence(normalizedMessage, skillConfig, skillName);
            
            if (confidence >= this.registry.settings.confidenceThreshold) {
                matches.push({
                    skill: skillName,
                    confidence: confidence,
                    category: skillConfig.category,
                    priority: skillConfig.priority || 5,
                    reason: this.getMatchReason(normalizedMessage, skillConfig),
                    alwaysLoad: skillConfig.alwaysLoad || false
                });
            }
        }
        
        // 应用排序和过滤策略
        const selectedSkills = this.selectOptimalSkills(matches, options);
        
        // 添加fallback技能
        const fallbackSkills = this.getFallbackSkills(selectedSkills);
        
        const result = {
            primary: selectedSkills,
            fallback: fallbackSkills,
            totalCandidates: matches.length,
            processingMode: selectedSkills.length > 0 ? 'skill' : 'direct',
            confidence: this.calculateOverallConfidence(selectedSkills),
            strategy: this.determineProcessingStrategy(selectedSkills, normalizedMessage),
            tokenEstimate: this.estimateTokenUsage(selectedSkills),
            timestamp: Date.now()
        };
        
        // 更新统计和缓存
        this.updateStats(result);
        if (this.registry.settings.enableCaching) {
            this.cache.set(cacheKey, result);
        }
        
        return result;
    }
    
    /**
     * 规范化用户消息
     */
    normalizeMessage(message) {
        return {
            original: message,
            lowercase: message.toLowerCase(),
            words: message.toLowerCase().split(/\s+/),
            length: message.length,
            hasCommand: message.startsWith('/'),
            hasQuestion: message.includes('?') || message.includes('？'),
            language: this.detectLanguage(message)
        };
    }
    
    /**
     * 计算单个技能的匹配置信度
     */
    async calculateSkillConfidence(normalizedMsg, skillConfig, skillName) {
        let totalScore = 0;
        let weightSum = 0;
        
        const strategies = this.registry.matchingStrategies;
        
        // 1. 精确关键词匹配
        if (strategies.exactKeyword && skillConfig.triggers) {
            const keywordScore = this.calculateKeywordScore(normalizedMsg, skillConfig.triggers);
            totalScore += keywordScore * strategies.exactKeyword.weight;
            weightSum += strategies.exactKeyword.weight;
        }
        
        // 2. 正则模式匹配  
        if (strategies.patternMatch && skillConfig.patterns) {
            const patternScore = this.calculatePatternScore(normalizedMsg, skillConfig.patterns);
            totalScore += patternScore * strategies.patternMatch.weight;
            weightSum += strategies.patternMatch.weight;
        }
        
        // 3. 频率和优先级加权
        if (strategies.frequencyBonus) {
            const frequencyBonus = strategies.frequencyBonus.values[skillConfig.frequency] || 0;
            totalScore += frequencyBonus * strategies.frequencyBonus.weight;
            weightSum += strategies.frequencyBonus.weight;
        }
        
        // 4. 上下文相关性检查
        const contextScore = await this.calculateContextScore(normalizedMsg, skillConfig, skillName);
        totalScore += contextScore * 0.1;
        weightSum += 0.1;
        
        // 5. 特殊条件检查
        if (!this.checkSpecialConditions(skillConfig, normalizedMsg)) {
            return 0; // 条件不满足，直接返回0
        }
        
        // 计算最终置信度
        const baseConfidence = weightSum > 0 ? totalScore / weightSum : 0;
        
        // 优先级加权
        const priorityMultiplier = this.registry.settings.priorityWeighting 
            ? (skillConfig.priority || 5) / 10 
            : 1;
            
        return Math.min(baseConfidence * priorityMultiplier, 1.0);
    }
    
    /**
     * 关键词匹配评分
     */
    calculateKeywordScore(normalizedMsg, triggers) {
        const matches = triggers.filter(trigger => 
            normalizedMsg.lowercase.includes(trigger.toLowerCase())
        );
        
        return matches.length / triggers.length;
    }
    
    /**
     * 正则模式匹配评分
     */
    calculatePatternScore(normalizedMsg, patterns) {
        let matchCount = 0;
        
        for (const pattern of patterns) {
            try {
                const regex = new RegExp(pattern, 'i');
                if (regex.test(normalizedMsg.original)) {
                    matchCount++;
                }
            } catch (err) {
                console.warn(`⚠️ Invalid regex pattern: ${pattern}`);
            }
        }
        
        return patterns.length > 0 ? matchCount / patterns.length : 0;
    }
    
    /**
     * 上下文相关性评分
     */
    async calculateContextScore(normalizedMsg, skillConfig, skillName) {
        // 检查消息长度和复杂度匹配
        const complexityMatch = this.checkComplexityMatch(normalizedMsg, skillConfig.complexity);
        
        // 检查类别相关性
        const categoryRelevance = this.checkCategoryRelevance(normalizedMsg, skillConfig.category);
        
        // 检查是否是直接命名调用
        const directCall = normalizedMsg.lowercase.includes(skillName.toLowerCase()) ? 0.3 : 0;
        
        return (complexityMatch + categoryRelevance + directCall) / 3;
    }
    
    /**
     * 复杂度匹配检查
     */
    checkComplexityMatch(normalizedMsg, complexity) {
        const messageComplexity = this.assessMessageComplexity(normalizedMsg);
        
        const complexityMap = {
            'low': 1,
            'medium': 2, 
            'high': 3,
            'very_high': 4
        };
        
        const msgLevel = complexityMap[messageComplexity] || 2;
        const skillLevel = complexityMap[complexity] || 2;
        
        // 相差越小匹配度越高
        const diff = Math.abs(msgLevel - skillLevel);
        return Math.max(0, 1 - diff * 0.25);
    }
    
    /**
     * 评估消息复杂度
     */
    assessMessageComplexity(normalizedMsg) {
        const wordCount = normalizedMsg.words.length;
        const hasMultipleRequests = normalizedMsg.original.includes('和') || normalizedMsg.original.includes(',');
        const hasSpecificFormat = /PDF|格式|样式|模板/.test(normalizedMsg.original);
        
        if (wordCount > 20 || hasMultipleRequests) return 'very_high';
        if (wordCount > 10 || hasSpecificFormat) return 'high';
        if (wordCount > 5) return 'medium';
        return 'low';
    }
    
    /**
     * 类别相关性检查
     */
    checkCategoryRelevance(normalizedMsg, category) {
        const categoryKeywords = {
            'system': ['配置', '设置', '系统', '管理'],
            'document': ['文档', '文件', '报告', '记录'],
            'media': ['音频', '视频', '图片', '媒体'],
            'content': ['内容', '创作', '写作', '文章'],
            'search': ['搜索', '查找', '寻找', '检索']
        };
        
        const keywords = categoryKeywords[category] || [];
        const matches = keywords.filter(keyword => 
            normalizedMsg.lowercase.includes(keyword)
        );
        
        return keywords.length > 0 ? matches.length / keywords.length : 0;
    }
    
    /**
     * 特殊条件检查
     */
    checkSpecialConditions(skillConfig, normalizedMsg) {
        if (!skillConfig.conditions) return true;
        
        for (const condition of skillConfig.conditions) {
            switch (condition) {
                case 'web_search_unavailable':
                    // 检查是否明确提到备用搜索需求
                    if (!normalizedMsg.lowercase.includes('tavily') && 
                        !normalizedMsg.lowercase.includes('备用')) {
                        return false;
                    }
                    break;
                // 可以添加更多条件
            }
        }
        
        return true;
    }
    
    /**
     * 选择最优技能组合
     */
    selectOptimalSkills(matches, options) {
        // 按置信度和优先级排序
        matches.sort((a, b) => {
            if (a.alwaysLoad && !b.alwaysLoad) return -1;
            if (!a.alwaysLoad && b.alwaysLoad) return 1;
            
            const scoreA = a.confidence + (a.priority / 100);
            const scoreB = b.confidence + (b.priority / 100);
            
            return scoreB - scoreA;
        });
        
        const maxSkills = options.maxSkills || this.registry.settings.maxConcurrentSkills;
        
        // 确保alwaysLoad的技能被包含
        const alwaysLoadSkills = matches.filter(m => m.alwaysLoad);
        const otherSkills = matches.filter(m => !m.alwaysLoad).slice(0, maxSkills - alwaysLoadSkills.length);
        
        return [...alwaysLoadSkills, ...otherSkills].slice(0, maxSkills);
    }
    
    /**
     * 获取fallback技能
     */
    getFallbackSkills(selectedSkills) {
        const selectedNames = selectedSkills.map(s => s.skill);
        return this.registry.fallback.filter(skill => !selectedNames.includes(skill));
    }
    
    /**
     * 计算整体置信度
     */
    calculateOverallConfidence(selectedSkills) {
        if (selectedSkills.length === 0) return 0;
        
        const totalConfidence = selectedSkills.reduce((sum, skill) => sum + skill.confidence, 0);
        return totalConfidence / selectedSkills.length;
    }
    
    /**
     * 确定处理策略
     */
    determineProcessingStrategy(selectedSkills, normalizedMsg) {
        if (selectedSkills.length === 0) {
            return 'direct_reply';
        }
        
        if (selectedSkills.length === 1) {
            return 'single_skill';
        }
        
        if (selectedSkills.some(s => s.category === 'system')) {
            return 'system_priority';
        }
        
        return 'multi_skill';
    }
    
    /**
     * 估算token使用量
     */
    estimateTokenUsage(selectedSkills) {
        const baseTokensPerSkill = 150; // 平均每个skill描述的token数
        const systemOverhead = 50; // 系统开销
        
        return selectedSkills.length * baseTokensPerSkill + systemOverhead;
    }
    
    /**
     * 获取匹配原因
     */
    getMatchReason(normalizedMsg, skillConfig) {
        const triggeredKeywords = skillConfig.triggers?.filter(trigger => 
            normalizedMsg.lowercase.includes(trigger.toLowerCase())
        ) || [];
        
        const matchedPatterns = skillConfig.patterns?.filter(pattern => {
            try {
                return new RegExp(pattern, 'i').test(normalizedMsg.original);
            } catch {
                return false;
            }
        }) || [];
        
        return {
            keywords: triggeredKeywords,
            patterns: matchedPatterns,
            category: skillConfig.category,
            priority: skillConfig.priority,
            confidence: 'calculated'
        };
    }
    
    /**
     * 语言检测
     */
    detectLanguage(message) {
        const chinesePattern = /[\u4e00-\u9fff]/;
        const hasChinese = chinesePattern.test(message);
        const hasEnglish = /[a-zA-Z]/.test(message);
        
        if (hasChinese && hasEnglish) return 'mixed';
        if (hasChinese) return 'chinese';
        if (hasEnglish) return 'english';
        return 'unknown';
    }
    
    /**
     * 更新统计信息
     */
    updateStats(result) {
        this.stats.totalMatches++;
        if (result.primary.length > 0) {
            this.stats.avgConfidence = (this.stats.avgConfidence * (this.stats.totalMatches - 1) + result.confidence) / this.stats.totalMatches;
        }
    }
    
    /**
     * 获取统计信息
     */
    getStats() {
        return {
            ...this.stats,
            cacheSize: this.cache.size,
            cacheHitRate: this.stats.totalMatches > 0 ? this.stats.cacheHits / this.stats.totalMatches : 0
        };
    }
    
    /**
     * 清理缓存
     */
    clearCache() {
        this.cache.clear();
        console.log('🧹 Skill matcher cache cleared');
    }
}

module.exports = { SkillMatcher };

// CLI 使用
if (require.main === module) {
    const matcher = new SkillMatcher();
    const command = process.argv[2];
    const message = process.argv[3] || '';
    
    async function runCommand() {
        switch (command) {
            case 'match':
                const result = await matcher.matchSkills(message);
                console.log(JSON.stringify(result, null, 2));
                break;
                
            case 'stats':
                await matcher.init();
                console.log(JSON.stringify(matcher.getStats(), null, 2));
                break;
                
            case 'test':
                const testCases = [
                    "帮我生成一个PDF",
                    "今天天气怎样？",
                    "转录这个语音文件", 
                    "我现在在哪个session？",
                    "写一篇文章"
                ];
                
                console.log('🧪 Testing skill matching...\n');
                for (const testMsg of testCases) {
                    const result = await matcher.matchSkills(testMsg);
                    console.log(`📝 "${testMsg}"`);
                    console.log(`   Mode: ${result.processingMode}`);
                    console.log(`   Skills: ${result.primary.map(s => s.skill).join(', ') || 'none'}`);
                    console.log(`   Confidence: ${result.confidence.toFixed(2)}\n`);
                }
                break;
                
            default:
                console.log('Usage: node skill-matcher.js <command> [message]');
                console.log('Commands:');
                console.log('  match <message>  - Match skills for message');
                console.log('  stats           - Show matching statistics');
                console.log('  test            - Run test cases');
        }
    }
    
    runCommand().catch(console.error);
}