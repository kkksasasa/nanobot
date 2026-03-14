# 🐂🐎 牛马客制化代码

**老板的专属代码库** - 这里存放定制化开发的代码

## 目录结构

```
custom/
├── README.md           # 本文件
├── api/                # FastAPI 接口
│   ├── main.py         # 主入口
│   ├── chat.py         # 聊天接口
│   └── __init__.py
├── services/           # 服务层
│   ├── nanobot_service.py  # nanobot 集成服务
│   └── __init__.py
├── utils/              # 工具函数
│   └── __init__.py
└── requirements.txt    # Python 依赖
```

## 快速启动

```bash
cd /home/admin/openclaw/workspace/custom
source ../nanobot/venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8001
```

## API 文档

启动后访问：http://localhost:8001/docs

## 接口列表

- `POST /api/chat` - 聊天接口（web 端调用）
- `GET /api/health` - 健康检查
- `GET /api/status` - 服务状态

---

_牛马出品，必属精品 🐂🐎_
