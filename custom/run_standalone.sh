#!/bin/bash
# 🐂🐎 牛马独立服务启动脚本
# 不修改任何 nanobot 官方代码

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 使用 nanobot 的虚拟环境
source ../nanobot/venv/bin/activate

# 添加 workspace 到 PYTHONPATH
export PYTHONPATH="/home/admin/openclaw/workspace:$PYTHONPATH"

# 启动服务
echo "🐂🐎 启动牛马独立 HTTP 服务..."
echo "📍 监听地址：http://0.0.0.0:8001"
echo "📚 API 文档：http://localhost:8001/docs"
echo "🧪 测试页面：http://localhost:8001/stream_test.html"
echo ""
echo "✅ 不修改任何 nanobot 官方代码"
echo ""

python standalone_server.py
