# Render 免费版部署指南（完全免费 · Vue + FastAPI）

用 Render 免费版把前后端都部署到云端，评审在线访问，不花一分钱。

## 一、把项目推到 GitHub

1. GitHub 新建一个仓库（例如 `subsidy-platform`，选 Public）
2. 在项目目录 `C:\Users\29515\Desktop\养老补贴` 下打开终端：

```bash
git init
git add .
git commit -m "init"
git branch -M main
git remote add origin https://github.com/你的用户名/subsidy-platform.git
git push -u origin main
```

> 如果项目里有不想上传的东西（node_modules、data、.env 等），确认 `.gitignore` 已忽略它们。

## 二、Render 注册 + 连 GitHub

1. 打开 `render.com` → **Sign up**（直接用 GitHub 账号登录最方便）
2. 登录后授权 Render 访问你的 GitHub 仓库

## 三、Blueprint 一键部署

1. Render 控制台 → 右上角 **New** → **Blueprint**
2. 选择你刚推的仓库 `subsidy-platform`
3. Render 会自动读取仓库根目录的 `render.yaml`，创建 **2 个服务**：
   - `subsidy-backend`（后端 FastAPI）
   - `subsidy-frontend`（前端 Vue 静态站点）

## 四、等待部署

- 首次部署约 5~10 分钟（拉代码 + 装依赖 + 前端 build）
- 后端首次启动会**自动生成演示数据**（约 1~3 分钟，100 万条记录）

## 五、访问地址

- **前端**：`https://subsidy-frontend.onrender.com`
- **后端 API**：`https://subsidy-backend.onrender.com`

把前端地址发给评审即可。

## 六、免费版的两个坑（务必知道）

| 坑 | 影响 | 缓解 |
|---|---|---|
| **休眠** | 后端 15 分钟无人访问会休眠，唤醒等 40~60 秒 | 评审第一次打开会转圈半分钟，属正常，等一会即可 |
| **临时盘** | SQLite 数据在临时盘，**重新部署（push 新代码）或重启后数据会丢**，自动重新生成 | 演示期间别频繁 push 就行 |

## 七、配置密钥（建议）

Render 控制台 → `subsidy-backend` → **Environment** → 添加变量：

```
JWT_SECRET = 换成你的随机字符串
DEEPSEEK_API_KEY = 换成你的key（不配则 AI 助手不可用）
```

改完点 **Save Changes** 自动重启生效。

## 八、更新代码后重新部署

```bash
git add .
git commit -m "update"
git push
```

Render 会自动检测到 push 并重新构建部署（此时数据会重新生成，等 1~3 分钟）。

## 常见问题

| 问题 | 解决 |
|---|---|
| 前端打不开、白屏 | 等 40~60 秒（后端在唤醒），刷新 |
| 前端 404（刷新子页面） | render.yaml 里已配 rewrite，若还 404 检查 Blueprint 是否用了最新 render.yaml |
| AI 助手报 502 | 没配 DEEPSEEK_API_KEY，去 Environment 加 |
