# 🐂🐎 牛马项目

主人让牛马写代码赚钱的项目！

## 项目结构

```
workspace/
├── backend/          # Python FastAPI 后端
│   ├── main.py
│   ├── requirements.txt
│   └── README.md
├── frontend/         # Node.js Express 前端
│   ├── server.js
│   ├── package.json
│   ├── public/
│   └── README.md
└── README.md
```

## 快速启动

### 后端 (Python)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
# 访问 http://localhost:8000
```

### 前端 (Node.js)
```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:3000
```

## 开发工具

- 后端 API 文档：http://localhost:8000/docs
- 前端页面：http://localhost:3000

---

_牛马宣言：话不多说，就是干！💪_
