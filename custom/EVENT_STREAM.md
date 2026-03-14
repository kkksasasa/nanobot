# 🐂🐎 事件流文档 - 支持思考过程、工具调用

## 📋 概述

HTTP Channel 现在支持推送**详细事件**到前端，包括：

- 💭 **思考过程** (thinking)
- 🔧 **工具调用** (tool_call)
- ✅ **工具结果** (tool_result)
- 💬 **回复内容** (chunk)
- ✓ **完成** (complete)
- ❌ **错误** (error)

---

## 🔌 SSE 事件格式

### 1. 开始事件
```json
{
  "type": "start",
  "session_id": "http:user123",
  "timestamp": "2026-03-14T17:00:00"
}
```

### 2. 思考过程
```json
{
  "type": "thinking",
  "content": "让我想想这个问题...",
  "session_id": "http:user123",
  "timestamp": "2026-03-14T17:00:01"
}
```

### 3. 工具调用
```json
{
  "type": "tool_call",
  "content": "调用工具：search",
  "session_id": "http:user123",
  "timestamp": "2026-03-14T17:00:02",
  "metadata": {
    "tool_name": "search",
    "arguments": {"query": "今天天气"}
  }
}
```

### 4. 工具结果
```json
{
  "type": "tool_result",
  "content": "北京今天晴，25°C",
  "session_id": "http:user123",
  "timestamp": "2026-03-14T17:00:03",
  "metadata": {
    "tool_name": "search"
  }
}
```

### 5. 回复片段
```json
{
  "type": "chunk",
  "content": "北京",
  "session_id": "http:user123",
  "timestamp": "2026-03-14T17:00:04"
}
```

### 6. 完成
```json
{
  "type": "complete",
  "content": "北京今天天气晴朗，气温 25 度。",
  "session_id": "http:user123",
  "timestamp": "2026-03-14T17:00:10"
}
```

### 7. 错误
```json
{
  "type": "error",
  "content": "连接超时",
  "session_id": "http:user123",
  "timestamp": "2026-03-14T17:00:15"
}
```

---

## 💻 前端集成示例

### JavaScript (EventSource)

```javascript
const eventSource = new EventSource(
  'http://localhost:8001/chat/stream?message=你好&session_id=user123'
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case 'start':
      console.log('🚀 开始处理');
      break;
    
    case 'thinking':
      console.log('💭 思考中:', data.content);
      // 显示思考过程 UI
      showThinking(data.content);
      break;
    
    case 'tool_call':
      console.log('🔧 调用工具:', data.metadata.tool_name);
      // 显示工具调用动画
      showToolCalling(data.metadata);
      break;
    
    case 'tool_result':
      console.log('✅ 工具结果:', data.content);
      // 显示工具结果
      showToolResult(data.content);
      break;
    
    case 'chunk':
      console.log('💬 回复片段:', data.content);
      // 增量显示回复
      appendToResponse(data.content);
      break;
    
    case 'complete':
      console.log('✓ 完成');
      // 隐藏加载状态
      hideLoading();
      eventSource.close();
      break;
    
    case 'error':
      console.error('❌ 错误:', data.content);
      // 显示错误提示
      showError(data.content);
      eventSource.close();
      break;
  }
};
```

### React Hook

```typescript
function useNanobotStream() {
  const [events, setEvents] = useState<Event[]>([]);
  const [response, setResponse] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const sendMessage = useCallback((message: string) => {
    setIsLoading(true);
    setEvents([]);
    setResponse('');
    
    const eventSource = new EventSource(
      `http://localhost:8001/chat/stream?message=${encodeURIComponent(message)}&session_id=${sessionId}`
    );
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setEvents(prev => [...prev, data]);
      
      if (data.type === 'chunk') {
        setResponse(prev => prev + data.content);
      } else if (data.type === 'complete' || data.type === 'error') {
        setIsLoading(false);
        eventSource.close();
      }
    };
    
    return () => eventSource.close();
  }, []);
  
  return { events, response, isLoading, sendMessage };
}
```

---

## 🎨 UI 渲染示例

### 事件流面板

```html
<div class="events-panel">
  <div class="event thinking">
    <div class="event-type">💭 思考</div>
    <div class="event-content">让我分析一下这个问题...</div>
  </div>
  
  <div class="event tool_call">
    <div class="event-type">🔧 工具调用</div>
    <div class="event-content">调用工具：search</div>
    <div class="event-meta">{"query": "天气"}</div>
  </div>
  
  <div class="event tool_result">
    <div class="event-type">✅ 工具结果</div>
    <div class="event-content">北京今天晴，25°C</div>
  </div>
  
  <div class="event chunk">
    <div class="event-type">💬 回复</div>
    <div class="event-content">北京今天天气晴朗...</div>
  </div>
  
  <div class="event complete">
    <div class="event-type">✓ 完成</div>
  </div>
</div>
```

### CSS 样式

```css
.events-panel {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 15px;
  max-height: 300px;
  overflow-y: auto;
  font-family: 'Consolas', monospace;
}

.event {
  margin-bottom: 8px;
  padding: 8px;
  border-radius: 5px;
  border-left: 3px solid #667eea;
}

.event.thinking {
  background: rgba(255, 193, 7, 0.2);
  border-left-color: #ffc107;
}

.event.tool_call {
  background: rgba(33, 150, 243, 0.2);
  border-left-color: #2196f3;
}

.event.tool_result {
  background: rgba(76, 175, 80, 0.2);
  border-left-color: #4caf50;
}

.event.chunk {
  background: rgba(156, 39, 176, 0.2);
  border-left-color: #9c27b0;
}

.event.complete {
  background: rgba(76, 175, 80, 0.3);
  border-left-color: #4caf50;
}
```

---

## 🔧 后端推送事件

### 推送思考过程

```python
from nanobot.bus.events import OutboundMessage

await bus.publish_outbound(OutboundMessage(
    channel="http",
    chat_id=session_id,
    content="让我想想这个问题...",
    metadata={"type": "thinking"}
))
```

### 推送工具调用

```python
await bus.publish_outbound(OutboundMessage(
    channel="http",
    chat_id=session_id,
    content="调用工具：search",
    metadata={
        "type": "tool_call",
        "tool_name": "search",
        "tool_args": {"query": "天气"}
    }
))
```

### 推送工具结果

```python
await bus.publish_outbound(OutboundMessage(
    channel="http",
    chat_id=session_id,
    content="北京今天晴，25°C",
    metadata={
        "type": "tool_result",
        "tool_name": "search"
    }
))
```

### 推送回复片段

```python
# 流式推送
for chunk in stream_response:
    await bus.publish_outbound(OutboundMessage(
        channel="http",
        chat_id=session_id,
        content=chunk,
        metadata={"type": "chunk"}
    ))
```

### 推送完成

```python
await bus.publish_outbound(OutboundMessage(
    channel="http",
    chat_id=session_id,
    content="完整回复内容",
    metadata={"type": "complete"}
))
```

---

## 🧪 测试

### 1. 访问测试页面

```bash
# 启动服务
cd /home/admin/openclaw/workspace/custom
source ../nanobot/venv/bin/activate
export PYTHONPATH="/home/admin/openclaw/workspace:$PYTHONPATH"
python test_http_channel.py

# 访问测试页面
http://localhost:8001/stream_test.html
```

### 2. cURL 测试

```bash
curl -N "http://localhost:8001/chat/stream?message=你好"
```

### 3. 查看事件日志

```bash
# 服务会输出详细日志
2026-03-14 17:00:00 | INFO | HTTP Channel: Sent thinking event
2026-03-14 17:00:01 | INFO | HTTP Channel: Sent tool_call event
2026-03-14 17:00:02 | INFO | HTTP Channel: Sent tool_result event
```

---

## 📊 完整流程

```
用户发送消息
    ↓
HTTP Channel 接收
    ↓
发布 InboundMessage 到 MessageBus
    ↓
AgentLoop 处理
    ↓
┌─────────────────────────────────┐
│ 1. 思考 → thinking 事件          │
│ 2. 调用工具 → tool_call 事件     │
│ 3. 工具结果 → tool_result 事件   │
│ 4. 生成回复 → chunk 事件 (多次)  │
│ 5. 完成 → complete 事件          │
└─────────────────────────────────┘
    ↓
HTTP Channel send() 方法
    ↓
SSE 推送到前端
    ↓
前端渲染事件流
```

---

## 🛡️ 注意事项

1. **事件顺序** - 确保按顺序推送事件
2. **超时处理** - 设置合理的超时时间（默认 120 秒）
3. **错误处理** - 捕获异常并推送 error 事件
4. **连接管理** - 及时清理断开的连接
5. **性能优化** - 避免过小的 chunk（建议 50-100 字符）

---

## 📞 测试页面

访问 `http://localhost:8001/stream_test.html` 查看实时事件流演示！

---

_最后更新：2026-03-14_
_🐂🐎 牛马出品_
