# 🐂🐎 HTTP Channel 集成文档

## 📋 概述

将自定义的 **HTTP Channel** 集成到 nanobot gateway 中，作为官方渠道之一运行。

**特性：**
- ✅ REST API 接口（普通聊天）
- ✅ SSE 流式接口（实时返回）
- ✅ 会话管理（保持上下文）
- ✅ 多客户端并发支持
- ✅ 与 nanobot gateway 无缝集成

---

## 🚀 快速启动

### 方式 1：启动完整 gateway（推荐）

```bash
cd /home/admin/openclaw/workspace/nanobot
source venv/bin/activate
nanobot gateway
```

**启动后：**
- HTTP Channel 会自动启动在 `http://0.0.0.0:8001`
- 同时运行其他已配置的渠道（飞书/钉钉等）

### 方式 2：仅启动 HTTP Channel

```bash
cd /home/admin/openclaw/workspace/custom
source ../nanobot/venv/bin/activate
export PYTHONPATH="/home/admin/openclaw/workspace:$PYTHONPATH"
python -c "
import asyncio
from nanobot.config.loader import load_config
from nanobot.bus.queue import MessageBus
from custom.http_channel import HTTPChannel

async def main():
    config = load_config()
    bus = MessageBus()
    channel = HTTPChannel(config, bus, host='0.0.0.0', port=8001)
    await channel.start()

asyncio.run(main())
"
```

---

## 🔌 API 接口

### 1. POST /chat - 普通聊天

**请求：**
```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，帮我写个 Python 函数",
    "session_id": "user123"
  }'
```

**响应：**
```json
{
  "success": true,
  "message": "好的，我来帮你写一个 Python 函数...",
  "session_id": "user123",
  "timestamp": "2026-03-14T16:50:00"
}
```

---

### 2. GET /chat/stream - 流式聊天（SSE）

**请求：**
```bash
curl -N "http://localhost:8001/chat/stream?message=你好&session_id=user123"
```

**响应（Server-Sent Events）：**
```
data: {"type":"start","session_id":"http:user123"}
data: {"type":"chunk","content":"好的"}
data: {"type":"chunk","content":"，我来"}
data: {"type":"chunk","content":"帮你..."}
data: {"type":"end"}
```

**JavaScript 示例：**
```javascript
const eventSource = new EventSource(
  'http://localhost:8001/chat/stream?message=你好&session_id=user123'
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'start') {
    console.log('开始回复');
  } else if (data.type === 'chunk') {
    console.log('收到片段:', data.content);
  } else if (data.type === 'end') {
    console.log('回复完成');
    eventSource.close();
  }
};
```

---

### 3. GET /health - 健康检查

```bash
curl http://localhost:8001/health
```

**响应：**
```json
{
  "status": "healthy",
  "service": "nanobot-http-channel",
  "channel": "http",
  "running": true,
  "active_sessions": 3,
  "timestamp": "2026-03-14T16:50:00"
}
```

---

### 4. GET /status - 服务状态

```bash
curl http://localhost:8001/status
```

**响应：**
```json
{
  "service": "nanobot-http-channel",
  "running": true,
  "active_sessions": 3,
  "sessions": ["http:user123", "http:user456", "http:user789"]
}
```

---

## 📁 项目结构

```
/home/admin/openclaw/workspace/
├── custom/
│   ├── http_channel.py       # HTTP Channel 实现 ⭐
│   ├── GATEWAY_INTEGRATION.md # 本文档
│   └── ...
└── nanobot/
    └── nanobot/
        └── channels/
            ├── manager.py    # 已修改，支持 HTTP Channel
            └── ...
```

---

## ⚙️ 配置说明

### nanobot 配置

编辑 `~/.nanobot/config.json`：

```json
{
  "channels": {
    "http": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 8001,
      "allowFrom": ["*"]
    }
  }
}
```

**配置项：**
- `enabled` - 是否启用
- `host` - 监听地址（默认 `0.0.0.0`）
- `port` - 监听端口（默认 `8001`）
- `allowFrom` - 允许的用户 ID 列表（`["*"]` 表示允许所有）

---

## 🔧 技术架构

### 消息流程

```
┌──────────┐     ┌─────────────┐     ┌──────────────┐
│  Web 客户端 │────▶│ HTTP Channel │────▶│ MessageBus   │
└──────────┘     └─────────────┘     └──────────────┘
                                            │
                                            ▼
                                     ┌──────────────┐
                                     │  AgentLoop   │
                                     └──────────────┘
                                            │
                                            ▼
                                     ┌──────────────┐
                                     │  LLM Provider│
                                     │ (qwen3.5-plus)│
                                     └──────────────┘
```

### 流式实现

1. **客户端** 发起 SSE 请求
2. **HTTP Channel** 创建响应队列
3. **AgentLoop** 处理消息，逐步生成回复
4. **Channel** 通过 `send()` 方法接收片段
5. **SSE** 实时推送到客户端

---

## 💻 客户端集成示例

### Python

```python
import requests
import json

class NiumaClient:
    def __init__(self, base_url='http://localhost:8001'):
        self.base_url = base_url
        self.session_id = f'web:{id(self)}'
    
    def chat(self, message: str) -> str:
        """普通聊天"""
        response = requests.post(
            f'{self.base_url}/chat',
            json={'message': message, 'session_id': self.session_id}
        )
        data = response.json()
        return data['message']
    
    def chat_stream(self, message: str):
        """流式聊天"""
        import sseclient
        
        url = f'{self.base_url}/chat/stream'
        params = {'message': message, 'session_id': self.session_id}
        
        response = requests.get(url, params=params, stream=True)
        client = sseclient.SSEClient(response)
        
        for event in client.events():
            data = json.loads(event.data)
            if data['type'] == 'chunk':
                yield data['content']
            elif data['type'] == 'end':
                break

# 使用示例
client = NiumaClient()

# 普通聊天
reply = client.chat('你好')
print(reply)

# 流式聊天
for chunk in client.chat_stream('你好'):
    print(chunk, end='', flush=True)
```

### JavaScript/TypeScript

```typescript
class NiumaClient {
  private baseUrl: string;
  private sessionId: string;
  
  constructor(baseUrl: string = 'http://localhost:8001') {
    this.baseUrl = baseUrl;
    this.sessionId = `web:${Math.random().toString(36).substr(2, 9)}`;
  }
  
  async chat(message: string): Promise<string> {
    const response = await fetch(`${this.baseUrl}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: message,
        session_id: this.sessionId
      })
    });
    
    const data = await response.json();
    return data.message;
  }
  
  chatStream(message: string): AsyncGenerator<string> {
    const url = `${this.baseUrl}/chat/stream?message=${encodeURIComponent(message)}&session_id=${this.sessionId}`;
    
    return (async function* () {
      const response = await fetch(url);
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      while (true) {
        const { done, value } = await reader!.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop()!;
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            if (data.type === 'chunk') {
              yield data.content;
            } else if (data.type === 'end') {
              return;
            }
          }
        }
      }
    })();
  }
}
```

---

## 🛡️ 安全建议

### 生产环境配置

1. **限制 CORS**
   ```python
   # 修改 http_channel.py
   self.app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://your-domain.com"],  # 限制具体域名
       allow_credentials=True,
       allow_methods=["POST", "GET"],
       allow_headers=["Content-Type"],
   )
   ```

2. **添加认证**
   ```python
   # 添加 API Key 验证
   @self.router.post("/chat")
   async def chat(request: ChatRequest, x_api_key: str = Header(...)):
       if x_api_key != os.getenv("API_KEY"):
           raise HTTPException(status_code=401, detail="Invalid API key")
   ```

3. **限流**
   ```python
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)
   app.state.limiter = limiter
   
   @router.post("/chat")
   @limiter.limit("10/minute")
   async def chat(request: Request, ...):
       ...
   ```

4. **使用 HTTPS**
   - 通过 Nginx 反向代理
   - 配置 SSL 证书

---

## 🔧 常见问题

### 1. Channel 未启动

**检查配置：**
```bash
cat ~/.nanobot/config.json | grep -A 5 '"http"'
```

**查看日志：**
```bash
nanobot gateway --verbose
```

### 2. 端口被占用

**解决：** 修改配置端口
```json
{
  "channels": {
    "http": {
      "port": 8002
    }
  }
}
```

### 3. CORS 错误

**解决：** 确保 `allow_origins=["*"]` 或配置具体域名

---

## 📊 性能优化

### 1. 连接池

```python
# 限制每个会话的队列数量
MAX_QUEUES_PER_SESSION = 5
if len(self.active_sessions[session_id]) >= MAX_QUEUES_PER_SESSION:
    raise HTTPException(429, "Too many connections")
```

### 2. 超时设置

```python
# 调整 SSE 超时
timeout=300.0  # 5 分钟
```

### 3. 缓冲区

```python
# 禁用 Nginx 缓冲
headers={
    "X-Accel-Buffering": "no",
}
```

---

## 📞 相关链接

- [nanobot 原文档](../SETUP_REPORT.md)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [SSE 规范](https://html.spec.whatwg.org/multipage/server-sent-events.html)

---

_最后更新：2026-03-14_
_🐂🐎 牛马出品_
