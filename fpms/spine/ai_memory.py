"""AI助手记忆系统 - 六层记忆架构

实现AI助手的Context连续性，解决跨session失忆问题。

基于 ADR-2026-03-20-AI-Memory-Architecture-Breakthrough.md 的设计。

六层记忆：
- L1 Constitution: 角色定义和行为原则
- L2 Fact: 项目状态和客观事实 (复用FPMS)
- L3 Judgment: 分析记忆和推理结果
- L4 Office Memory: 工作记忆和职责边界
- L5 Narrative: 对外表述记忆
- L6 Temporary: 临时会话记忆
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from .store import Store


class MemoryLayer(Enum):
    """六层记忆模型"""
    CONSTITUTION = "constitution"    # L1: 角色定义和行为原则
    FACT = "fact"                   # L2: 项目状态和客观事实
    JUDGMENT = "judgment"           # L3: 分析记忆和推理结果
    OFFICE_MEMORY = "office_memory" # L4: 工作记忆和职责边界
    NARRATIVE = "narrative"         # L5: 对外表述记忆
    TEMPORARY = "temporary"         # L6: 临时会话记忆


@dataclass
class AIMemory:
    """AI助手记忆条目"""
    id: str
    layer: MemoryLayer
    topic: str           # 话题/分类 (用于Context组装)
    content: str         # 记忆内容
    relevance_score: float = 1.0  # 相关性分数 (用于检索排序)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict = field(default_factory=dict)  # 扩展信息


@dataclass
class ContextBundle:
    """组装好的Context包，推送给AI"""
    session_id: str
    topic: str              # 当前话题
    constitution: List[AIMemory]    # L1: 角色记忆
    facts: List[AIMemory]           # L2: 相关事实 (可能来自FPMS)
    judgments: List[AIMemory]       # L3: 相关分析
    office_memory: List[AIMemory]   # L4: 工作记忆
    narrative: List[AIMemory]       # L5: 表述记忆
    temporary: List[AIMemory]       # L6: 临时记忆
    assembled_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AIMemoryStore:
    """AI助手记忆存储和检索"""
    
    def __init__(self, db_path: str):
        """初始化AI记忆存储"""
        self.db_path = db_path
        self._ensure_tables()
    
    def _ensure_tables(self) -> None:
        """确保数据表存在"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS ai_memories (
                    id TEXT PRIMARY KEY,
                    layer TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    content TEXT NOT NULL,
                    relevance_score REAL DEFAULT 1.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}'
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_ai_memories_layer_topic 
                ON ai_memories(layer, topic)
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_ai_memories_topic_relevance 
                ON ai_memories(topic, relevance_score DESC)
            ''')
    
    def store_memory(self, memory: AIMemory) -> None:
        """存储记忆"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO ai_memories 
                (id, layer, topic, content, relevance_score, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                memory.id,
                memory.layer.value,
                memory.topic,
                memory.content,
                memory.relevance_score,
                memory.created_at,
                memory.updated_at,
                json.dumps(memory.metadata)
            ))
    
    def search_memories(
        self, 
        topic: str,
        layers: List[MemoryLayer] = None,
        limit: int = 10
    ) -> List[AIMemory]:
        """按话题和层级搜索记忆"""
        if layers is None:
            layers = list(MemoryLayer)
        
        layer_filter = ', '.join(['?' for _ in layers])
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(f'''
                SELECT * FROM ai_memories 
                WHERE topic = ? AND layer IN ({layer_filter})
                ORDER BY relevance_score DESC, updated_at DESC
                LIMIT ?
            ''', [topic] + [layer.value for layer in layers] + [limit])
            
            memories = []
            for row in cursor:
                memories.append(AIMemory(
                    id=row['id'],
                    layer=MemoryLayer(row['layer']),
                    topic=row['topic'],
                    content=row['content'],
                    relevance_score=row['relevance_score'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    metadata=json.loads(row['metadata'])
                ))
            
            return memories
    
    def get_constitution_memories(self) -> List[AIMemory]:
        """获取Constitution层记忆 (总是加载)"""
        return self.search_memories(
            topic="*",  # Constitution适用于所有话题
            layers=[MemoryLayer.CONSTITUTION]
        )


class ContextEngine:
    """Context组装引擎 - 实现DCP (确定性Context推送)"""
    
    def __init__(self, ai_memory_store: AIMemoryStore, fpms_store=None):
        """初始化Context引擎"""
        self.ai_memory = ai_memory_store
        self.fpms_store = fpms_store  # 集成FPMS的项目记忆
    
    def assemble_context(
        self, 
        session_id: str,
        topic: str,
        include_layers: List[MemoryLayer] = None
    ) -> ContextBundle:
        """组装Context Bundle (DCP核心功能)"""
        if include_layers is None:
            include_layers = [
                MemoryLayer.CONSTITUTION,
                MemoryLayer.JUDGMENT,
                MemoryLayer.OFFICE_MEMORY
            ]
        
        # 基础结构
        bundle = ContextBundle(
            session_id=session_id,
            topic=topic,
            constitution=[],
            facts=[],
            judgments=[],
            office_memory=[],
            narrative=[],
            temporary=[]
        )
        
        # 1. Constitution总是加载
        bundle.constitution = self.ai_memory.get_constitution_memories()
        
        # 2. 按话题加载其他层级
        for layer in include_layers:
            if layer == MemoryLayer.CONSTITUTION:
                continue  # 已处理
                
            memories = self.ai_memory.search_memories(topic, [layer], limit=5)
            
            if layer == MemoryLayer.FACT:
                bundle.facts.extend(memories)
            elif layer == MemoryLayer.JUDGMENT:
                bundle.judgments.extend(memories)
            elif layer == MemoryLayer.OFFICE_MEMORY:
                bundle.office_memory.extend(memories)
            elif layer == MemoryLayer.NARRATIVE:
                bundle.narrative.extend(memories)
            elif layer == MemoryLayer.TEMPORARY:
                bundle.temporary.extend(memories)
        
        # 3. 如果有FPMS集成，添加项目事实
        if self.fpms_store:
            bundle.facts.extend(self._get_fpms_facts(topic))
        
        return bundle
    
    def _get_fpms_facts(self, topic: str) -> List[AIMemory]:
        """从FPMS获取项目相关事实 (待实现FPMS集成)"""
        # TODO: 实现FPMS集成，将项目状态转换为AIMemory格式
        return []
    
    def expand_context_dynamically(
        self,
        current_bundle: ContextBundle,
        search_query: str,
        additional_layers: List[MemoryLayer] = None
    ) -> List[AIMemory]:
        """动态扩展Context (按需检索)"""
        if additional_layers is None:
            additional_layers = [MemoryLayer.JUDGMENT, MemoryLayer.OFFICE_MEMORY]
        
        # 基于查询词搜索相关记忆
        # TODO: 实现语义搜索，现在先用简单的话题匹配
        additional_memories = []
        for layer in additional_layers:
            memories = self.ai_memory.search_memories(
                topic=search_query,  # 简化版：直接用查询作为话题
                layers=[layer],
                limit=3
            )
            additional_memories.extend(memories)
        
        return additional_memories


class MemoryUpdater:
    """记忆更新器 - 处理对话后的记忆写回"""
    
    def __init__(self, ai_memory_store: AIMemoryStore):
        self.ai_memory = ai_memory_store
    
    def update_from_conversation(
        self,
        session_id: str,
        topic: str,
        conversation_summary: str,
        new_insights: List[str] = None,
        decisions_made: List[str] = None
    ) -> None:
        """从对话更新记忆"""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # 1. 更新临时记忆
        temp_memory = AIMemory(
            id=f"temp_{session_id}_{timestamp[:10]}",
            layer=MemoryLayer.TEMPORARY,
            topic=topic,
            content=conversation_summary,
            created_at=timestamp,
            updated_at=timestamp,
            metadata={"session_id": session_id}
        )
        self.ai_memory.store_memory(temp_memory)
        
        # 2. 提取判断记忆
        if new_insights:
            for i, insight in enumerate(new_insights):
                judgment_memory = AIMemory(
                    id=f"judgment_{topic}_{timestamp}_{i}",
                    layer=MemoryLayer.JUDGMENT,
                    topic=topic,
                    content=insight,
                    relevance_score=0.8,  # 新洞察高相关性
                    created_at=timestamp,
                    updated_at=timestamp,
                    metadata={"source": "conversation_insight"}
                )
                self.ai_memory.store_memory(judgment_memory)
        
        # 3. 提取决策记忆
        if decisions_made:
            for i, decision in enumerate(decisions_made):
                office_memory = AIMemory(
                    id=f"decision_{topic}_{timestamp}_{i}",
                    layer=MemoryLayer.OFFICE_MEMORY,
                    topic=topic,
                    content=decision,
                    relevance_score=0.9,  # 决策最高相关性
                    created_at=timestamp,
                    updated_at=timestamp,
                    metadata={"type": "decision", "source": "conversation"}
                )
                self.ai_memory.store_memory(office_memory)


# 便利函数
def create_ai_memory_system(db_path: str) -> tuple[AIMemoryStore, ContextEngine, MemoryUpdater]:
    """创建完整的AI记忆系统"""
    memory_store = AIMemoryStore(db_path)
    context_engine = ContextEngine(memory_store)
    memory_updater = MemoryUpdater(memory_store)
    
    return memory_store, context_engine, memory_updater