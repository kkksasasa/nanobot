#!/bin/bash
# 🐂🐎 牛马 Gateway 启动脚本（带 HTTP Channel）
# 通过 sitecustomize 应用 monkey-patch

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 使用 nanobot 的虚拟环境
source ../nanobot/venv/bin/activate

# 添加 workspace 和 custom 到 PYTHONPATH（sitecustomize 需要）
export PYTHONPATH="/home/admin/openclaw/workspace/custom:/home/admin/openclaw/workspace:$PYTHONPATH"

# 启动 gateway
echo "🐈 启动 nanobot gateway..."
echo "🐂🐎 HTTP Channel 已集成"
echo "📍 HTTP Channel: http://0.0.0.0:8001"
echo "📚 API 文档：http://localhost:8001/docs"
echo ""

nanobot gateway --verbose "$@"
