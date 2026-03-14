"""
🐂🐎 sitecustomize - Python 启动时自动执行
自动 patch ChannelManager，添加 HTTP Channel
"""

import sys
from pathlib import Path

workspace = Path("/home/admin/openclaw/workspace")
if str(workspace) not in sys.path:
    sys.path.insert(0, str(workspace))

try:
    from loguru import logger
    from nanobot.channels.manager import ChannelManager
    
    original = ChannelManager._init_channels
    
    def patched(self):
        original(self)
        try:
            from custom.http_channel import HTTPChannel
            http = HTTPChannel(self.config, self.bus, host="0.0.0.0", port=8001)
            self.channels["http"] = http
            logger.info("✅ HTTP Channel enabled on 0.0.0.0:8001")
        except Exception as e:
            logger.error(f"Failed to enable HTTP Channel: {e}")
    
    ChannelManager._init_channels = patched
    logger.info("✅ ChannelManager patched")

except Exception as e:
    # 静默失败，不影响其他功能
    pass
