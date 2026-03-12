#!/usr/bin/env node

/**
 * Skill Loader - 第二阶段按需加载器
 * 根据匹配结果，智能加载所需的skill描述
 */

const { SkillMatcher } = require('./skill-matcher');
const fs = require('fs').promises;
const path = require('path');

class SkillLoader {
    constructor() {
        this.matcher = new SkillMatcher();
        this.loadedSkills = new Map(); // 技能描述缓存
        this.loadedPaths = new Map();  // 路径缓存
        this.stats = {
            totalLoads: 0,
            cacheHits: 0,
            failedLoads: 0,
            tokensSaved: 0,
            tokensUsed: 0
        };
    }
    
    async init() {
        await this.matcher.init();
    }
    
    /**
     * 主要接口：智能加载技能描述
     */
    async smartLoad(userMessage, options = {}) {
        await this.init();
        
        // 第一阶段：轻量匹配
        const matchResult = await this.matcher.matchSkills(userMessage, options);
        
        if (matchResult.processingMode === 'direct') {
            const tokensSaved = this.estimateAllSkillsTokens();
            this.stats.tokensSaved += tokensSaved;
            
            return {
                mode: 'direct',
                skills: [],
                fallback: matchResult.fallback,
                message: 'No skills needed - direct processing',
                tokensSaved: tokensSaved,
                tokensUsed: 0,
                confidence: 0,
                strategy: 'bypass_skills',
                performance: this.getPerformanceMetrics()
            };
        }
        
        // 第二阶段：按需加载技能描述
        const loadResults = await this.loadSelectedSkills(matchResult.primary);
        const fallbackResults = await this.loadFallbackSkills(matchResult.fallback);
        
        // 合并结果
        const allSkills = [...loadResults.skills, ...fallbackResults.skills];
        const tokensUsed = this.calculateTokenUsage(allSkills);
        const tokensSaved = this.estimateAllSkillsTokens() - tokensUsed;
        
        this.updateStats(tokensUsed, tokensSaved);
        
        return {
            mode: 'skill',
            skills: allSkills,
            primary: loadResults.skills,
            fallback: fallbackResults.skills,
            totalCandidates: matchResult.totalCandidates,
            confidence: matchResult.confidence,
            strategy: matchResult.strategy,
            tokensUsed: tokensUsed,
            tokensSaved: tokensSaved,
            loadSuccess: loadResults.successCount,
            loadFailures: loadResults.failureCount,
            performance: this.getPerformanceMetrics(),
            details: {
                matchingTime: matchResult.timestamp,
                loadingTime: Date.now(),
                cacheHits: this.stats.cacheHits,
                optimization: this.calculateOptimizationRatio()
            }
        };
    }
    
    /**
     * 加载选中的技能描述
     */
    async loadSelectedSkills(primarySkills) {
        const loadPromises = primarySkills.map(skill => 
            this.loadSkillDescription(skill.skill, skill)
        );
        
        const results = await Promise.allSettled(loadPromises);
        const skills = [];
        let successCount = 0;
        let failureCount = 0;
        
        for (let i = 0; i < results.length; i++) {
            const result = results[i];
            const skillInfo = primarySkills[i];
            
            if (result.status === 'fulfilled' && result.value) {
                skills.push({
                    name: skillInfo.skill,
                    description: result.value.description,
                    fullPath: result.value.fullPath,
                    confidence: skillInfo.confidence,
                    category: skillInfo.category,
                    priority: skillInfo.priority,
                    reason: skillInfo.reason,
                    loadSource: result.value.source,
                    metadata: result.value.metadata
                });
                successCount++;
            } else {
                console.warn(`⚠️ Failed to load skill: ${skillInfo.skill}`, result.reason);
                failureCount++;
                this.stats.failedLoads++;
            }
        }
        
        return { skills, successCount, failureCount };
    }
    
    /**
     * 加载fallback技能
     */
    async loadFallbackSkills(fallbackSkills) {
        const skills = [];
        
        for (const skillName of fallbackSkills) {
            try {
                const skillData = await this.loadSkillDescription(skillName);
                if (skillData) {
                    skills.push({
                        name: skillName,
                        description: skillData.description,
                        fullPath: skillData.fullPath,
                        confidence: 1.0, // Fallback技能默认最高置信度
                        category: 'fallback',
                        priority: 10,
                        loadSource: skillData.source,
                        isFallback: true
                    });
                }
            } catch (err) {
                console.warn(`⚠️ Failed to load fallback skill: ${skillName}`, err.message);
            }
        }
        
        return { skills, successCount: skills.length, failureCount: 0 };
    }
    
    /**
     * 加载单个技能描述
     */
    async loadSkillDescription(skillName, skillInfo = null) {
        // 检查缓存
        if (this.loadedSkills.has(skillName)) {
            this.stats.cacheHits++;
            return this.loadedSkills.get(skillName);
        }
        
        try {
            const skillPath = await this.findSkillPath(skillName);
            const skillData = await this.extractSkillDescription(skillPath, skillName);
            
            // 缓存结果
            this.loadedSkills.set(skillName, skillData);
            this.loadedPaths.set(skillName, skillPath);
            this.stats.totalLoads++;
            
            return skillData;
            
        } catch (err) {
            console.error(`❌ Error loading skill ${skillName}:`, err.message);
            return null;
        }
    }
    
    /**
     * 查找技能路径
     */
    async findSkillPath(skillName) {
        // 检查路径缓存
        if (this.loadedPaths.has(skillName)) {
            return this.loadedPaths.get(skillName);
        }
        
        const possiblePaths = [
            path.join(__dirname, '..', skillName, 'SKILL.md'),
            path.join(__dirname, '..', skillName, 'README.md'),
            path.join(__dirname, '..', skillName, skillName + '.md'),
        ];
        
        for (const skillPath of possiblePaths) {
            try {
                await fs.access(skillPath);
                return skillPath;
            } catch {
                // 继续尝试下一个路径
            }
        }
        
        throw new Error(`Skill file not found for: ${skillName}`);
    }
    
    /**
     * 提取技能描述
     */
    async extractSkillDescription(skillPath, skillName) {
        const content = await fs.readFile(skillPath, 'utf8');
        const lines = content.split('\n');
        
        // 多种提取策略
        const description = this.extractDescriptionMultiStrategy(lines, content, skillName);
        const metadata = this.extractSkillMetadata(lines, content);
        
        return {
            description: description,
            fullPath: skillPath,
            source: 'file',
            metadata: metadata,
            extractedAt: Date.now(),
            contentLength: content.length
        };
    }
    
    /**
     * 多策略描述提取
     */
    extractDescriptionMultiStrategy(lines, fullContent, skillName) {
        // 策略1: 查找描述段落
        const descSection = this.findDescriptionSection(lines);
        if (descSection && descSection.length > 20) {
            return this.cleanDescription(descSection);
        }
        
        // 策略2: 查找第一个有意义的段落
        const firstParagraph = this.findFirstMeaningfulParagraph(lines);
        if (firstParagraph && firstParagraph.length > 20) {
            return this.cleanDescription(firstParagraph);
        }
        
        // 策略3: 组合前几行
        const combinedLines = lines
            .slice(0, 5)
            .join(' ')
            .replace(/#/g, '')
            .trim();
        if (combinedLines.length > 20) {
            return this.cleanDescription(combinedLines.substring(0, 200));
        }
        
        // 策略4: 使用技能名称作为fallback
        return `${skillName} skill - functionality extracted from ${skillName}`;
    }
    
    /**
     * 查找描述部分
     */
    findDescriptionSection(lines) {
        const descriptionIndicators = [
            /^.*description[：:]?(.*)$/i,
            /^.*功能[：:]?(.*)$/i,
            /^.*说明[：:]?(.*)$/i
        ];
        
        for (const line of lines) {
            for (const indicator of descriptionIndicators) {
                const match = line.match(indicator);
                if (match && match[1] && match[1].trim().length > 10) {
                    return match[1].trim();
                }
            }
        }
        
        return null;
    }
    
    /**
     * 查找第一个有意义的段落
     */
    findFirstMeaningfulParagraph(lines) {
        for (let i = 0; i < Math.min(lines.length, 10); i++) {
            const line = lines[i].trim();
            
            // 跳过标题、空行、特殊标记
            if (!line || line.startsWith('#') || line.startsWith('*') || 
                line.startsWith('-') || line.startsWith('_') ||
                line.length < 20) {
                continue;
            }
            
            // 找到有意义的内容
            if (line.length > 20 && line.length < 300) {
                return line;
            }
        }
        
        return null;
    }
    
    /**
     * 清理描述文本
     */
    cleanDescription(description) {
        return description
            .replace(/[#*_`]/g, '')  // 移除markdown标记
            .replace(/\s+/g, ' ')    // 压缩空白字符
            .trim()
            .substring(0, 250);      // 限制长度
    }
    
    /**
     * 提取技能元数据
     */
    extractSkillMetadata(lines, content) {
        const metadata = {
            hasScripts: content.includes('scripts/'),
            hasReferences: content.includes('references/'),
            hasConfig: content.includes('config/'),
            complexity: this.estimateSkillComplexity(content),
            language: this.detectContentLanguage(content),
            lastModified: null
        };
        
        // 尝试提取更多元数据
        for (const line of lines.slice(0, 20)) {
            if (line.includes('version') || line.includes('版本')) {
                const versionMatch = line.match(/(\d+\.\d+\.\d+)/);
                if (versionMatch) metadata.version = versionMatch[1];
            }
            
            if (line.includes('author') || line.includes('作者')) {
                metadata.author = line.split(/[：:]/)[1]?.trim();
            }
        }
        
        return metadata;
    }
    
    /**
     * 估算技能复杂度
     */
    estimateSkillComplexity(content) {
        const indicators = {
            scripts: (content.match(/\.js|\.py|\.sh/g) || []).length,
            configs: (content.match(/config|settings|options/gi) || []).length,
            apis: (content.match(/api|endpoint|request/gi) || []).length,
            integrations: (content.match(/integration|webhook|callback/gi) || []).length
        };
        
        const complexityScore = indicators.scripts * 2 + indicators.configs + 
                              indicators.apis * 1.5 + indicators.integrations * 2;
        
        if (complexityScore > 10) return 'very_high';
        if (complexityScore > 5) return 'high';  
        if (complexityScore > 2) return 'medium';
        return 'low';
    }
    
    /**
     * 检测内容语言
     */
    detectContentLanguage(content) {
        const chineseChars = (content.match(/[\u4e00-\u9fff]/g) || []).length;
        const englishWords = (content.match(/[a-zA-Z]+/g) || []).length;
        
        if (chineseChars > englishWords) return 'chinese';
        if (englishWords > chineseChars * 2) return 'english';
        return 'mixed';
    }
    
    /**
     * 强制加载指定技能
     */
    async forceLoad(skillNames, options = {}) {
        await this.init();
        
        const loadPromises = skillNames.map(name => this.loadSkillDescription(name));
        const results = await Promise.allSettled(loadPromises);
        
        const skills = [];
        let successCount = 0;
        let failureCount = 0;
        
        for (let i = 0; i < results.length; i++) {
            const result = results[i];
            const skillName = skillNames[i];
            
            if (result.status === 'fulfilled' && result.value) {
                skills.push({
                    name: skillName,
                    description: result.value.description,
                    fullPath: result.value.fullPath,
                    confidence: 1.0,
                    loadSource: result.value.source,
                    metadata: result.value.metadata,
                    forceLoaded: true
                });
                successCount++;
            } else {
                failureCount++;
            }
        }
        
        const tokensUsed = this.calculateTokenUsage(skills);
        this.updateStats(tokensUsed, 0);
        
        return {
            mode: 'force',
            skills: skills,
            successCount: successCount,
            failureCount: failureCount,
            tokensUsed: tokensUsed,
            performance: this.getPerformanceMetrics()
        };
    }
    
    /**
     * 计算token使用量
     */
    calculateTokenUsage(skills) {
        return skills.reduce((total, skill) => {
            const descLength = skill.description?.length || 0;
            // 简单估算: 每4个字符约等于1个token
            return total + Math.ceil(descLength / 4);
        }, 0);
    }
    
    /**
     * 估算所有技能的token总量
     */
    estimateAllSkillsTokens() {
        // 基于当前注册表估算
        const totalSkills = Object.keys(this.matcher.registry?.skills || {}).length;
        return totalSkills * 150; // 平均每个技能150 tokens
    }
    
    /**
     * 更新统计信息
     */
    updateStats(tokensUsed, tokensSaved) {
        this.stats.tokensUsed += tokensUsed;
        this.stats.tokensSaved += tokensSaved;
    }
    
    /**
     * 获取性能指标
     */
    getPerformanceMetrics() {
        return {
            totalLoads: this.stats.totalLoads,
            cacheHitRate: this.stats.totalLoads > 0 ? 
                this.stats.cacheHits / this.stats.totalLoads : 0,
            failureRate: this.stats.totalLoads > 0 ? 
                this.stats.failedLoads / this.stats.totalLoads : 0,
            tokensOptimized: this.stats.tokensSaved,
            cacheSize: this.loadedSkills.size
        };
    }
    
    /**
     * 计算优化比率
     */
    calculateOptimizationRatio() {
        const totalPossibleTokens = this.stats.tokensUsed + this.stats.tokensSaved;
        return totalPossibleTokens > 0 ? this.stats.tokensSaved / totalPossibleTokens : 0;
    }
    
    /**
     * 清理缓存
     */
    clearCache() {
        this.loadedSkills.clear();
        this.loadedPaths.clear();
        this.matcher.clearCache();
        console.log('🧹 Skill loader caches cleared');
    }
    
    /**
     * 获取详细统计
     */
    getDetailedStats() {
        return {
            ...this.stats,
            performance: this.getPerformanceMetrics(),
            optimization: this.calculateOptimizationRatio(),
            matcherStats: this.matcher.getStats(),
            cacheInfo: {
                skillsCached: this.loadedSkills.size,
                pathsCached: this.loadedPaths.size
            }
        };
    }
    
    /**
     * 重新加载技能注册表
     */
    async reloadRegistry() {
        await this.matcher.loadRegistry();
        console.log('🔄 Skill registry reloaded');
    }
}

module.exports = { SkillLoader };

// CLI 使用
if (require.main === module) {
    const loader = new SkillLoader();
    const command = process.argv[2];
    const args = process.argv.slice(3);
    
    async function runCommand() {
        switch (command) {
            case 'smart':
                const message = args[0] || '';
                const result = await loader.smartLoad(message);
                console.log(JSON.stringify(result, null, 2));
                break;
                
            case 'force':
                const skills = args;
                if (skills.length === 0) {
                    console.error('❌ Please specify skill names to force load');
                    process.exit(1);
                }
                const forceResult = await loader.forceLoad(skills);
                console.log(JSON.stringify(forceResult, null, 2));
                break;
                
            case 'stats':
                await loader.init();
                const stats = loader.getDetailedStats();
                console.log(JSON.stringify(stats, null, 2));
                break;
                
            case 'benchmark':
                console.log('🏃 Running benchmark...\n');
                
                const testMessages = [
                    "帮我生成一个PDF",
                    "今天天气怎样？", 
                    "转录这个语音文件",
                    "写一篇杂志风格的文章",
                    "我现在在哪个session？",
                    "搜索一下OpenAI的最新消息",
                    "创建一个多智能体团队"
                ];
                
                let totalTokensSaved = 0;
                let totalTokensUsed = 0;
                
                for (const msg of testMessages) {
                    const start = Date.now();
                    const result = await loader.smartLoad(msg);
                    const duration = Date.now() - start;
                    
                    totalTokensSaved += result.tokensSaved || 0;
                    totalTokensUsed += result.tokensUsed || 0;
                    
                    console.log(`📝 "${msg}"`);
                    console.log(`   Mode: ${result.mode}`);
                    console.log(`   Skills: ${result.skills?.map(s => s.name).join(', ') || 'none'}`);
                    console.log(`   Tokens: Used ${result.tokensUsed || 0}, Saved ${result.tokensSaved || 0}`);
                    console.log(`   Time: ${duration}ms\n`);
                }
                
                console.log('📊 Benchmark Summary:');
                console.log(`   Total tokens saved: ${totalTokensSaved}`);
                console.log(`   Total tokens used: ${totalTokensUsed}`);
                console.log(`   Optimization ratio: ${(totalTokensSaved / (totalTokensSaved + totalTokensUsed) * 100).toFixed(1)}%`);
                break;
                
            case 'clear':
                loader.clearCache();
                break;
                
            default:
                console.log('Usage: node skill-loader.js <command> [args...]');
                console.log('Commands:');
                console.log('  smart <message>     - Smart load based on message');
                console.log('  force <skills...>   - Force load specific skills');
                console.log('  stats              - Show detailed statistics');
                console.log('  benchmark          - Run performance benchmark');
                console.log('  clear              - Clear all caches');
        }
    }
    
    runCommand().catch(console.error);
}