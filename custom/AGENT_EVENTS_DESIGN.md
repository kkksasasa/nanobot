# 🐂🐎 Agent 事件解析器设计文档

## 📋 概述

**不修改任何官方代码**，通过包装和回调机制，解析 AgentLoop 的所有回调信息并推送到前端。

---

## 🎯 设计目标

1. ✅ **零修改** - 不改动 nanobot 任何官方文件
2. ✅ **完整解析** - 捕获所有 AgentLoop 回调事件
3. ✅ **实时推送** - SSE 流式推送到前端
4. ✅ **易于扩展** - 在 custom 目录添加新功能

---

## 🏗️ 架构设计

### 核心组件

```
custom/
├── agent_events.py        # 事件解析器 ⭐
├── standalone_server.py   # 独立服务
└── stream_test.html       # 测试页面
```

### 类关系

```
AgentEventParser          # 解析 AgentLoop 回调
    ↓
EnhancedAgentLoop         # 包装官方 AgentLoop
    ↓
AgentLoop (官方，未修改)
```

---

## 🔍 事件类型

### 1. Thinking（思考过程）

**来源：** AgentLoop._run_agent_loop 中的 on_progress 回调

**解析：**
```python
# 提取 <think> 标签内容
<think>
让我分析一下这个问题...
需要调用搜索工具...
</think>

```

**推送事件：**
```json
{
  "type": "thinking",
  "content": "让我分析一下这个问题...",
  "session_id": "http:user1"
}
```

---

### 2. Tool Call（工具调用）

**来源：** AgentLoop._run_agent_loop 中的 tool_hint

**解析：**
```python
# 格式：web_search("query..."), read_file("path...")
tool_hint = 'web_search("今天天气"), read_file("config.json")'
```

**推送事件：**
```json
{
  "type": "tool_call",
  "content": "调用工具：web_search",
  "metadata": {
    "tool_name": "web_search",
    "arguments": {"query": "今天天气"}
  }
}
```

---

### 3. Chunk（回复片段）

**来源：** AgentLoop 的最终回复，分块推送

**推送事件：**
```json
{
  "type": "chunk",
  "content": "北京",
  "session_id": "http:user1"
}
```

---

### 4. Complete（完成）

**来源：** AgentLoop 处理完成

**推送事件：**
```json
{
  "type": "complete",
  "content": "北京今天天气晴朗，气温 25 度。",
  "session_id": "http:user1"
}
```

---

### 5. Error（错误）

**来源：** 异常捕获

**推送事件：**
```json
{
  "type": "error",
  "content": "连接超时",
  "session_id": "http:user1"
}
```

---

## 💻 实现细节

### AgentEventParser 类

```python
class AgentEventParser:
    """解析 AgentLoop 的回调事件"""
    
    def __init__(self, session_id: str, send_callback: Callable):
        self.session_id = session_id
        self.send_callback = send_callback
    
    async def on_progress(self, content: str, **kwargs):
        """处理 on_progress 回调"""
        tool_hint = kwargs.get("tool_hint", False)
        
        if tool_hint:
            await self._handle_tool_hint(content)
        else:
            await self._handle_thinking(content)
    
    async def _handle_thinking(self, content: str):
        """提取 <think> 标签内容"""
        think_pattern = re.compile(r'<think>(.*?)</think>', re.DOTALL)
        matches = think_pattern.findall(content)
        
        for thinking in matches:
            await self.send_callback(
                thinking.strip(),
                {"type": "thinking", "session_id": self.session_id}
            )
    
    async def _handle_tool_hint(self, content: str):
        """解析工具调用"""
        pattern = re.compile(r'(\w+)\("([^"]+)"\)')
        matches = pattern.findall(content)
        
        for tool_name, args in matches:
            await self.send_callback(
                f"调用工具：{tool_name}",
                {
                    "type": "tool_call",
                    "tool_name": tool_name,
                    "arguments": {"query": args}
                }
            )
```

---

### EnhancedAgentLoop 包装器

```python
class EnhancedAgentLoop:
    """增强 AgentLoop，添加事件推送"""
    
    def __init__(self, agent_loop, bus):
        self.agent = agent_loop
        self.bus = bus
    
    async def process_with_events(self, message, session_id, ...):
        """处理消息并推送详细事件"""
        
        # 创建事件解析器
        async def send_callback(content, metadata):
            await self.bus.publish_outbound(OutboundMessage(
                channel="http",
                chat_id=session_id,
                content=content,
                metadata=metadata,
            ))
        
        parser = AgentEventParser(session_id, send_callback)
        
        # 调用官方 AgentLoop，传入回调
        response = await self.agent.process_direct(
            content=message,
            session_key=session_id,
            on_progress=parser.on_progress,  # ← 关键！
        )
        
        # 分块推送回复
        for chunk in chunks:
            await send_callback(chunk, {"type": "chunk"})
```

---

## 🔄 完整流程

```
1. 用户发送消息
   ↓
2. HTTP Channel 接收
   ↓
3. EnhancedAgentLoop.process_with_events()
   ↓
4. 创建 AgentEventParser
   ↓
5. 调用官方 AgentLoop.process_direct()
   ↓
6. AgentLoop._run_agent_loop()
   ├─ 调用 LLM
   ├─ 有 tool_calls?
   │   ├─ 调用 on_progress(thought) → thinking 事件
   │   └─ 调用 on_progress(tool_hint) → tool_call 事件
   ├─ 执行工具
   └─ 返回最终回复
   ↓
7. 分块推送回复 → chunk 事件
   ↓
8. 推送完成 → complete 事件
   ↓
9. SSE 推送到前端
```

---

## 📊 事件序列示例

**用户问：** "帮我查一下北京今天的天气"

**事件流：**

```json
// 1. 开始
{"type": "start", "session_id": "http:user1"}

// 2. 思考过程
{"type": "thinking", "content": "用户想查天气，我需要调用搜索工具..."}

// 3. 工具调用
{"type": "tool_call", "content": "调用工具：web_search", "metadata": {"tool_name": "web_search", "arguments": {"query": "北京今天天气"}}}

// 4. 工具执行结果（可选，如果需要显示）
{"type": "tool_result", "content": "北京今天晴，25°C..."}

// 5-7. 回复片段
{"type": "chunk", "content": "北京"}
{"type": "chunk", "content": "今天"}
{"type": "chunk", "content": "天气晴朗，气温 25 度。"}

// 8. 完成
{"type": "complete", "content": "北京今天天气晴朗，气温 25 度。"}
```

---

## 🎨 前端渲染

### React 组件示例

```tsx
function ChatWindow() {
  const [events, setEvents] = useState<Event[]>([]);
  
  const sendMessage = (message: string) => {
    const eventSource = new EventSource(
      `/chat/stream?message=${encodeURIComponent(message)}`
    );
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setEvents(prev => [...prev, data]);
      
      // 根据类型渲染不同 UI
      if (data.type === 'thinking') {
        showThinking(data.content);
      } else if (data.type === 'tool_call') {
        showToolCalling(data.metadata);
      } else if (data.type === 'chunk') {
        appendToResponse(data.content);
      }
    };
  };
  
  return (
    <div className="chat-window">
      {events.map((event, i) => (
        <EventView key={i} event={event} />
      ))}
    </div>
  );
}

function EventView({ event }: { event: Event }) {
  switch (event.type) {
    case 'thinking':
      return <ThinkingView content={event.content} />;
    case 'tool_call':
      return <ToolCallView metadata={event.metadata} />;
    case 'chunk':
      return <ChunkView content={event.content} />;
    default:
      return null;
  }
}
```

---

## 🛡️ 设计原则

### 1. 不修改官方代码
- ✅ 所有代码在 `custom/` 目录
- ✅ 通过包装和回调实现扩展
- ✅ 官方代码保持原样

### 2. 松耦合
- ✅ AgentEventParser 独立于 AgentLoop
- ✅ 通过回调函数通信
- ✅ 易于替换/升级

### 3. 可扩展
- ✅ 添加新事件类型只需修改 AgentEventParser
- ✅ 添加新解析逻辑不影响其他部分
- ✅ 支持多种推送渠道

---

## 🧪 测试

### 启动服务
```bash
cd /home/admin/openclaw/workspace/custom
./run_standalone.sh
```

### 访问测试页面
```
http://localhost:8001/stream_test.html
```

### cURL 测试
```bash
curl -N "http://localhost:8001/chat/stream?message=帮我查北京天气"
```

---

## 📋 文件清单

| 文件 | 说明 | 状态 |
|------|------|------|
| `agent_events.py` | 事件解析器 | ✅ 完成 |
| `standalone_server.py` | 独立服务（已更新） | ✅ 完成 |
| `stream_test.html` | 测试页面 | ✅ 完成 |
| `AGENT_EVENTS_DESIGN.md` | 本文档 | ✅ 完成 |

---

## 🔮 未来扩展

### 1. 更多事件类型
- memory_read - 读取记忆
- memory_write - 写入记忆
- subagent_spawn - 创建子代理
- mcp_tool_call - MCP 工具调用

### 2. 事件过滤
```python
# 只推送特定类型的事件
parser.filter_events(['thinking', 'tool_call', 'chunk'])
```

### 3. 事件聚合
```python
# 合并连续的 chunk 事件
parser.aggregate_chunks(window_ms=100)
```

---

_最后更新：2026-03-14_
_🐂🐎 牛马出品 - 不修改官方代码 ✅_
