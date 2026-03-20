"""AI助手记忆系统的MCP工具接口

为OpenClaw提供memory_search、context_load等工具，
实现AI助手的跨session记忆连续性。
"""

from typing import Dict, List, Any, Optional
import json
from .ai_memory import (
    AIMemory,
    MemoryLayer, 
    AIMemoryStore,
    ContextEngine,
    MemoryUpdater,
    create_ai_memory_system
)


class AIMemoryTools:
    """AI助手记忆工具集"""
    
    def __init__(self, db_path: str):
        """初始化记忆工具"""
        self.memory_store, self.context_engine, self.memory_updater = create_ai_memory_system(db_path)
    
    def memory_search(
        self,
        query: str,
        layers: List[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """搜索相关记忆
        
        Args:
            query: 搜索话题
            layers: 要搜索的记忆层级 (可选)
            limit: 返回条数限制
        """
        try:
            # 转换层级参数
            if layers:
                memory_layers = [MemoryLayer(layer) for layer in layers]
            else:
                memory_layers = None
            
            # 搜索记忆
            memories = self.memory_store.search_memories(
                topic=query,
                layers=memory_layers,
                limit=limit
            )
            
            # 转换为JSON格式
            result = {
                "success": True,
                "query": query,
                "found_count": len(memories),
                "memories": []
            }
            
            for memory in memories:
                result["memories"].append({
                    "id": memory.id,
                    "layer": memory.layer.value,
                    "topic": memory.topic,
                    "content": memory.content,
                    "relevance_score": memory.relevance_score,
                    "created_at": memory.created_at,
                    "updated_at": memory.updated_at,
                    "metadata": memory.metadata
                })
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    def load_context(
        self,
        session_id: str,
        topic: str,
        include_layers: List[str] = None
    ) -> Dict[str, Any]:
        """加载Context Bundle (DCP核心功能)
        
        Args:
            session_id: 会话ID
            topic: 当前话题
            include_layers: 要包含的记忆层级
        """
        try:
            # 转换层级参数
            if include_layers:
                memory_layers = [MemoryLayer(layer) for layer in include_layers]
            else:
                memory_layers = None
            
            # 组装Context
            bundle = self.context_engine.assemble_context(
                session_id=session_id,
                topic=topic,
                include_layers=memory_layers
            )
            
            # 转换为工具返回格式
            result = {
                "success": True,
                "session_id": session_id,
                "topic": topic,
                "assembled_at": bundle.assembled_at,
                "context": {}
            }
            
            # 添加各层记忆
            if bundle.constitution:
                result["context"]["constitution"] = [
                    {
                        "content": mem.content,
                        "relevance_score": mem.relevance_score
                    } 
                    for mem in bundle.constitution
                ]
            
            if bundle.facts:
                result["context"]["facts"] = [
                    {
                        "content": mem.content,
                        "topic": mem.topic,
                        "relevance_score": mem.relevance_score
                    }
                    for mem in bundle.facts
                ]
            
            if bundle.judgments:
                result["context"]["judgments"] = [
                    {
                        "content": mem.content,
                        "topic": mem.topic,
                        "relevance_score": mem.relevance_score
                    }
                    for mem in bundle.judgments
                ]
            
            if bundle.office_memory:
                result["context"]["office_memory"] = [
                    {
                        "content": mem.content,
                        "topic": mem.topic,
                        "relevance_score": mem.relevance_score
                    }
                    for mem in bundle.office_memory
                ]
            
            if bundle.narrative:
                result["context"]["narrative"] = [
                    {
                        "content": mem.content,
                        "topic": mem.topic,
                        "relevance_score": mem.relevance_score
                    }
                    for mem in bundle.narrative
                ]
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id,
                "topic": topic
            }
    
    def store_memory(
        self,
        layer: str,
        topic: str,
        content: str,
        relevance_score: float = 1.0,
        metadata: Dict = None
    ) -> Dict[str, Any]:
        """存储新记忆
        
        Args:
            layer: 记忆层级
            topic: 话题分类
            content: 记忆内容
            relevance_score: 相关性分数
            metadata: 扩展元数据
        """
        try:
            # 生成记忆ID
            import hashlib
            import time
            memory_id = f"{layer}_{topic}_{int(time.time())}_{hashlib.md5(content.encode()).hexdigest()[:8]}"
            
            # 创建记忆对象
            memory = AIMemory(
                id=memory_id,
                layer=MemoryLayer(layer),
                topic=topic,
                content=content,
                relevance_score=relevance_score,
                metadata=metadata or {}
            )
            
            # 存储记忆
            self.memory_store.store_memory(memory)
            
            return {
                "success": True,
                "memory_id": memory_id,
                "layer": layer,
                "topic": topic,
                "message": "Memory stored successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "layer": layer,
                "topic": topic
            }
    
    def expand_context(
        self,
        session_id: str,
        current_topic: str,
        search_query: str,
        additional_layers: List[str] = None
    ) -> Dict[str, Any]:
        """动态扩展Context (按需检索)
        
        Args:
            session_id: 会话ID
            current_topic: 当前话题
            search_query: 搜索查询
            additional_layers: 额外搜索的层级
        """
        try:
            # 创建临时bundle用于扩展
            base_bundle = self.context_engine.assemble_context(session_id, current_topic)
            
            # 转换层级参数
            if additional_layers:
                memory_layers = [MemoryLayer(layer) for layer in additional_layers]
            else:
                memory_layers = None
            
            # 动态扩展
            additional_memories = self.context_engine.expand_context_dynamically(
                current_bundle=base_bundle,
                search_query=search_query,
                additional_layers=memory_layers
            )
            
            # 返回结果
            result = {
                "success": True,
                "session_id": session_id,
                "search_query": search_query,
                "found_count": len(additional_memories),
                "additional_memories": []
            }
            
            for memory in additional_memories:
                result["additional_memories"].append({
                    "layer": memory.layer.value,
                    "topic": memory.topic,
                    "content": memory.content,
                    "relevance_score": memory.relevance_score
                })
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id,
                "search_query": search_query
            }
    
    def update_conversation_memory(
        self,
        session_id: str,
        topic: str,
        conversation_summary: str,
        new_insights: List[str] = None,
        decisions_made: List[str] = None
    ) -> Dict[str, Any]:
        """更新对话记忆
        
        Args:
            session_id: 会话ID
            topic: 话题
            conversation_summary: 对话摘要
            new_insights: 新洞察
            decisions_made: 新决策
        """
        try:
            self.memory_updater.update_from_conversation(
                session_id=session_id,
                topic=topic,
                conversation_summary=conversation_summary,
                new_insights=new_insights or [],
                decisions_made=decisions_made or []
            )
            
            return {
                "success": True,
                "session_id": session_id,
                "topic": topic,
                "message": "Conversation memory updated successfully",
                "insights_count": len(new_insights or []),
                "decisions_count": len(decisions_made or [])
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id,
                "topic": topic
            }


# 工具函数注册
def register_ai_memory_tools(db_path: str) -> AIMemoryTools:
    """注册AI记忆工具到MCP系统"""
    return AIMemoryTools(db_path)