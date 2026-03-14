"""
nanobot 集成服务
封装 nanobot 的 AgentLoop，提供简单的聊天接口
"""

import asyncio
from pathlib import Path
from typing import Optional, Callable, AsyncGenerator


class NanobotService:
    """nanobot 服务封装"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化 nanobot 服务
        
        Args:
            config_path: nanobot 配置文件路径，默认 ~/.nanobot/config.json
        """
        self.config_path = Path(config_path).expanduser() if config_path else Path.home() / ".nanobot" / "config.json"
        self.agent = None
        self._initialized = False
    
    async def initialize(self):
        """初始化 nanobot AgentLoop"""
        if self._initialized:
            return
        
        from nanobot.config.loader import load_config
        from nanobot.agent.loop import AgentLoop
        from nanobot.bus.queue import MessageBus
        from nanobot.session.manager import SessionManager
        from nanobot.providers.litellm_provider import LiteLLMProvider
        
        # 加载配置
        config = load_config(self.config_path)
        
        # 创建核心组件
        bus = MessageBus()
        session_manager = SessionManager(config.workspace_path)
        
        # 创建 LLM Provider
        provider = LiteLLMProvider(
            api_key=config.get_provider(config.agents.defaults.model).api_key,
            api_base=config.get_api_base(config.agents.defaults.model),
            default_model=config.agents.defaults.model,
            provider_name=config.get_provider_name(config.agents.defaults.model),
        )
        
        # 创建 AgentLoop
        self.agent = AgentLoop(
            bus=bus,
            provider=provider,
            workspace=config.workspace_path,
            model=config.agents.defaults.model,
            temperature=config.agents.defaults.temperature,
            max_tokens=config.agents.defaults.max_tokens,
            max_iterations=config.agents.defaults.max_tool_iterations,
            memory_window=config.agents.defaults.memory_window,
            reasoning_effort=config.agents.defaults.reasoning_effort,
            brave_api_key=None,
            web_proxy=None,
            exec_config=config.tools.exec,
            cron_service=None,
            restrict_to_workspace=config.tools.restrict_to_workspace,
            session_manager=session_manager,
            mcp_servers={},
            channels_config=config.channels,
        )
        
        self._initialized = True
        print(f"✅ nanobot 服务已初始化，模型：{config.agents.defaults.model}")
    
    async def chat(
        self, 
        message: str, 
        session_id: str = "web:default",
        on_progress: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        发送消息并获取回复
        
        Args:
            message: 用户消息
            session_id: 会话 ID（用于保持上下文）
            on_progress: 进度回调函数（接收思考过程）
        
        Returns:
            AI 回复内容
        """
        if not self._initialized:
            await self.initialize()
        
        # 解析 session_id 格式 "channel:chat_id"
        if ":" in session_id:
            channel, chat_id = session_id.split(":", 1)
        else:
            channel = "web"
            chat_id = session_id
        
        # 处理消息
        response = await self.agent.process_direct(
            message,
            session_key=session_id,
            channel=channel,
            chat_id=chat_id,
            on_progress=on_progress,
        )
        
        return response
    
    async def chat_stream(
        self, 
        message: str, 
        session_id: str = "web:default"
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天（逐步返回回复）
        
        Args:
            message: 用户消息
            session_id: 会话 ID
        
        Yields:
            逐步返回的回复内容
        """
        if not self._initialized:
            await self.initialize()
        
        # 解析 session_id
        if ":" in session_id:
            channel, chat_id = session_id.split(":", 1)
        else:
            channel = "web"
            chat_id = session_id
        
        # 收集完整回复
        full_response = ""
        
        def on_chunk(chunk: str):
            nonlocal full_response
            full_response += chunk
            # 这里可以通过队列传递给流式响应
        
        # 处理消息
        await self.agent.process_direct(
            message,
            session_key=session_id,
            channel=channel,
            chat_id=chat_id,
            on_progress=on_chunk,
        )
        
        yield full_response
    
    def get_status(self) -> dict:
        """获取服务状态"""
        return {
            "initialized": self._initialized,
            "config_path": str(self.config_path),
            "model": self.agent.model if self.agent else None,
        }


# 全局单例
_service: Optional[NanobotService] = None


def get_service() -> NanobotService:
    """获取 nanobot 服务单例"""
    global _service
    if _service is None:
        _service = NanobotService()
    return _service


async def init_service(config_path: Optional[str] = None):
    """初始化服务单例"""
    service = get_service()
    await service.initialize()
    return service
