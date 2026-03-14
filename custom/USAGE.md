# 🐂🐎 牛马客制化服务 - 使用文档

## 📋 概述

基于 nanobot 框架的客制化 FastAPI 聊天服务，提供 web 端可调用的 API 接口。

---

## 🚀 快速启动

### 方式 1：使用启动脚本（推荐）

```bash
cd /home/admin/openclaw/workspace
./run_custom.sh
```

### 方式 2：手动启动

```bash
cd /home/admin/openclaw/workspace/custom
source ../nanobot/venv/bin/activate
export PYTHONPATH="/home/admin/openclaw/workspace:$PYTHONPATH"
uvicorn custom.api.main:app --host 0.0.0.0 --port 8001
```

---

## 📍 访问地址

启动成功后：

- **API 文档**: http://localhost:8001/docs
- **测试页面**: http://localhost:8001/test.html
- **健康检查**: http://localhost:8001/api/health
- **服务状态**: http://localhost:8001/api/status

---

## 🔌 API 接口

### 1. POST /api/chat - 聊天接口

**请求：**
```json
{
  "message": "你好，帮我写个 Python 脚本",
  "session_id": "web:user123"
}
```

**响应：**
```json
{
  "success": true,
  "message": "好的，我来帮你写一个 Python 脚本...",
  "session_id": "web:user123",
  "timestamp": "2026-03-14T16:40:00",
  "model": "qwen3.5-plus"
}
```

**cURL 示例：**
```bash
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好", "session_id": "web:test"}'
```

---

### 2. GET /api/chat/stream - 流式聊天（SSE）

**请求：**
```bash
curl -N http://localhost:8001/api/chat/stream?message=你好
```

**响应（Server-Sent Events）：**
```
data: 好的...
data: 我来帮你...
data: [DONE]
```

---

### 3. GET /api/health - 健康检查

**响应：**
```json
{
  "status": "healthy",
  "service": "niuma-custom-api",
  "version": "0.1.4.post4",
  "timestamp": "2026-03-14T16:40:00",
  "nanobot_initialized": true
}
```

---

### 4. GET /api/status - 服务状态

**响应：**
```json
{
  "service": "niuma-custom-api",
  "initialized": true,
  "model": "qwen3.5-plus",
  "config_path": "/home/admin/.nanobot/config.json",
  "sessions": [
    {
      "key": "web:user123",
      "created_at": "2026-03-14T16:30:00",
      "updated_at": "2026-03-14T16:40:00",
      "message_count": 5
    }
  ]
}
```

---

## 💻 Web 端集成示例

### JavaScript/TypeScript

```javascript
class NiumaClient {
  constructor(baseUrl = 'http://localhost:8001') {
    this.baseUrl = baseUrl;
    this.sessionId = 'web:' + Math.random().toString(36).substr(2, 9);
  }
  
  async chat(message) {
    const response = await fetch(`${this.baseUrl}/api/chat`, {
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
}

// 使用示例
const client = new NiumaClient();
const reply = await client.chat('你好，帮我写个函数');
console.log(reply);
```

### Python

```python
import requests

class NiumaClient:
    def __init__(self, base_url='http://localhost:8001'):
        self.base_url = base_url
        self.session_id = f'web:{requests.utils.requote_uri(str(random.random()))}'
    
    def chat(self, message: str) -> str:
        response = requests.post(
            f'{self.base_url}/api/chat',
            json={'message': message, 'session_id': self.session_id}
        )
        data = response.json()
        return data['message']

# 使用示例
client = NiumaClient()
reply = client.chat('你好')
print(reply)
```

---

## 📁 项目结构

```
custom/
├── README.md           # 项目说明
├── USAGE.md            # 使用文档（本文件）
├── start.sh            # 启动脚本
├── test.html           # 测试页面
├── __init__.py         # Python 包标识
├── api/                # API 路由
│   ├── main.py         # FastAPI 主入口
│   ├── chat.py         # 聊天接口
│   └── __init__.py
├── services/           # 服务层
│   ├── nanobot_service.py  # nanobot 封装
│   └── __init__.py
└── utils/              # 工具函数
    └── __init__.py
```

---

## ⚙️ 配置说明

### nanobot 配置

服务使用 nanobot 的配置文件：
- **路径**: `~/.nanobot/config.json`
- **模型**: 在配置文件中设置（当前：qwen3.5-plus）
- **API Key**: 阿里云千问（已在配置中）

### 修改模型

编辑 `~/.nanobot/config.json`：

```json
{
  "agents": {
    "defaults": {
      "model": "qwen-max"  // 改成其他模型
    }
  }
}
```

可用模型：
- `qwen-plus` - 通义千问 Plus（平衡）
- `qwen-max` - 通义千问 Max（最强）
- `qwen3.5-plus` - 通义千问 3.5 Plus（新模型）
- `qwen-turbo` - 通义千问 Turbo（快速）

---

## 🔧 常见问题

### 1. 启动失败：ModuleNotFoundError

**解决：**
```bash
export PYTHONPATH="/home/admin/openclaw/workspace:$PYTHONPATH"
```

### 2. 无法连接 nanobot

**检查：**
```bash
# 查看 nanobot 配置
cat ~/.nanobot/config.json

# 测试 nanobot
cd /home/admin/openclaw/workspace/nanobot
source venv/bin/activate
nanobot agent -m "测试"
```

### 3. 端口被占用

**解决：** 修改启动端口
```bash
uvicorn custom.api.main:app --port 8002  # 改成其他端口
```

---

## 🛡️ 生产环境建议

1. **限制 CORS** - 修改 `api/main.py` 中的 `allow_origins`
2. **添加认证** - 实现 API Key 或 JWT 验证
3. **限流** - 添加请求频率限制
4. **日志** - 配置结构化日志
5. **监控** - 集成 Prometheus/Grafana
6. **HTTPS** - 使用 Nginx 反向代理

---

## 📞 技术支持

- **nanobot 文档**: https://github.com/HKUDS/nanobot
- **FastAPI 文档**: https://fastapi.tiangolo.com/
- **牛马出品**: 🐂🐎

---

_最后更新：2026-03-14_
