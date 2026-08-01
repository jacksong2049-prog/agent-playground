let currentArticle = null;
let wechatCredentialsReady = false;
let coverMediaId = "";
let latestAudit = null;

const $ = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#39;");
const setMessage = (text, error = false) => {
  $("message").textContent = text;
  $("message").className = error ? "error" : "";
};

async function request(url, options = {}) {
  const headers = options.body instanceof FormData ? {} : {"Content-Type": "application/json"};
  const adminToken = sessionStorage.getItem("adminToken");
  if (adminToken) headers.Authorization = `Bearer ${adminToken}`;
  const response = await fetch(url, {headers, ...options});
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "请求失败");
  return data;
}

async function loadStatus() {
  try {
    const data = await request("/api/status");
    wechatCredentialsReady = data.wechat_credentials_ready;
    $("status").innerHTML = `AI：${data.openai_ready ? "已配置" : "未配置"}<br>微信凭证：${data.wechat_credentials_ready ? "已配置" : "未配置"}<br>封面：${data.cover_ready ? "已就绪" : "未就绪"}<br>模型：${data.model}`;
    if (data.cover_ready) $("coverStatus").textContent = "封面：已配置或已上传";
    updateDraftButton();
  } catch (error) {
    $("status").textContent = error.message;
  }
}

function updateDraftButton() {
  const hasCover = Boolean(coverMediaId) || $("coverStatus").textContent.includes("已配置");
  const auditPassed = latestAudit && latestAudit.passed;
  const warningsAccepted = !latestAudit || latestAudit.warnings === 0 || $("warningAck").checked;
  $("draftBtn").disabled = !(currentArticle && wechatCredentialsReady && hasCover && auditPassed && warningsAccepted);
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
        <strong>${escapeHtml(item.title)}</strong>
        <p>${escapeHtml(item.summary || "暂无摘要")}</p>
        <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">查看原文</a>
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

function renderAudit(report) {
  latestAudit = report;
  const label = report.passed ? `通过：${report.warnings} 个警告` : `未通过：${report.errors} 个错误`;
  $("audit").textContent = label;
  $("auditIssues").classList.remove("empty");
  $("auditIssues").innerHTML = report.issues.length
    ? report.issues.map((issue) => `<div class="audit-item ${issue.level}"><strong>${issue.level === "error" ? "错误" : "警告"}</strong> ${escapeHtml(issue.message)}${issue.excerpt ? ` <code>${escapeHtml(issue.excerpt)}</code>` : ""}</div>`).join("")
    : '<div class="audit-item success">未发现明显风险。</div>';
  updateDraftButton();
}

function renderArticle(article, report) {
  currentArticle = article;
  $("article").classList.remove("empty");
  $("article").innerHTML = `
    <label>标题<input id="titleInput" maxlength="64" value="${escapeHtml(article.title)}"></label>
    <label>摘要<textarea id="digestInput" rows="3" maxlength="120">${escapeHtml(article.digest)}</textarea></label>
    <label>正文 HTML<textarea id="contentInput" rows="18">${escapeHtml(article.content_html)}</textarea></label>
    <h3>渲染预览</h3>
    <article class="wechat-preview">${article.content_html}</article>`;
  $("auditBtn").disabled = false;
  $("warningAck").checked = false;
  renderAudit(report);
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
    renderArticle(data.article, data.audit);
    setMessage(`文章已生成并保存为 ${data.saved}`);
  } catch (error) { setMessage(error.message, true); }
  finally { $("generateBtn").disabled = false; }
});

$("auditBtn").addEventListener("click", async () => {
  setMessage("正在重新审核当前版本…");
  try {
    const data = await request("/api/audit", {
      method: "POST",
      body: JSON.stringify({article: articleFromEditor()}),
    });
    currentArticle = articleFromEditor();
    renderAudit(data.audit);
    setMessage("审核完成。请逐项核对警告。");
  } catch (error) { setMessage(error.message, true); }
});

$("coverInput").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  setMessage("正在上传封面到微信公众号永久素材库…");
  try {
    const data = await request("/api/cover", {method: "POST", body: form});
    coverMediaId = data.media_id;
    $("coverStatus").textContent = `封面：上传成功（media_id ${data.media_id.slice(0, 10)}…）`;
    setMessage("封面上传成功。");
    updateDraftButton();
  } catch (error) { setMessage(error.message, true); }
  finally { event.target.value = ""; }
});

$("warningAck").addEventListener("change", updateDraftButton);

$("saveTokenBtn").addEventListener("click", () => {
  const token = $("adminTokenInput").value.trim();
  if (token) sessionStorage.setItem("adminToken", token);
  else sessionStorage.removeItem("adminToken");
  setMessage(token ? "管理口令已在当前浏览器会话中保存。" : "管理口令已清除。");
});

$("draftBtn").addEventListener("click", async () => {
  if (!confirm("确认已核对来源、数字、引语和当前正文，并推送到微信公众号草稿箱？")) return;
  setMessage("正在进行最终审核并推送草稿箱…");
  $("draftBtn").disabled = true;
  try {
    const data = await request("/api/draft", {
      method: "POST",
      body: JSON.stringify({
        article: articleFromEditor(),
        acknowledged_warnings: $("warningAck").checked,
        cover_media_id: coverMediaId,
      }),
    });
    setMessage(`推送成功，media_id：${data.result.media_id || "已创建"}`);
  } catch (error) { setMessage(error.message, true); }
  finally { updateDraftButton(); }
});

loadStatus();
