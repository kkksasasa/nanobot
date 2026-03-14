"""
聊天 API 路由
提供 web 端可调用的聊天接口
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio

router = APIRouter(prefix="/api", tags=["聊天"])


# ============ 数据模型 ============

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息", min_length=1, max_length=10000)
    session_id: str = Field(default="web:default", description="会话 ID（保持上下文）")
    stream: bool = Field(default=False, description="是否流式返回")


class ChatResponse(BaseModel):
    """聊天响应"""
    success: bool = True
    message: str
    session_id: str
    timestamp: str
    model: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    service: str
    version: str
    timestamp: str
    nanobot_initialized: bool


class StatusResponse(BaseModel):
    """服务状态响应"""
    service: str
    initialized: bool
    model: Optional[str]
    config_path: Optional[str]
    sessions: List[Dict[str, Any]]


# ============ 路由 ============

@router.post("/chat", response_model=ChatResponse, summary="聊天接口")
async def chat(request: ChatRequest):
    """
    ## 聊天接口
    
    web 端调用此接口与 nanobot 对话
    
    ### 参数
    - **message**: 用户消息（必填）
    - **session_id**: 会话 ID，用于保持对话上下文（可选，默认 "web:default"）
    - **stream**: 是否流式返回（可选，默认 false）
    
    ### 返回
    - **success**: 是否成功
    - **message**: AI 回复内容
    - **session_id**: 会话 ID
    - **timestamp**: 时间戳
    - **model**: 使用的模型
    """
    from ..services.nanobot_service import get_service
    
    try:
        service = get_service()
        
        # 发送消息
        response = await service.chat(
            message=request.message,
            session_id=request.session_id,
        )
        
        return ChatResponse(
            success=True,
            message=response,
            session_id=request.session_id,
            timestamp=datetime.now().isoformat(),
            model=service.agent.model if service.agent else None,
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"聊天失败：{str(e)}")


@router.get("/chat/stream", summary="流式聊天接口（SSE）")
async def chat_stream(message: str, session_id: str = "web:default"):
    """
    ## 流式聊天接口（Server-Sent Events）
    
    逐步返回 AI 回复，适合实时显示
    
    ### 参数
    - **message**: 用户消息
    - **session_id**: 会话 ID
    """
    from fastapi.responses import StreamingResponse
    from ..services.nanobot_service import get_service
    
    async def generate():
        try:
            service = get_service()
            
            # 流式处理
            async for chunk in service.chat_stream(message, session_id):
                yield f"data: {chunk}\n\n"
            
            yield "data: [DONE]\n\n"
        
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/health", response_model=HealthResponse, summary="健康检查")
async def health_check():
    """
    ## 健康检查
    
    检查服务是否正常运行
    """
    from ..services.nanobot_service import get_service
    from nanobot import __version__
    
    service = get_service()
    
    return HealthResponse(
        status="healthy",
        service="niuma-custom-api",
        version=__version__,
        timestamp=datetime.now().isoformat(),
        nanobot_initialized=service._initialized,
    )


@router.get("/status", response_model=StatusResponse, summary="服务状态")
async def get_status():
    """
    ## 服务状态
    
    获取当前服务状态和会话列表
    """
    from ..services.nanobot_service import get_service
    
    service = get_service()
    status = service.get_status()
    
    # 获取会话列表
    sessions = []
    if service._initialized and service.agent:
        from nanobot.session.manager import SessionManager
        from nanobot.config.loader import load_config
        
        config = load_config(service.config_path)
        session_manager = SessionManager(config.workspace_path)
        
        for session in session_manager.list_sessions():
            sessions.append({
                "key": session.get("key", ""),
                "created_at": session.get("created_at", ""),
                "updated_at": session.get("updated_at", ""),
                "message_count": session.get("message_count", 0),
            })
    
    return StatusResponse(
        service="niuma-custom-api",
        initialized=status["initialized"],
        model=status["model"],
        config_path=status["config_path"],
        sessions=sessions,
    )
