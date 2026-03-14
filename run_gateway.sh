#!/bin/bash
# 🐂🐎 启动 nanobot gateway（带 HTTP Channel）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/nanobot"

# 激活虚拟环境
source venv/bin/activate

# 添加 workspace 到 PYTHONPATH（让 nanobot 能找到 custom 模块）
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# 启动 gateway
echo "🐈 启动 nanobot gateway..."
echo "📍 HTTP Channel: http://0.0.0.0:8001"
echo "📚 API 文档：http://localhost:8001/docs"
echo "🧪 测试：http://localhost:8001/chat/stream?message=你好"
echo ""

nanobot gateway "$@"
