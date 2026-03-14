"""
🐂🐎 牛马 HTTP Channel - Gateway 集成版
继承 BaseChannel，可作为 nanobot gateway 的一个渠道

不修改任何官方代码，通过 monkey-patch 集成
"""

import asyncio
import uuid
from typing import Dict, Set, Optional, Any
from datetime import datetime

from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from loguru import logger

from nanobot.channels.base import BaseChannel
from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus


# ============ 数据模型 ============

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: str = Field(default_factory=lambda: f"http:{uuid.uuid4().hex[:8]}")


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


# ============ HTTP Channel ============

class HTTPChannel(BaseChannel):
    """
    HTTP API Channel - 作为 nanobot gateway 的一个渠道
    
    提供 REST API 和 SSE 流式接口
    支持详细事件推送：thinking, tool_call, chunk, complete
    """
    
    name = "http"
    
    def __init__(self, config: Any, bus: MessageBus, host: str = "0.0.0.0", port: int = 8001):
        super().__init__(config, bus)
        self.host = host
        self.port = port
        self.app = FastAPI(title="nanobot HTTP Channel")
        self.router = APIRouter()
        
        # CORS 配置
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 连接管理
        self.active_sessions: Dict[str, Set[asyncio.Queue]] = {}
        self.session_metadata: Dict[str, dict] = {}
        
        # 注册路由
        self._setup_routes()
        self.app.include_router(self.router)
        
        logger.info(f"HTTP Channel initialized on {host}:{port}")
    
    def _setup_routes(self):
        """设置 API 路由"""
        
        @self.router.get("/health", tags=["健康"])
        async def health_check():
            return {
                "status": "healthy",
                "service": "nanobot-http-channel",
                "channel": self.name,
                "running": self._running,
                "active_sessions": len(self.active_sessions),
                "timestamp": datetime.now().isoformat(),
            }
        
        @self.router.get("/status", tags=["状态"])
        async def get_status():
            return {
                "service": "nanobot-http-channel",
                "running": self._running,
                "active_sessions": len(self.active_sessions),
                "sessions": list(self.active_sessions.keys()),
            }
        
        @self.router.post("/chat", tags=["聊天"])
        async def chat(request: ChatRequest):
            """普通聊天接口"""
            session_id = request.session_id
            if ":" not in session_id:
                session_id = f"http:{session_id}"
            
            response_queue = asyncio.Queue()
            
            if session_id not in self.active_sessions:
                self.active_sessions[session_id] = set()
            
            self.active_sessions[session_id].add(response_queue)
            
            try:
                # 发布到消息总线
                await self._handle_message(
                    sender_id=session_id,
                    chat_id=session_id,
                    content=request.message,
                    session_key=session_id,
                )
                
                # 收集回复
                full_response = []
                try:
                    while True:
                        chunk = await asyncio.wait_for(response_queue.get(), timeout=60.0)
                        data = SSEMessage.model_validate_json(chunk)
                        if data.type == "complete":
                            break
                        if data.type == "chunk":
                            full_response.append(data.content or "")
                        if data.type == "error":
                            raise HTTPException(status_code=500, detail=data.content)
                except asyncio.TimeoutError:
                    raise HTTPException(status_code=504, detail="请求超时")
                
                return {"success": True, "message": "".join(full_response), "session_id": session_id}
            
            finally:
                if session_id in self.active_sessions:
                    self.active_sessions[session_id].discard(response_queue)
                    if not self.active_sessions[session_id]:
                        del self.active_sessions[session_id]
        
        @self.router.get("/chat/stream", tags=["聊天"])
        async def chat_stream(message: str, session_id: str = None):
            """流式聊天接口（SSE）"""
            if not session_id:
                session_id = f"http:{uuid.uuid4().hex[:8]}"
            elif ":" not in session_id:
                session_id = f"http:{session_id}"
            
            response_queue = asyncio.Queue()
            
            if session_id not in self.active_sessions:
                self.active_sessions[session_id] = set()
            
            self.active_sessions[session_id].add(response_queue)
            
            # 发布到消息总线
            await self._handle_message(
                sender_id=session_id,
                chat_id=session_id,
                content=message,
                session_key=session_id,
            )
            
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
                finally:
                    if session_id in self.active_sessions:
                        self.active_sessions[session_id].discard(response_queue)
                        if not self.active_sessions[session_id]:
                            del self.active_sessions[session_id]
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                }
            )
        
        @self.router.get("/", tags=["根"])
        async def root():
            return {
                "service": "nanobot HTTP Channel",
                "docs": "/docs",
                "health": "/health",
                "chat": "/chat",
                "stream": "/chat/stream",
            }
    
    async def start(self) -> None:
        """启动 HTTP 服务器"""
        import uvicorn
        
        self._running = True
        logger.info(f"Starting HTTP Channel on {self.host}:{self.port}")
        
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=False,
        )
        
        server = uvicorn.Server(config)
        asyncio.create_task(server.serve())
        
        while not server.started:
            await asyncio.sleep(0.1)
        
        logger.info(f"HTTP Channel running on http://{self.host}:{self.port}")
        
        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await server.shutdown()
    
    async def stop(self) -> None:
        """停止 HTTP 服务器"""
        self._running = False
        logger.info("Stopping HTTP Channel...")
        self.active_sessions.clear()
        self.session_metadata.clear()
    
    async def send(self, msg: OutboundMessage) -> None:
        """
        发送消息到客户端
        支持详细事件：thinking, tool_call, tool_result, chunk, complete
        """
        if msg.channel != self.name:
            return
        
        session_id = msg.chat_id
        
        if session_id not in self.active_sessions:
            logger.warning(f"Session {session_id} not found, discarding message")
            return
        
        content = msg.content or ""
        metadata = msg.metadata or {}
        event_type = metadata.get("type", "chunk")
        
        # 创建对应的 SSE 消息
        if event_type == "thinking":
            sse_msg = SSEMessage.thinking(content, session_id)
        elif event_type == "tool_call":
            sse_msg = SSEMessage.tool_call(
                name=metadata.get("tool_name", "unknown"),
                args=metadata.get("tool_args", metadata.get("arguments", {})),
                session_id=session_id,
            )
        elif event_type == "tool_result":
            sse_msg = SSEMessage.tool_result(
                name=metadata.get("tool_name", "unknown"),
                result=content,
                session_id=session_id,
            )
        elif event_type == "complete":
            sse_msg = SSEMessage.complete(content, session_id)
        elif event_type == "error":
            sse_msg = SSEMessage.error(content, session_id)
        else:
            sse_msg = SSEMessage.chunk(content, session_id)
        
        # 发送到所有队列
        for queue in list(self.active_sessions[session_id]):
            try:
                await queue.put(sse_msg.model_dump_json())
            except Exception as e:
                logger.error(f"Failed to send to queue: {e}")


def create_channel(config: Any, bus: MessageBus) -> HTTPChannel:
    """创建 HTTP Channel 实例"""
    http_config = getattr(config.channels, "http", {})
    host = http_config.get("host", "0.0.0.0") if isinstance(http_config, dict) else "0.0.0.0"
    port = http_config.get("port", 8001) if isinstance(http_config, dict) else 8001
    return HTTPChannel(config, bus, host=host, port=port)
