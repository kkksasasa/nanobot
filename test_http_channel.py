#!/usr/bin/env python3
"""测试 HTTP Channel"""

import asyncio
import sys
from pathlib import Path

# 添加 workspace 到路径
workspace = Path(__file__).parent
if str(workspace) not in sys.path:
    sys.path.insert(0, str(workspace))

from nanobot.config.loader import load_config
from nanobot.bus.queue import MessageBus
from custom.http_channel import HTTPChannel


async def main():
    print("🐂🐎 加载配置...")
    config = load_config()
    
    print("🐂🐎 创建消息总线...")
    bus = MessageBus()
    
    print("🐂🐎 创建 HTTP Channel...")
    channel = HTTPChannel(config, bus, host='0.0.0.0', port=8001)
    
    print("🚀 启动 HTTP Channel...")
    print("📍 访问：http://localhost:8001/health")
    print("📚 API 文档：http://localhost:8001/docs")
    print("按 Ctrl+C 停止")
    print()
    
    try:
        await channel.start()
    except KeyboardInterrupt:
        print("\n🛑 停止服务...")
        await channel.stop()


if __name__ == "__main__":
    asyncio.run(main())
