#!/usr/bin/env python3
"""
🐂🐎 牛马 Gateway 启动器
通过 monkey-patch 将 HTTP Channel 集成到 nanobot gateway

不修改任何官方代码！

使用方法：
    python -m custom.run_gateway
"""

import sys
from pathlib import Path

# 添加 workspace 到路径
workspace = Path(__file__).parent.parent
if str(workspace) not in sys.path:
    sys.path.insert(0, str(workspace))

from loguru import logger


def patch_channel_manager():
    """
    Monkey-patch ChannelManager._init_channels() 方法
    添加 HTTP Channel
    """
    logger.info("🐂🐎 Patching ChannelManager to add HTTP Channel...")
    
    from nanobot.channels.manager import ChannelManager
    
    # 保存原始方法
    original_init_channels = ChannelManager._init_channels
    
    def patched_init_channels(self):
        """扩展的 _init_channels 方法"""
        original_init_channels(self)
        
        try:
            from custom.http_channel import HTTPChannel
            
            http_channel = HTTPChannel(
                self.config,
                self.bus,
                host="0.0.0.0",
                port=8001,
            )
            
            self.channels["http"] = http_channel
            logger.info("✅ HTTP Channel enabled on 0.0.0.0:8001")
        
        except Exception as e:
            logger.error(f"Failed to enable HTTP Channel: {e}")
    
    # 应用 patch
    ChannelManager._init_channels = patched_init_channels
    logger.info("✅ ChannelManager patched successfully")


# 应用 monkey-patch
patch_channel_manager()

# 运行官方 gateway 命令
from nanobot.cli.commands import gateway

if __name__ == "__main__":
    gateway(port=18790, verbose=True)
