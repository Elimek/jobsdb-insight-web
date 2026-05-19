# JobsDB Insight Web

实时查询 JobsDB HK 岗位申请人数、附简历率、Cover Letter 率的 Web 应用。

## 原理

从 JobsDB 内部 GraphQL API 获取数据，无需实际申请。仅需一次登录提取 session token。

```
登录态 → GraphQL 查询 `jobDetails.insights` → 返回实时竞争数据
                          ↓
           ApplicantCount, ApplicantsWithResumePercentage, 
           ApplicantsWithCoverLetterPercentage
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | GitHub Pages (静态站点) |
| 后端 | Python FastAPI |
| 部署 | Render.com / Railway / 任意 VPS |

## 快速开始

### 1. 提取 token

```bash
cd backend
pip install -r requirements.txt
python app.py --init
```

### 2. 启动服务器

```bash
python app.py
# → http://localhost:8899
```

### 3. 部署

**后端（Render.com）：**
1. 上传 `backend/` 到新仓库
2. Render.com → New Web Service → 选择仓库
3. Start Command: `uvicorn app:app --host 0.0.0.0 --port 10000`
4. 设置环境变量 `JOBSDB_TOKEN`（从 `.jobsdb_token.json` 获取）

**前端（GitHub Pages）：**
1. 上传 `frontend/` 到 GitHub Pages
2. 修改 `frontend/config.js` 中的 `API_URL` 为后端地址
3. 设置 GitHub Pages → Source: main branch /docs

## 项目结构

```
jobsdb-insight-web/
├── frontend/           # GitHub Pages 静态站点
│   ├── index.html      # 主页面
│   ├── config.js       # API 地址配置
│   └── style.css       # 样式
├── backend/            # FastAPI 后端
│   ├── app.py          # 主服务器
│   ├── extract_token.py # Token提取脚本
│   └── requirements.txt
└── README.md
```

## API

**单岗位查询：**
```
GET /api/job?id=91640131
```

**批量查询：**
```
GET /api/batch?ids=91640131,92206861,92136321
```

**响应格式：**
```json
{
  "id": "91640131",
  "title": "AI Product Manager / Owner (ERP project)",
  "company": "Galaxy Telecom (Hong Kong) Limited",
  "applicants": 115,
  "resume_pct": 98,
  "cover_pct": 26
}
```
