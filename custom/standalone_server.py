#!/usr/bin/env python3
"""
🐂🐎 牛马独立 HTTP 服务
不修改任何 nanobot 官方代码，独立运行的 FastAPI 服务
直接集成 AgentLoop，支持流式和详细事件推送
"""

import asyncio
import sys
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Set, Optional, Any

# 添加 workspace 到路径
workspace = Path(__file__).parent.parent
if str(workspace) not in sys.path:
    sys.path.insert(0, str(workspace))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from loguru import logger

# nanobot 导入
from nanobot.config.loader import load_config
from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus
from nanobot.bus.events import OutboundMessage
from nanobot.session.manager import SessionManager
from nanobot.providers.litellm_provider import LiteLLMProvider

# 客制化事件解析器
from custom.agent_events import create_event_parser, wrap_agent_loop


# ============ 数据模型 ============

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: str = Field(default_factory=lambda: f"http:{uuid.uuid4().hex[:8]}")


class ChatResponse(BaseModel):
    success: bool = True
    message: str
    session_id: str
    timestamp: str


class SSEMessage(BaseModel):
    type: str
    content: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @classmethod
    def start(cls, session_id: str):
        return cls(type="start", session_id=session_id, timestamp=datetime.now().isoformat())
    
    @classmethod
    def thinking(cls, content: str, session_id: str = None):
        return cls(type="thinking", content=content, session_id=session_id, timestamp=datetime.now().isoformat())
    
    @classmethod
    def tool_call(cls, name: str, args: dict, session_id: str = None):
        return cls(
            type="tool_call",
            content=f"调用工具：{name}",
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            metadata={"tool_name": name, "arguments": args}
        )
    
    @classmethod
    def tool_result(cls, name: str, result: str, session_id: str = None):
        return cls(
            type="tool_result",
            content=result[:200] + "..." if len(result) > 200 else result,
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            metadata={"tool_name": name}
        )
    
    @classmethod
    def chunk(cls, content: str, session_id: str = None):
        return cls(type="chunk", content=content, session_id=session_id, timestamp=datetime.now().isoformat())
    
    @classmethod
    def complete(cls, content: str = None, session_id: str = None):
        return cls(type="complete", content=content, session_id=session_id, timestamp=datetime.now().isoformat())
    
    @classmethod
    def error(cls, error: str, session_id: str = None):
        return cls(type="error", content=error, session_id=session_id, timestamp=datetime.now().isoformat())


# ============ 服务类 ============

class NiumaService:
    """牛马独立服务 - 不依赖 nanobot gateway"""
    
    def __init__(self):
        self.config = None
        self.agent = None
        self.bus = None
        self.session_manager = None
        self._initialized = False
        
        # 会话管理
        self.active_sessions: Dict[str, Set[asyncio.Queue]] = {}
    
    async def initialize(self):
        """初始化服务"""
        if self._initialized:
            return
        
        logger.info("🐂🐎 初始化牛马服务...")
        
        # 加载配置
        self.config = load_config()
        
        # 创建核心组件
        self.bus = MessageBus()
        self.session_manager = SessionManager(self.config.workspace_path)
        
        # 创建 LLM Provider
        provider_cfg = self.config.get_provider(self.config.agents.defaults.model)
        self.agent = AgentLoop(
            bus=self.bus,
            provider=LiteLLMProvider(
                api_key=provider_cfg.api_key,
                api_base=self.config.get_api_base(self.config.agents.defaults.model),
                default_model=self.config.agents.defaults.model,
                provider_name=self.config.get_provider_name(self.config.agents.defaults.model),
            ),
            workspace=self.config.workspace_path,
            model=self.config.agents.defaults.model,
            temperature=self.config.agents.defaults.temperature,
            max_tokens=self.config.agents.defaults.max_tokens,
            max_iterations=self.config.agents.defaults.max_tool_iterations,
            memory_window=self.config.agents.defaults.memory_window,
            reasoning_effort=self.config.agents.defaults.reasoning_effort,
            brave_api_key=None,
            web_proxy=None,
            exec_config=self.config.tools.exec,
            cron_service=None,
            restrict_to_workspace=self.config.tools.restrict_to_workspace,
            session_manager=self.session_manager,
            mcp_servers={},
            channels_config=self.config.channels,
        )
        
        self._initialized = True
        logger.info(f"✅ 服务初始化完成，模型：{self.config.agents.defaults.model}")
    
    async def process_message(
        self,
        message: str,
        session_id: str,
        response_queue: asyncio.Queue,
    ):
        """处理消息并推送详细事件 - 使用事件解析器"""
        try:
            # 解析 session_id
            if ":" not in session_id:
                session_id = f"http:{session_id}"
            
            # 发送开始事件
            await response_queue.put(SSEMessage.start(session_id).model_dump_json())
            
            # 创建事件解析器的回调
            async def send_event(content: str, metadata: dict):
                """发送事件到队列"""
                event_type = metadata.get("type", "chunk")
                
                if event_type == "thinking":
                    sse_msg = SSEMessage.thinking(content, session_id)
                elif event_type == "tool_call":
                    sse_msg = SSEMessage.tool_call(
                        name=metadata.get("tool_name", "unknown"),
                        args=metadata.get("arguments", {}),
                        session_id=session_id,
                    )
                elif event_type == "chunk":
                    sse_msg = SSEMessage.chunk(content, session_id)
                elif event_type == "complete":
                    sse_msg = SSEMessage.complete(content, session_id)
                elif event_type == "error":
                    sse_msg = SSEMessage.error(content, session_id)
                else:
                    sse_msg = SSEMessage.chunk(content, session_id)
                
                await response_queue.put(sse_msg.model_dump_json())
            
            # 使用增强的 AgentLoop 包装器
            enhanced = wrap_agent_loop(self.agent, self.bus)
            
            # 处理消息（会自动推送详细事件）
            await enhanced.process_with_events(
                message=message,
                session_id=session_id,
                channel="http",
                chat_id=session_id,
            )
        
        except Exception as e:
            logger.error(f"处理消息失败：{e}")
            await response_queue.put(SSEMessage.error(str(e)).model_dump_json())
        
        finally:
            # 清理会话
            if session_id in self.active_sessions:
                self.active_sessions[session_id].discard(response_queue)
                if not self.active_sessions[session_id]:
                    del self.active_sessions[session_id]


# ============ FastAPI 应用 ============

app = FastAPI(title="🐂🐎 牛马独立 HTTP 服务")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = NiumaService()


@app.on_event("startup")
async def startup_event():
    """启动时初始化服务"""
    await service.initialize()


@app.get("/", tags=["根"])
async def root():
    return {
        "service": "🐂🐎 牛马独立 HTTP 服务",
        "docs": "/docs",
        "health": "/health",
        "chat": "/chat",
        "stream": "/chat/stream",
    }


@app.get("/health", tags=["健康"])
async def health_check():
    return {
        "status": "healthy" if service._initialized else "initializing",
        "service": "niuma-standalone",
        "initialized": service._initialized,
        "model": service.config.agents.defaults.model if service.config else None,
        "active_sessions": len(service.active_sessions),
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/chat", response_model=ChatResponse, tags=["聊天"])
async def chat(request: ChatRequest):
    """普通聊天接口"""
    if not service._initialized:
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    session_id = request.session_id
    response_queue = asyncio.Queue()
    
    service.active_sessions[session_id] = {response_queue}
    
    # 处理消息
    asyncio.create_task(service.process_message(
        request.message,
        session_id,
        response_queue,
    ))
    
    # 收集回复
    full_response = []
    try:
        while True:
            chunk = await asyncio.wait_for(response_queue.get(), timeout=60.0)
            data = SSEMessage.model_validate_json(chunk)
            if data.type == "complete":
                break
            if data.type == "chunk":
                full_response.append(data.content)
            if data.type == "error":
                raise HTTPException(status_code=500, detail=data.content)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="请求超时")
    
    return ChatResponse(
        success=True,
        message="".join(full_response),
        session_id=session_id,
        timestamp=datetime.now().isoformat(),
    )


@app.get("/chat/stream", tags=["聊天"])
async def chat_stream(message: str, session_id: str = None):
    """流式聊天接口（SSE）"""
    if not service._initialized:
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    if not session_id:
        session_id = f"http:{uuid.uuid4().hex[:8]}"
    elif ":" not in session_id:
        session_id = f"http:{session_id}"
    
    response_queue = asyncio.Queue()
    service.active_sessions[session_id] = {response_queue}
    
    # 处理消息
    asyncio.create_task(service.process_message(
        message,
        session_id,
        response_queue,
    ))
    
    async def generate():
        try:
            while True:
                chunk = await asyncio.wait_for(response_queue.get(), timeout=120.0)
                yield f"data: {chunk}\n\n"
                
                data = SSEMessage.model_validate_json(chunk)
                if data.type in ["complete", "error"]:
                    break
        except asyncio.TimeoutError:
            yield f"data: {SSEMessage.error('请求超时').model_dump_json()}\n\n"
        except Exception as e:
            yield f"data: {SSEMessage.error(str(e)).model_dump_json()}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ============ 启动命令 ============

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🐂🐎 启动牛马独立 HTTP 服务...")
    logger.info("📍 监听地址：http://0.0.0.0:8001")
    logger.info("📚 API 文档：http://localhost:8001/docs")
    logger.info("🧪 测试页面：http://localhost:8001/stream_test.html")
    
    uvicorn.run(
        "standalone_server:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
    )
