# AI行动营微信公众号内容引擎 MVP

自动采集公开 RSS 热点，筛选 AI、Agent、创业主题，生成微信公众号文章；配置公众号开发凭证后，自动保存到草稿箱。

## 流程

1. 采集 RSS 热点。
2. 按关键词筛选排序。
3. 调用 OpenAI 生成标题、摘要、正文 HTML 和来源清单。
4. 校验标题长度、字段和来源 URL。
5. 保存 JSON，并可调用微信公众号草稿接口。

## 启动

```bash
cd tools/wechat-content-engine
python -m venv .venv
# Windows: .venv\\Scripts\\activate
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python content_engine.py
```

## 配置

- `OPENAI_API_KEY`：模型密钥。
- `WECHAT_APP_ID`、`WECHAT_APP_SECRET`：公众号开发者凭证。
- `WECHAT_COVER_MEDIA_ID`：公众号永久封面素材 ID。
- `NEWS_RSS_URLS`：逗号分隔的 RSS 地址。

未配置微信参数时，只生成本地文章 JSON，不写入草稿箱。

## 微信侧准备

公众号必须具备草稿接口权限；部署服务器出口 IP 需要加入公众号后台白名单；封面图应先上传为永久素材并取得 media_id。

## 下一阶段

增加搜索 API、事实核验、敏感词检查、选题后台、人工确认、定时任务、多平台改写和发布日志。
