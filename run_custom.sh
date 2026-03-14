#!/bin/bash
# 🐂🐎 快速启动牛马客制化服务

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CUSTOM_DIR="$SCRIPT_DIR/custom"

cd "$CUSTOM_DIR"

# 使用 nanobot 的虚拟环境
source "$SCRIPT_DIR/nanobot/venv/bin/activate"

# 添加 workspace 到 PYTHONPATH
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# 启动服务
echo "🐂🐎 启动牛马客制化服务..."
echo "📍 监听地址：http://0.0.0.0:8001"
echo "📚 API 文档：http://localhost:8001/docs"
echo "🧪 测试页面：http://localhost:8001/test.html"
echo ""

uvicorn custom.api.main:app --host 0.0.0.0 --port 8001 --reload
