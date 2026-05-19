# JobsDB Insight Web

贴入 JobsDB 岗位链接，秒查申请人数、附简历率、Cover Letter 率。

## 用户使用

打开网页 → 粘贴岗位链接 → 查看竞争数据。**三步，5秒。**

不需要任何技术知识，不需要安装任何东西。

## 部署

### 1. 后端（Render.com / Railway / VPS）

```bash
cd backend
pip install -r requirements.txt
```

**设置环境变量 `JOBSDB_SOL_ID`**（从你已登录 JobsDB 的浏览器中获取）：

> 登录 hk.jobsdb.com → F12 → Application → Cookies → `sol_id` → 复制值

```bash
export JOBSDB_SOL_ID="你的sol_id"
python app.py
# → 运行在 http://localhost:8899
```

### 2. 前端（GitHub Pages）

修改 `frontend/config.js` 中的 `API_URL` 为后端地址，然后部署到 GitHub Pages。

## 架构

```
用户 → 粘贴链接 → GitHub Pages ──GET /api/job?id=xxx──→ FastAPI 后端
                                                        │
                                                        │ JOBSDB_SOL_ID
                                                        ▼
                                                  JobsDB GraphQL API
                                                        │
                                                        ▼
                                                  申请人数 · 简历率 · Cover率
```

## 技术栈

- 前端: 纯静态 HTML/CSS/JS (GitHub Pages)
- 后端: Python FastAPI (Render / Railway / fly.io)
- 认证: `sol_id` cookie 内嵌在服务端，用户无感知
