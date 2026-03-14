#!/bin/bash
# 🐂🐎 牛马客制化服务启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 使用 nanobot 的虚拟环境
VENV_PATH="../nanobot/venv/bin/activate"

if [ ! -f "$VENV_PATH" ]; then
    echo "❌ 虚拟环境不存在：$VENV_PATH"
    echo "请先确保 nanobot 环境已正确安装"
    exit 1
fi

# 激活虚拟环境
source "$VENV_PATH"

# 检查 FastAPI 和 uvicorn
if ! python -c "import fastapi" 2>/dev/null; then
    echo "⚠️  安装 FastAPI..."
    pip install fastapi uvicorn[standard] -q
fi

# 启动服务
echo "🐂🐎 启动牛马客制化服务..."
echo "📍 监听地址：http://0.0.0.0:8001"
echo "📚 API 文档：http://localhost:8001/docs"
echo ""

# 添加父目录到 PYTHONPATH（这样 custom 才能作为模块导入）
export PYTHONPATH="$(dirname "$SCRIPT_DIR"):$PYTHONPATH"

# 启动 uvicorn
uvicorn custom.api.main:app --host 0.0.0.0 --port 8001 "$@"
