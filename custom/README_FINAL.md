# 🐂🐎 牛马独立 HTTP 服务 - 最终版

## ✅ 重要说明

**本实现完全不修改任何 nanobot 官方代码！**

- ✅ 所有代码都在 `custom/` 目录下
- ✅ 不修改 `nanobot/` 目录的任何文件
- ✅ 独立运行，不依赖 nanobot gateway
- ✅ 直接集成 AgentLoop

---

## 🚀 快速启动

```bash
cd /home/admin/openclaw/workspace/custom
./run_standalone.sh
```

**启动后访问：**
- 📚 API 文档：http://localhost:8001/docs
- 🧪 测试页面：http://localhost:8001/stream_test.html
- 💚 健康检查：http://localhost:8001/health

---

## 📁 项目结构

```
/home/admin/openclaw/workspace/custom/
├── standalone_server.py    # 独立服务主程序 ⭐
├── run_standalone.sh       # 启动脚本
├── stream_test.html        # 测试页面
├── http_channel.py         # HTTP Channel（备用）
├── EVENT_STREAM.md         # 事件流文档
├── GATEWAY_INTEGRATION.md  # Gateway 集成文档（已废弃）
└── README_FINAL.md         # 本文档
```

---

## 🔌 API 接口

### 1. POST /chat - 普通聊天

```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "session_id": "user1"}'
```

### 2. GET /chat/stream - 流式聊天（SSE）

```bash
curl -N "http://localhost:8001/chat/stream?message=你好&session_id=user1"
```

**响应事件：**
- `start` - 开始处理
- `thinking` - 思考过程
- `tool_call` - 工具调用
- `tool_result` - 工具结果
- `chunk` - 回复片段
- `complete` - 完成
- `error` - 错误

---

## 💻 前端集成

### JavaScript

```javascript
const eventSource = new EventSource(
  'http://localhost:8001/chat/stream?message=你好&session_id=user1'
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'thinking') {
    console.log('💭 思考:', data.content);
  } else if (data.type === 'chunk') {
    console.log('💬 回复:', data.content);
  } else if (data.type === 'complete') {
    console.log('✓ 完成');
    eventSource.close();
  }
};
```

---

## 🛡️ 设计原则

### 1. 不修改官方代码
- ✅ 所有代码在 `custom/` 目录
- ✅ 通过 PYTHONPATH 导入 nanobot
- ✅ 独立运行，不依赖 gateway

### 2. 直接集成 AgentLoop
```python
from nanobot.agent.loop import AgentLoop

agent = AgentLoop(
    bus=MessageBus(),
    provider=LiteLLMProvider(...),
    workspace=config.workspace_path,
    ...
)
```

### 3. 支持详细事件
- 思考过程
- 工具调用
- 工具结果
- 流式回复

---

## 📊 架构图

```
┌──────────────┐
│  Web 客户端    │
│  (SSE 接收)   │
└──────┬───────┘
       │ HTTP/SSE
       ▼
┌──────────────────────────────┐
│  standalone_server.py        │
│  (独立 FastAPI 服务)          │
│  - 不修改官方代码 ✅          │
│  - 直接集成 AgentLoop         │
│  - 支持详细事件推送           │
└──────┬───────────────────────┘
       │ 直接调用
       ▼
┌──────────────────┐
│ nanobot          │
│ AgentLoop        │
│ (官方代码，未修改)│
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ LiteLLM Provider │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ qwen3.5-plus     │
│ (阿里云千问)      │
└──────────────────┘
```

---

## 🧪 测试

### 1. 启动服务
```bash
cd /home/admin/openclaw/workspace/custom
./run_standalone.sh
```

### 2. 访问测试页面
```
http://localhost:8001/stream_test.html
```

### 3. API 测试
```bash
# 健康检查
curl http://localhost:8001/health

# 普通聊天
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'

# 流式聊天
curl -N "http://localhost:8001/chat/stream?message=你好"
```

---

## ⚠️ 注意事项

### 已废弃的方案
- ❌ `http_channel.py` - 需要修改 nanobot/channels/manager.py
- ❌ `GATEWAY_INTEGRATION.md` - 依赖 gateway 集成

### 推荐方案
- ✅ `standalone_server.py` - 独立运行，不修改官方代码

---

## 📋 配置文件

服务使用 nanobot 的配置文件：
- **路径**: `~/.nanobot/config.json`
- **模型**: `qwen3.5-plus`
- **API Key**: 阿里云千问

---

## 🔧 开发说明

### 添加新功能
直接编辑 `custom/` 目录下的文件，不需要修改任何官方代码。

### 扩展 API
在 `standalone_server.py` 中添加新的路由：

```python
@app.get("/my-new-endpoint", tags=["自定义"])
async def my_new_endpoint():
    return {"message": "Hello"}
```

### 修改事件类型
编辑 `SSEMessage` 类，添加新的事件类型方法。

---

## 📞 相关链接

- [EVENT_STREAM.md](EVENT_STREAM.md) - 事件流详细文档
- [stream_test.html](stream_test.html) - 测试页面源码
- [nanobot 原文档](../nanobot/SETUP_REPORT.md) - nanobot 环境报告

---

_最后更新：2026-03-14_
_🐂🐎 牛马出品 - 不修改官方代码 ✅_
