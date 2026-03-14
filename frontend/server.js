const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// CORS 配置
app.use(cors({
  origin: ['http://localhost:8000', 'http://127.0.0.1:8000'],
  credentials: true
}));

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// 首页
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// API 测试
app.get('/api/health', (req, res) => {
  res.json({ status: 'healthy', service: 'frontend' });
});

// 代理后端 API (可选)
app.use('/api/backend', async (req, res) => {
  try {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    const response = await fetch(`${backendUrl}${req.path}`);
    const data = await response.json();
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: 'Backend unavailable' });
  }
});

app.listen(PORT, () => {
  console.log(`🐂🐎 牛马前端已启动 on http://localhost:${PORT}`);
});
