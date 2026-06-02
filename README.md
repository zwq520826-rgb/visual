# 职数洞见 - 本地启动说明

本项目是一个招聘数据可视化平台：

- 后端：Flask，默认端口 `5001`
- 前端：Vue 3 + Vite，目录名是 `fronted/`，默认端口 `3000`

这份 README 已按当前仓库实际情况重新整理，并在本机于 `2026-06-02` 做过启动验证。

## 先说结论

当前机器上能跑通的命令是：

```bash
conda run -n chinavis-data python app.py
```

另开一个终端：

```bash
cd fronted
npm run dev
```

启动后访问：

- 前端：`http://localhost:3000`
- 后端接口验证：`http://127.0.0.1:5001/api/overview`

## 为什么以前的 README 跑不起来

旧说明里混入了几套过时信息，主要问题有：

- 前端真实目录是 `fronted/`，不是 `frontend/`
- 前端真实开发端口是 `3000`，不是 `5173`
- 后端真实端口是 `5001`
- 直接用系统 `python3` 会失败：本机当前是 `Python 3.13.12`，而 `requirements.txt` 里的 `pandas==2.1.4` 在 `Python 3.13` 下无法正常安装

## 环境要求

### 后端

- 推荐 Python `3.10` 或 `3.11`
- 不建议直接使用 Python `3.13`
- 推荐使用现成 Conda 环境 `chinavis-data`

### 前端

- Node.js `18+`
- npm 可用

本机当前验证版本：

- Python: `3.13.12`（系统默认，不兼容本项目依赖）
- Conda 环境 `chinavis-data`: `Python 3.11.15`
- Node.js: `v24.14.1`
- npm: `11.11.0`

## 项目结构

```text
visual/
├── app.py                 # Flask 入口
├── config.py              # 数据库与服务配置
├── routes/                # API 路由
├── services/              # 业务逻辑
├── database/Q3.py         # MySQL 访问层
├── dataset/               # 本地数据文件
└── fronted/               # Vue 3 + Vite 前端
```

## 推荐启动方式

### 方案 A：直接使用本机现有 Conda 环境

先启动后端：

```bash
cd /Users/zwq/six_smester/visual_all/git_vis/visual
conda run -n chinavis-data python app.py
```

再启动前端：

```bash
cd /Users/zwq/six_smester/visual_all/git_vis/visual/fronted
npm install
npm run dev
```

如果 `fronted/node_modules` 已经存在，`npm install` 可以跳过。

### 方案 B：重新创建一个兼容的 Python 环境

如果以后不想依赖 `chinavis-data`，可以自己建一个 3.11 环境：

```bash
conda create -n job-visual python=3.11 -y
conda activate job-visual
python -m pip install -r requirements.txt
```

然后启动后端：

```bash
python app.py
```

前端仍然在 `fronted/` 目录启动：

```bash
cd fronted
npm install
npm run dev
```

## 数据库配置

数据库默认值在 `config.py` 中：

```python
DB_HOST = 'localhost'
DB_PORT = 3306
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'vision'
API_PORT = 5001
```

数据库连接参数可以通过环境变量覆盖：

```bash
export DB_HOST=localhost
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=''
export DB_NAME=vision
```

注意：

- 当前 `app.py` 中的 Flask 监听地址和端口写死为 `0.0.0.0:5001`
- `config.py` 里的 `API_HOST` 和 `API_PORT` 目前没有接入 `app.run(...)`
- 如果你要修改后端监听端口，当前应直接修改 `app.py`

## 功能依赖说明

不是所有接口都走同一套数据源：

- 大部分城市、行业、经验、Q1、Q3、Q4 聚类等接口依赖 MySQL 中的 `vision` 数据库
- `Q4` 词云接口读取本地 JSON：`dataset/dataset/第四题/city_wordcloud_data.json`

这意味着：

- 后端服务本身可以启动
- 但如果 MySQL 没准备好，很多图表接口会报数据库错误

## 已验证的启动结果

以下链路已经在当前机器验证过：

- `conda run -n chinavis-data python app.py` 可以启动 Flask
- `http://127.0.0.1:5001/api/overview` 可以返回数据
- `cd fronted && npm run dev` 可以启动 Vite
- 前端地址是 `http://localhost:3000`

## 常见问题

### 1. `ModuleNotFoundError: No module named 'flask_cors'`

说明你没有在正确的 Python 环境里安装依赖，或者用错了解释器。

优先检查：

```bash
conda run -n chinavis-data python -c "import flask, flask_cors, pandas, pymysql; print('ok')"
```

如果没有这个环境，就用 Python 3.10/3.11 重装依赖，不要直接用 Python 3.13。

### 2. `pandas==2.1.4` 安装失败

如果你看到类似下面的错误：

```text
_PyLong_AsByteArray ... too few arguments
```

基本就是在用 Python 3.13。切到 Python 3.10 或 3.11 再安装。

### 3. 前端启动了，但页面请求不到接口

检查这几项：

- 后端是否真的在 `5001` 端口运行
- 前端是否在 `fronted/` 目录启动
- 本机通过 `localhost` 或 `127.0.0.1` 访问前端时，默认会直连 `http://127.0.0.1:5001/api`
- 这条直连配置在 `fronted/src/config/appConfig.js`
- 只有非本机访问时，才会回退到 `fronted/vite.config.js` 里的 `/api` 代理

后端探活：

```bash
curl http://127.0.0.1:5001/api/overview
```

### 4. 数据库连接失败

检查：

- MySQL 是否启动
- `vision` 数据库是否存在
- 业务表 `data` 是否存在
- `config.py` 或环境变量中的账号密码是否正确

### 5. 端口被占用

默认端口：

- 前端：`3000`
- 后端：`5001`

可以先查看：

```bash
lsof -nP -iTCP:3000 -sTCP:LISTEN
lsof -nP -iTCP:5001 -sTCP:LISTEN
```

## 不推荐依赖的旧脚本

仓库里虽然还有这些文件：

- `start_platform.py`
- `start_server.py`

但它们更适合辅助启动或旧流程，不应该再当成唯一权威文档。请以本 README 的命令和端口为准。

## 一次性启动清单

如果你只是想最快重跑一遍，照着下面做：

```bash
cd /Users/zwq/six_smester/visual_all/git_vis/visual
conda run -n chinavis-data python app.py
```

新开终端：

```bash
cd /Users/zwq/six_smester/visual_all/git_vis/visual/fronted
npm run dev
```

然后打开：

```text
http://localhost:3000
```
