# AI行动营微信公众号内容引擎 MVP

自动采集公开 RSS 热点，筛选 AI、Agent、创业主题，生成微信公众号文章；经人工预览和修改后，可保存到公众号草稿箱。

## 当前流程

1. 网页控制台采集全球 RSS 热点。
2. 人工勾选值得写的来源。
3. 调用 OpenAI 生成标题、摘要、正文 HTML 和来源清单。
4. 校验标题长度、字段和来源 URL。
5. 在网页中预览、修改文章。
6. 人工确认后调用微信公众号草稿接口。

## 启动网页控制台

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

仍可通过以下命令直接执行一次完整流水线：

```bash
python content_engine.py
```

## 配置

- `OPENAI_API_KEY`：模型密钥。
- `OPENAI_MODEL`：默认 `gpt-5-mini`。
- `WECHAT_APP_ID`、`WECHAT_APP_SECRET`：公众号开发者凭证。
- `WECHAT_COVER_MEDIA_ID`：公众号永久封面素材 ID。
- `NEWS_RSS_URLS`：逗号分隔的 RSS 地址。
- `TOPIC_KEYWORDS`：热点排序关键词。

未配置微信参数时，网页仍可采集、生成和预览文章，但“推送草稿箱”按钮不可用。

## 微信侧准备

公众号需要具备草稿接口权限；部署服务器出口 IP 要加入公众号后台白名单；封面图需先上传为永久素材并取得 `media_id`。

## 安全边界

- 不在仓库提交任何真实密钥。
- 默认不会自动推送，必须人工点击确认。
- 生成文章只能引用本轮采集到的来源 URL。
- 每次生成都会在 `output/` 留存 JSON 版本。

## 下一阶段

增加搜索 API、二次事实核验、敏感词检查、自动封面生成与上传、定时任务、发布日志，以及小红书和视频号改写。
