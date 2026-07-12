let currentArticle = null;
let wechatReady = false;

const $ = (id) => document.getElementById(id);
const setMessage = (text, error = false) => {
  $("message").textContent = text;
  $("message").className = error ? "error" : "";
};

async function request(url, options = {}) {
  const response = await fetch(url, {headers: {"Content-Type": "application/json"}, ...options});
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "请求失败");
  return data;
}

async function loadStatus() {
  try {
    const data = await request("/api/status");
    wechatReady = data.wechat_ready;
    $("status").innerHTML = `AI：${data.openai_ready ? "已配置" : "未配置"}<br>微信：${data.wechat_ready ? "已配置" : "未配置"}<br>模型：${data.model}`;
  } catch (error) {
    $("status").textContent = error.message;
  }
}

function selectedUrls() {
  return [...document.querySelectorAll(".source-check:checked")].map((el) => el.value);
}

function renderSources(items) {
  $("sourceCount").textContent = `${items.length} 条`;
  $("sources").classList.remove("empty");
  $("sources").innerHTML = items.map((item, index) => `
    <label class="source-item">
      <input class="source-check" type="checkbox" value="${item.url}" ${index < 8 ? "checked" : ""}>
      <div>
        <strong>${item.title}</strong>
        <p>${item.summary || "暂无摘要"}</p>
        <a href="${item.url}" target="_blank" rel="noreferrer">查看原文</a>
      </div>
    </label>`).join("");
  $("generateBtn").disabled = items.length === 0;
}

function articleFromEditor() {
  return {
    ...currentArticle,
    title: $("titleInput").value.trim(),
    digest: $("digestInput").value.trim(),
    content_html: $("contentInput").value.trim(),
  };
}

function renderArticle(article) {
  currentArticle = article;
  $("article").classList.remove("empty");
  $("article").innerHTML = `
    <label>标题<input id="titleInput" maxlength="64" value="${article.title.replaceAll('"', '&quot;')}"></label>
    <label>摘要<textarea id="digestInput" rows="3" maxlength="120">${article.digest}</textarea></label>
    <label>正文 HTML<textarea id="contentInput" rows="18">${article.content_html}</textarea></label>
    <h3>渲染预览</h3>
    <article class="wechat-preview">${article.content_html}</article>`;
  $("audit").textContent = "已通过基础检查";
  $("draftBtn").disabled = !wechatReady;
}

$("collectBtn").addEventListener("click", async () => {
  setMessage("正在采集…");
  try {
    const data = await request("/api/collect", {method: "POST"});
    renderSources(data.items);
    setMessage(`已采集 ${data.items.length} 条热点。`);
  } catch (error) { setMessage(error.message, true); }
});

$("generateBtn").addEventListener("click", async () => {
  setMessage("正在生成文章…");
  $("generateBtn").disabled = true;
  try {
    const data = await request("/api/generate", {
      method: "POST",
      body: JSON.stringify({selected_urls: selectedUrls()}),
    });
    renderArticle(data.article);
    setMessage(`文章已生成并保存为 ${data.saved}`);
  } catch (error) { setMessage(error.message, true); }
  finally { $("generateBtn").disabled = false; }
});

$("draftBtn").addEventListener("click", async () => {
  if (!confirm("确认把当前版本推送到微信公众号草稿箱？")) return;
  setMessage("正在推送草稿箱…");
  $("draftBtn").disabled = true;
  try {
    const data = await request("/api/draft", {
      method: "POST",
      body: JSON.stringify({article: articleFromEditor()}),
    });
    setMessage(`推送成功，media_id：${data.result.media_id || "已创建"}`);
  } catch (error) { setMessage(error.message, true); }
  finally { $("draftBtn").disabled = !wechatReady; }
});

loadStatus();
