# 免费云端部署指南

本文教你**不花钱**把「西安市高龄补贴监管平台」部署到公网，手机/电脑随时访问，不用每次在自己电脑上跑代码。

## 一、先了解架构

```
浏览器/手机  →  前端（静态页面，GitHub Pages/Vercel 托管）
                    │  调 API
                    ▼
               后端（FastAPI + SQLite，Render/云服务器托管）
```

- **前端**：`npm run build` 产出纯静态文件，免费托管。
- **后端**：FastAPI 进程 + SQLite 数据库文件。

## 二、环境变量清单

| 变量 | 作用 | 建议值 |
|---|---|---|
| `ELDER_TOTAL` | 老人档案条数（控制数据库大小） | 云端 `10000`，本地演示 `100000` |
| `DEEPSEEK_API_KEY` | AI 助手的密钥 | 你的 DeepSeek key |
| `JWT_SECRET` | 登录令牌签名密钥 | 随便一串随机字符 |
| `VITE_API_BASE` | 前端请求的后端地址（前端构建时用） | 如 `https://你的后端.onrender.com/api` |

## 三、数据规模配置（重要）

默认 10 万老人 ≈ 100MB 数据库，免费额度吃紧。云端用 1 万条（约 10MB）：

```powershell
# 后端启动时设置
$env:ELDER_TOTAL="10000"
$env:DEEPSEEK_API_KEY="你的key"
$env:JWT_SECRET="随便一串字符"
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

首次启动会生成数据（1 万条约 10 秒，10 万条约 1-3 分钟），之后幂等、秒开。

## 四、前端部署（免费）

### 方案 A：Vercel（推荐，最省事）

1. 把项目推到 GitHub 仓库
2. 打开 [vercel.com](https://vercel.com)，用 GitHub 登录，Import 你的仓库
3. 配置：
   - Framework Preset：`Vite`
   - Root Directory：`frontend`
   - Build Command：`npm run build`
   - Output Directory：`dist`
   - 环境变量：`VITE_API_BASE` 填你的后端地址（如 `https://xxx.onrender.com/api`）
4. Deploy，几秒钟后拿到一个 `https://xxx.vercel.app` 的网址

### 方案 B：GitHub Pages

1. 本地构建：`cd frontend && npm run build`
2. 把 `frontend/dist` 内容推到 `gh-pages` 分支
3. 仓库 Settings → Pages → 选择 `gh-pages` 分支

## 五、后端部署（免费）

### 方案 A：Render（免费，最简单）

1. 打开 [render.com](https://render.com)，GitHub 登录，New → Web Service
2. 选你的仓库，配置：
   - Runtime：`Python 3`
   - Build Command：`pip install -r requirements.txt`
   - Start Command：`uvicorn main:app --host 0.0.0.0 --port 10000`
   - Root Directory：仓库根目录（`main.py` 所在目录）
3. 环境变量（Environment 标签页）：
   - `ELDER_TOTAL=10000`
   - `DEEPSEEK_API_KEY=你的key`
   - `JWT_SECRET=随便一串字符`
4. Deploy

> ⚠️ **Render 免费版注意**：
> - 文件系统**不持久**，每次重新部署会清空 SQLite，首次启动自动重新生成数据（1 万条约 10 秒，可接受）
> - 15 分钟无访问会「休眠」，下次访问需等约 30-60 秒冷启动

### 方案 B：云服务器（更稳定，约 30-60 元/月）

如果免费平台的休眠/冷启动受不了，用阿里云/腾讯云轻量服务器（学生价更便宜）：

```bash
# 服务器上
git clone 你的仓库
cd 养老补贴
pip install -r requirements.txt
# 用 nohup 常驻后台
ELDER_TOTAL=10000 DEEPSEEK_API_KEY=xxx JWT_SECRET=xxx \
  nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 &
```

然后用 Nginx 反代 + 部署前端静态文件即可（SQLite 也能持久，不丢数据）。

## 六、前后端联调

1. 后端部署好后，拿到类似 `https://xxx.onrender.com` 的地址
2. 前端构建时设置 `VITE_API_BASE=https://xxx.onrender.com/api`
3. 重新部署前端
4. 打开前端网址，登录 `admin/admin123` 即可

## 七、常见问题

| 问题 | 原因 | 解决 |
|---|---|---|
| 接口 404/502 | 前端 API 地址没配对 | 检查 `VITE_API_BASE` |
| AI 助手报「未配置 Key」 | 没设 `DEEPSEEK_API_KEY` | 后端环境变量里加上 |
| 登录后跳回登录页 | 前后端 JWT_SECRET 不一致或跨域 | 保持同一个 `JWT_SECRET` |
| 数据每次重启变少 | 免费平台文件不持久 | 换云服务器，或接受自动重建 |
