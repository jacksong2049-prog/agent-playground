# AI行动营微信公众号内容引擎 MVP

自动采集公开 RSS 热点，筛选 AI、Agent、创业主题，生成微信公众号文章；经增强审核、人工预览和修改后，可保存到公众号草稿箱。

## 当前流程

1. 网页控制台采集全球 RSS 热点。
2. 人工勾选值得写的来源。
3. 调用 OpenAI 生成标题、摘要、正文 HTML 和来源清单。
4. 执行字段、来源、敏感词、绝对化表述、数字和引语风险检查。
5. 在网页中预览、修改并重新审核文章。
6. 上传封面到微信公众号永久素材库，或使用已有 `media_id`。
7. 勾选人工复核确认后，保存到微信公众号草稿箱。

## Windows 一键使用

首次使用：

1. 下载仓库并切换到 `feat/wechat-content-engine-mvp` 分支。
2. 打开 `tools\wechat-content-engine\windows`。
3. 双击 `install.bat`。
4. 在自动打开的 `.env` 中填写 OpenAI 和微信公众号参数。
5. 双击 `start.bat`。
6. 浏览器访问 `http://127.0.0.1:8000`。

辅助脚本：

- `install.bat`：创建虚拟环境、安装依赖、创建 `.env`、运行测试。
- `start.bat`：启动服务并打开浏览器。
- `stop.bat`：停止本机 8000 端口上的服务。
- `update.bat`：安全拉取最新分支；本地有未提交修改时自动停止。
- `diagnose.bat`：生成不包含密钥明文的诊断报告并自动打开。

## 手动启动

```bash
cd tools/wechat-content-engine
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

浏览器访问 `http://localhost:8000`。

## 自动化测试

```bash
python -m pytest -q
```

## 配置

- `OPENAI_API_KEY`：模型密钥。
- `OPENAI_MODEL`：默认 `gpt-5-mini`。
- `WECHAT_APP_ID`、`WECHAT_APP_SECRET`：公众号开发者凭证。
- `WECHAT_COVER_MEDIA_ID`：可选，已有永久封面素材 ID。
- `NEWS_RSS_URLS`：逗号分隔的 RSS 地址。
- `TOPIC_KEYWORDS`：热点排序关键词。
- `CUSTOM_SENSITIVE_WORDS`：自定义敏感词，逗号分隔。

未配置微信参数时，网页仍可采集、生成、审核和预览文章，但不能推送草稿箱。

## 微信侧准备

公众号需要具备草稿和永久素材接口权限；运行程序的公网出口 IP 要加入公众号后台白名单。网页可上传本地封面图并自动取得 `media_id`。

## Docker

```bash
docker compose up -d --build
docker compose logs -f web
docker compose down
```

## 安全边界

- 不在仓库提交任何真实密钥。
- 默认不会自动推送，必须人工点击并勾选复核确认。
- 推送接口会在服务端再次审核，不能通过绕过前端规避。
- 生成文章只能引用本轮采集到的来源 URL。
- 每次生成都会在 `output/` 留存 JSON 版本。
- 定时任务只生成候选稿，不自动发布。
