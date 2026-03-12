#!/usr/bin/env node

/**
 * Smart Skill System - 智能技能系统集成接口
 * 提供简单的API来替代传统的全量skill加载
 */

const { SkillLoader } = require('./skill-loader');
const fs = require('fs').promises;
const path = require('path');

class SmartSkillSystem {
    constructor(options = {}) {
        this.loader = new SkillLoader();
        this.config = {
            enableOptimization: options.enableOptimization !== false,
            logPerformance: options.logPerformance || false,
            cacheResults: options.cacheResults !== false,
            fallbackToTraditional: options.fallbackToTraditional || false,
            debugMode: options.debugMode || false
        };
        
        this.sessionCache = new Map();
        this.globalStats = {
            totalRequests: 0,
            optimizedRequests: 0,
            traditionalRequests: 0,
            totalTokensSaved: 0,
            averageResponseTime: 0,
            errorRate: 0
        };
    }
    
    async init() {
        await this.loader.init();
        if (this.config.logPerformance) {
            console.log('🚀 Smart Skill System initialized');
        }
    }
    
    /**
     * 主要接口：智能获取技能描述
     * 这个函数可以直接替代原有的skill描述注入逻辑
     */
    async getRelevantSkills(userMessage, sessionId = 'default', options = {}) {
        const startTime = Date.now();
        this.globalStats.totalRequests++;
        
        try {
            await this.init();
            
            // 检查是否启用优化
            if (!this.config.enableOptimization) {
                return await this.traditionaltLoad();
            }
            
            // 智能加载
            const result = await this.loader.smartLoad(userMessage, options);
            const responseTime = Date.now() - startTime;
            
            // 更新统计
            this.updateGlobalStats(result, responseTime, 'optimized');
            
            // 缓存结果
            if (this.config.cacheResults) {
                this.cacheResult(userMessage, sessionId, result);
            }
            
            // 生成格式化的skill描述
            const formattedSkills = this.formatSkillsForSystem(result.skills);
            
            const response = {
                skills: formattedSkills,
                mode: result.mode,
                optimization: {
                    tokensUsed: result.tokensUsed || 0,
                    tokensSaved: result.tokensSaved || 0,
                    optimizationRatio: this.calculateOptimization(result),
                    skillsLoaded: result.skills?.length || 0,
                    responseTime: responseTime
                },
                metadata: {
                    confidence: result.confidence || 0,
                    strategy: result.strategy || 'unknown',
                    fallbackUsed: (result.fallback?.length || 0) > 0,
                    sessionId: sessionId
                }
            };
            
            if (this.config.debugMode) {
                response.debug = {
                    matchResult: result,
                    processingDetails: this.getProcessingDetails(result)
                };
            }
            
            return response;
            
        } catch (error) {
            this.globalStats.errorRate++;
            console.error('❌ Smart skill system error:', error.message);
            
            // Fallback到传统加载
            if (this.config.fallbackToTraditional) {
                console.log('⚠️ Falling back to traditional skill loading');
                return await this.traditionalLoad();
            }
            
            throw error;
        }
    }
    
    /**
     * 传统的全量加载方式（作为fallback）
     */
    async traditionalLoad() {
        this.globalStats.traditionalRequests++;
        
        const allSkills = await this.loadAllSkills();
        const formattedSkills = allSkills.map(skill => ({
            name: skill.name,
            description: skill.description
        }));
        
        return {
            skills: formattedSkills,
            mode: 'traditional',
            optimization: {
                tokensUsed: this.estimateTraditionalTokens(allSkills),
                tokensSaved: 0,
                optimizationRatio: 0,
                skillsLoaded: allSkills.length,
                responseTime: 0
            },
            metadata: {
                confidence: 1.0,
                strategy: 'load_all',
                fallbackUsed: true
            }
        };
    }
    
    /**
     * 加载所有技能（传统方式）
     */
    async loadAllSkills() {
        const skillsDir = path.join(__dirname, '..');
        const skillDirs = await fs.readdir(skillsDir);
        const skills = [];
        
        for (const dir of skillDirs) {
            if (dir.startsWith('_') || dir.startsWith('.')) continue;
            
            try {
                const skillData = await this.loader.loadSkillDescription(dir);
                if (skillData) {
                    skills.push({
                        name: dir,
                        description: skillData.description,
                        fullPath: skillData.fullPath
                    });
                }
            } catch (err) {
                console.warn(`⚠️ Could not load skill ${dir}:`, err.message);
            }
        }
        
        return skills;
    }
    
    /**
     * 格式化技能描述供系统使用
     */
    formatSkillsForSystem(skills) {
        if (!Array.isArray(skills)) return [];
        
        return skills.map(skill => ({
            name: skill.name,
            description: this.optimizeDescription(skill.description),
            location: skill.fullPath,
            confidence: skill.confidence,
            category: skill.category,
            loadSource: skill.loadSource || 'smart'
        }));
    }
    
    /**
     * 优化描述文本以减少token使用
     */
    optimizeDescription(description) {
        if (!description) return '';
        
        // 移除多余的空白和格式化字符
        let optimized = description
            .replace(/\s+/g, ' ')
            .replace(/[#*_`]/g, '')
            .trim();
        
        // 限制长度
        if (optimized.length > 200) {
            optimized = optimized.substring(0, 197) + '...';
        }
        
        return optimized;
    }
    
    /**
     * 缓存结果
     */
    cacheResult(userMessage, sessionId, result) {
        const cacheKey = `${sessionId}:${userMessage.toLowerCase().trim()}`;
        this.sessionCache.set(cacheKey, {
            result: result,
            timestamp: Date.now(),
            hits: 1
        });
        
        // 限制缓存大小
        if (this.sessionCache.size > 1000) {
            const oldestKey = this.sessionCache.keys().next().value;
            this.sessionCache.delete(oldestKey);
        }
    }
    
    /**
     * 检查缓存
     */
    checkCache(userMessage, sessionId) {
        const cacheKey = `${sessionId}:${userMessage.toLowerCase().trim()}`;
        const cached = this.sessionCache.get(cacheKey);
        
        if (cached) {
            // 检查缓存是否过期（5分钟）
            const age = Date.now() - cached.timestamp;
            if (age < 5 * 60 * 1000) {
                cached.hits++;
                return cached.result;
            } else {
                this.sessionCache.delete(cacheKey);
            }
        }
        
        return null;
    }
    
    /**
     * 计算优化比率
     */
    calculateOptimization(result) {
        const used = result.tokensUsed || 0;
        const saved = result.tokensSaved || 0;
        const total = used + saved;
        
        return total > 0 ? saved / total : 0;
    }
    
    /**
     * 估算传统方式的token使用
     */
    estimateTraditionalTokens(skills) {
        return skills.reduce((total, skill) => {
            return total + Math.ceil((skill.description?.length || 150) / 4);
        }, 0);
    }
    
    /**
     * 更新全局统计
     */
    updateGlobalStats(result, responseTime, mode) {
        if (mode === 'optimized') {
            this.globalStats.optimizedRequests++;
            this.globalStats.totalTokensSaved += result.tokensSaved || 0;
        }
        
        // 更新平均响应时间
        const totalRequests = this.globalStats.totalRequests;
        this.globalStats.averageResponseTime = 
            (this.globalStats.averageResponseTime * (totalRequests - 1) + responseTime) / totalRequests;
    }
    
    /**
     * 获取处理详情
     */
    getProcessingDetails(result) {
        return {
            primarySkills: result.primary?.length || 0,
            fallbackSkills: result.fallback?.length || 0,
            loadSuccess: result.loadSuccess || 0,
            loadFailures: result.loadFailures || 0,
            cacheHits: result.performance?.cacheHitRate || 0,
            confidence: result.confidence || 0
        };
    }
    
    /**
     * 强制加载指定技能
     */
    async forceLoadSkills(skillNames, sessionId = 'default') {
        await this.init();
        
        const result = await this.loader.forceLoad(skillNames);
        const formattedSkills = this.formatSkillsForSystem(result.skills);
        
        return {
            skills: formattedSkills,
            mode: 'force',
            optimization: {
                tokensUsed: result.tokensUsed || 0,
                tokensSaved: 0,
                optimizationRatio: 0,
                skillsLoaded: result.skills?.length || 0
            },
            metadata: {
                confidence: 1.0,
                strategy: 'force_load',
                sessionId: sessionId,
                forced: true
            }
        };
    }
    
    /**
     * 获取系统统计信息
     */
    getSystemStats() {
        const loaderStats = this.loader.getDetailedStats();
        
        return {
            global: this.globalStats,
            optimization: {
                optimizationRate: this.globalStats.optimizedRequests / this.globalStats.totalRequests,
                averageTokensSaved: this.globalStats.totalTokensSaved / this.globalStats.optimizedRequests,
                errorRate: this.globalStats.errorRate / this.globalStats.totalRequests
            },
            loader: loaderStats,
            cache: {
                size: this.sessionCache.size,
                hitRate: this.calculateCacheHitRate()
            },
            config: this.config
        };
    }
    
    /**
     * 计算缓存命中率
     */
    calculateCacheHitRate() {
        let totalHits = 0;
        let totalRequests = 0;
        
        for (const cached of this.sessionCache.values()) {
            totalHits += cached.hits;
            totalRequests += cached.hits;
        }
        
        return totalRequests > 0 ? (totalHits - this.sessionCache.size) / totalRequests : 0;
    }
    
    /**
     * 清理缓存
     */
    clearCache() {
        this.sessionCache.clear();
        this.loader.clearCache();
        console.log('🧹 Smart skill system cache cleared');
    }
    
    /**
     * 重置统计
     */
    resetStats() {
        this.globalStats = {
            totalRequests: 0,
            optimizedRequests: 0,
            traditionalRequests: 0,
            totalTokensSaved: 0,
            averageResponseTime: 0,
            errorRate: 0
        };
        console.log('📊 Statistics reset');
    }
    
    /**
     * 更新配置
     */
    updateConfig(newConfig) {
        this.config = { ...this.config, ...newConfig };
        console.log('⚙️ Configuration updated');
    }
    
    /**
     * 健康检查
     */
    async healthCheck() {
        try {
            await this.init();
            const testResult = await this.loader.smartLoad('test message');
            
            return {
                status: 'healthy',
                components: {
                    loader: 'ok',
                    matcher: 'ok',
                    cache: this.sessionCache.size < 1000 ? 'ok' : 'warning'
                },
                stats: this.getSystemStats(),
                timestamp: Date.now()
            };
        } catch (error) {
            return {
                status: 'unhealthy',
                error: error.message,
                timestamp: Date.now()
            };
        }
    }
}

/**
 * 全局单例实例
 */
let globalInstance = null;

/**
 * 获取全局实例
 */
function getSmartSkillSystem(options = {}) {
    if (!globalInstance) {
        globalInstance = new SmartSkillSystem(options);
    }
    return globalInstance;
}

/**
 * 便捷的快速接口
 */
async function getSkillsForMessage(userMessage, sessionId = 'default', options = {}) {
    const system = getSmartSkillSystem();
    return await system.getRelevantSkills(userMessage, sessionId, options);
}

module.exports = { 
    SmartSkillSystem, 
    getSmartSkillSystem, 
    getSkillsForMessage 
};

// CLI 使用
if (require.main === module) {
    const command = process.argv[2];
    const args = process.argv.slice(3);
    
    async function runCommand() {
        const system = getSmartSkillSystem({ logPerformance: true, debugMode: true });
        
        switch (command) {
            case 'test':
                const message = args[0] || '帮我生成一个PDF';
                console.log(`🧪 Testing message: "${message}"\n`);
                
                const result = await system.getRelevantSkills(message, 'test-session');
                console.log('📝 Result:');
                console.log(`   Mode: ${result.mode}`);
                console.log(`   Skills loaded: ${result.skills.length}`);
                console.log(`   Tokens used: ${result.optimization.tokensUsed}`);
                console.log(`   Tokens saved: ${result.optimization.tokensSaved}`);
                console.log(`   Optimization: ${(result.optimization.optimizationRatio * 100).toFixed(1)}%`);
                console.log(`   Response time: ${result.optimization.responseTime}ms`);
                
                if (result.skills.length > 0) {
                    console.log('\n📚 Loaded skills:');
                    result.skills.forEach(skill => {
                        console.log(`   - ${skill.name}: ${skill.description.substring(0, 60)}...`);
                    });
                }
                break;
                
            case 'benchmark':
                console.log('🏃 Running comprehensive benchmark...\n');
                
                const testCases = [
                    { message: "帮我生成一个PDF", expected: ['pdf-generator'] },
                    { message: "今天天气怎样？", expected: [] },
                    { message: "转录这个语音文件", expected: ['voice-transcription'] },
                    { message: "写一篇杂志风格的文章", expected: ['article-generator'] },
                    { message: "我现在在哪个session？", expected: ['session-manager'] },
                    { message: "创建一个skill", expected: ['skill-creator'] },
                    { message: "搜索OpenAI消息", expected: [] }
                ];
                
                let totalOptimization = 0;
                let correctPredictions = 0;
                
                for (const testCase of testCases) {
                    const result = await system.getRelevantSkills(testCase.message, 'benchmark');
                    const loadedSkills = result.skills.map(s => s.name);
                    
                    const hasExpectedSkills = testCase.expected.every(expected => 
                        loadedSkills.some(loaded => loaded.includes(expected))
                    );
                    
                    if (hasExpectedSkills || testCase.expected.length === 0) {
                        correctPredictions++;
                    }
                    
                    totalOptimization += result.optimization.optimizationRatio;
                    
                    console.log(`📝 "${testCase.message}"`);
                    console.log(`   Expected: ${testCase.expected.join(', ') || 'none'}`);
                    console.log(`   Loaded: ${loadedSkills.join(', ') || 'none'}`);
                    console.log(`   Correct: ${hasExpectedSkills || testCase.expected.length === 0 ? '✅' : '❌'}`);
                    console.log(`   Optimization: ${(result.optimization.optimizationRatio * 100).toFixed(1)}%\n`);
                }
                
                console.log('📊 Benchmark Results:');
                console.log(`   Accuracy: ${(correctPredictions / testCases.length * 100).toFixed(1)}%`);
                console.log(`   Average optimization: ${(totalOptimization / testCases.length * 100).toFixed(1)}%`);
                break;
                
            case 'stats':
                const stats = system.getSystemStats();
                console.log(JSON.stringify(stats, null, 2));
                break;
                
            case 'health':
                const health = await system.healthCheck();
                console.log(JSON.stringify(health, null, 2));
                break;
                
            case 'compare':
                console.log('⚖️ Comparing traditional vs smart loading...\n');
                
                // 传统方式
                console.log('📚 Traditional loading:');
                const traditionalStart = Date.now();
                const traditionalResult = await system.traditionalLoad();
                const traditionalTime = Date.now() - traditionalStart;
                
                console.log(`   Skills loaded: ${traditionalResult.skills.length}`);
                console.log(`   Tokens used: ${traditionalResult.optimization.tokensUsed}`);
                console.log(`   Time: ${traditionalTime}ms\n`);
                
                // 智能方式
                console.log('🧠 Smart loading:');
                const testMsg = args[0] || '帮我生成一个PDF';
                const smartStart = Date.now();
                const smartResult = await system.getRelevantSkills(testMsg);
                const smartTime = Date.now() - smartStart;
                
                console.log(`   Message: "${testMsg}"`);
                console.log(`   Skills loaded: ${smartResult.skills.length}`);
                console.log(`   Tokens used: ${smartResult.optimization.tokensUsed}`);
                console.log(`   Tokens saved: ${smartResult.optimization.tokensSaved}`);
                console.log(`   Time: ${smartTime}ms\n`);
                
                // 对比
                console.log('📈 Comparison:');
                const tokenSavings = traditionalResult.optimization.tokensUsed - smartResult.optimization.tokensUsed;
                const timeDiff = traditionalTime - smartTime;
                
                console.log(`   Token savings: ${tokenSavings} (${(tokenSavings / traditionalResult.optimization.tokensUsed * 100).toFixed(1)}%)`);
                console.log(`   Time difference: ${timeDiff}ms`);
                console.log(`   Skills reduction: ${traditionalResult.skills.length - smartResult.skills.length}`);
                break;
                
            case 'clear':
                system.clearCache();
                break;
                
            default:
                console.log('Usage: node smart-skill-system.js <command> [args...]');
                console.log('Commands:');
                console.log('  test [message]     - Test smart loading with a message');
                console.log('  benchmark         - Run accuracy and performance tests');
                console.log('  stats            - Show system statistics');
                console.log('  health           - Perform health check');
                console.log('  compare [message] - Compare traditional vs smart loading');
                console.log('  clear            - Clear all caches');
        }
    }
    
    runCommand().catch(console.error);
}