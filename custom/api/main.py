"""
🐂🐎 牛马客制化 FastAPI 服务
提供 web 端可调用的聊天接口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from .chat import router as chat_router


# ============ 生命周期管理 ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    print("🐂🐎 牛马服务启动中...")
    
    try:
        from ..services.nanobot_service import init_service
        await init_service()
        print("✅ nanobot 服务初始化完成")
    except Exception as e:
        print(f"⚠️ nanobot 初始化失败：{e}")
        print("   将在首次请求时重试")
    
    yield
    
    # 关闭时清理
    print("🐂🐎 牛马服务关闭中...")


# ============ 创建应用 ============

app = FastAPI(
    title="🐂🐎 牛马客制化 API",
    description="""
## nanobot 客制化聊天服务
    
基于 nanobot 框架，提供 web 端可调用的聊天接口。

### 功能特性
- ✅ 聊天对话（支持上下文）
- ✅ 流式返回（SSE）
- ✅ 健康检查
- ✅ 状态查询
- ✅ CORS 支持（跨域访问）

### 快速开始
```bash
# 启动服务
uvicorn custom.api.main:app --reload --host 0.0.0.0 --port 8001

# 访问文档
http://localhost:8001/docs
```
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# ============ 中间件 ============

# CORS 配置（允许跨域）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ 注册路由 ============

app.include_router(chat_router)

# ============ 根路由 ============

@app.get("/", tags=["根"])
async def root():
    """根路径，显示欢迎信息"""
    return {
        "message": "🐂🐎 欢迎使用牛马客制化 API",
        "docs": "/docs",
        "health": "/api/health",
        "chat": "/api/chat",
    }


@app.get("/ping", tags=["根"])
async def ping():
    """简单的 Ping 测试"""
    return {"pong": True, "service": "niuma-custom-api"}


# ============ 启动命令 ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )
