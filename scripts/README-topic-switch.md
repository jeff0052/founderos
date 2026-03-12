# 话题切换助手

解决 Jeff 的实际需求：**2-3个不相关问题会增加 context**

## 🎯 核心功能

### 自动检测
- 检测话题切换意图：`换个话题`、`新问题`、`另外一个`
- Context 监控：>50k 提醒，>80k 强烈建议
- 零配置：直接集成到对话流程

### 快速切换
```bash
# 检查当前状态
./scripts/topic-switch.sh status

# 获取切换建议  
./scripts/topic-switch.sh new

# 记录话题
./scripts/topic-switch.sh add "NetStar API 对接"
```

## 🚀 使用场景

**Jeff 的典型工作流:**
1. 正在讨论 NetStar API
2. 说：`对了，还想问问薪水的事`
3. 系统自动建议：💡 检测到话题切换意图，建议 `/new` 开新对话
4. Jeff 选择是否切换

## 📊 智能提醒

**Context 阈值:**
- 50k+: 温和提醒考虑切换
- 80k+: 强烈建议避免限流  
- 100k+: 危险区域，必须切换

**触发词汇:**
- `换个话题`、`新问题`、`另外一个`
- `还有个事`、`顺便问`、`对了`

## 🔧 集成方式

自动在对话中检查，无需手动调用：
```javascript
const { shouldSuggestSwitch } = require('./check-topic-switch.js');
const analysis = shouldSuggestSwitch(userMessage, contextSize);
if (analysis.should) {
    // 显示切换建议
}
```

## 💡 优势

**相比复杂的 session-manager:**
- ✅ 简单直接，解决实际问题
- ✅ 零配置，自动工作  
- ✅ 低成本，只在需要时提醒
- ✅ 符合 Jeff 的工作习惯

**解决的痛点:**
- Context 爆炸导致限流
- 不同话题混杂在一起
- 不知道何时该切换

---

**原则**: 简单有效，解决实际问题，不过度设计