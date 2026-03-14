"""
🐂🐎 Agent 事件解析器
解析 AgentLoop 的所有回调信息，推送到前端

不修改任何官方代码，通过包装和回调实现
"""

import asyncio
import json
import re
from typing import Callable, Awaitable, Optional, Dict, Any, List
from datetime import datetime
from loguru import logger


class AgentEventParser:
    """
    解析 AgentLoop 的回调事件
    
    支持的事件类型：
    - thinking: 思考过程（<think> 标签内容）
    - tool_call: 工具调用
    - tool_result: 工具执行结果
    - chunk: 回复内容片段
    - complete: 完成
    - error: 错误
    """
    
    def __init__(self, session_id: str, send_callback: Callable[[str, Dict[str, Any]], Awaitable[None]]):
        """
        初始化事件解析器
        
        Args:
            session_id: 会话 ID
            send_callback: 发送回调函数，签名 async def callback(content: str, metadata: dict)
        """
        self.session_id = session_id
        self.send_callback = send_callback
        self.thinking_buffer = ""
        self.tool_calls = []
        self.tool_results = []
        self.response_chunks = []
    
    async def on_progress(self, content: str, **kwargs):
        """
        处理 on_progress 回调
        
        这是 AgentLoop._run_agent_loop 中调用的回调
        """
        tool_hint = kwargs.get("tool_hint", False)
        
        if tool_hint:
            # 工具调用提示
            await self._handle_tool_hint(content)
        else:
            # 思考过程
            await self._handle_thinking(content)
    
    async def _handle_thinking(self, content: str):
        """处理思考过程"""
        # 提取 <think> 标签内容
        think_pattern = re.compile(r'<think>(.*?)</think>', re.DOTALL)
        matches = think_pattern.findall(content)
        
        for thinking in matches:
            thinking = thinking.strip()
            if thinking:
                await self.send_callback(
                    thinking,
                    {
                        "type": "thinking",
                        "session_id": self.session_id,
                    }
                )
                logger.debug(f"💭 Thinking: {thinking[:100]}...")
        
        # 也发送原始内容（如果没有标签）
        if not matches and content.strip():
            clean_content = content.strip()
            # 移除可能的标签残留
            clean_content = re.sub(r'<think>.*?</think>', '', clean_content, flags=re.DOTALL).strip()
            if clean_content:
                await self.send_callback(
                    clean_content,
                    {
                        "type": "thinking",
                        "session_id": self.session_id,
                    }
                )
    
    async def _handle_tool_hint(self, content: str):
        """
        处理工具调用提示
        
        格式示例：web_search("query..."), read_file("path...")
        """
        # 解析工具调用
        # 格式：tool_name("args") 或 tool_name("args..."), tool2("args2")
        pattern = re.compile(r'(\w+)\("([^"]+)"\)')
        matches = pattern.findall(content)
        
        for tool_name, args in matches:
            # 发送工具调用事件
            await self.send_callback(
                f"调用工具：{tool_name}",
                {
                    "type": "tool_call",
                    "tool_name": tool_name,
                    "arguments": {"query": args} if args else {},
                    "session_id": self.session_id,
                }
            )
            logger.debug(f"🔧 Tool call: {tool_name}({args})")
    
    def create_on_progress_callback(self) -> Callable[[str], Awaitable[None]]:
        """创建可以传递给 AgentLoop.process_direct 的回调函数"""
        async def callback(content: str, **kwargs):
            await self.on_progress(content, **kwargs)
        return callback


class EnhancedAgentLoop:
    """
    增强的 AgentLoop 包装器
    
    添加详细事件推送功能，不修改官方代码
    """
    
    def __init__(self, agent_loop, bus):
        """
        初始化包装器
        
        Args:
            agent_loop: 官方的 AgentLoop 实例
            bus: MessageBus 实例
        """
        self.agent = agent_loop
        self.bus = bus
    
    async def process_with_events(
        self,
        message: str,
        session_id: str,
        channel: str = "http",
        chat_id: str = None,
    ):
        """
        处理消息并推送详细事件
        
        Args:
            message: 用户消息
            session_id: 会话 ID
            channel: 渠道名称
            chat_id: 聊天 ID
        """
        if not chat_id:
            chat_id = session_id
        
        # 创建事件解析器
        async def send_callback(content: str, metadata: Dict[str, Any]):
            """发送事件到消息总线"""
            from nanobot.bus.events import OutboundMessage
            await self.bus.publish_outbound(OutboundMessage(
                channel=channel,
                chat_id=chat_id,
                content=content,
                metadata=metadata,
            ))
        
        parser = AgentEventParser(session_id, send_callback)
        
        # 创建包装的 on_progress 回调
        async def on_progress(content: str, **kwargs):
            await parser.on_progress(content, **kwargs)
        
        # 调用官方的 process_direct，传入我们的回调
        try:
            # 先发送开始事件
            await send_callback("", {
                "type": "start",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
            })
            
            # 处理消息
            response = await self.agent.process_direct(
                content=message,
                session_key=session_id,
                channel=channel,
                chat_id=chat_id,
                on_progress=on_progress,
            )
            
            # 分块发送回复（模拟流式）
            chunks = [response[i:i+50] for i in range(0, len(response), 50)]
            for chunk in chunks:
                await send_callback(chunk, {
                    "type": "chunk",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                })
                await asyncio.sleep(0.05)  # 模拟流式延迟
            
            # 发送完成事件
            await send_callback(response, {
                "type": "complete",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
            })
            
            return response
        
        except Exception as e:
            logger.error(f"处理消息失败：{e}")
            await send_callback(str(e), {
                "type": "error",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
            })
            raise


def create_event_parser(
    session_id: str,
    send_callback: Callable[[str, Dict[str, Any]], Awaitable[None]]
) -> AgentEventParser:
    """创建事件解析器的工厂函数"""
    return AgentEventParser(session_id, send_callback)


def wrap_agent_loop(agent_loop, bus) -> EnhancedAgentLoop:
    """包装 AgentLoop 的工厂函数"""
    return EnhancedAgentLoop(agent_loop, bus)
