/**
 * 合规标准问答页面
 */
window.Pages = window.Pages || {};
window.PageInit = window.PageInit || {};

window.Pages['qa'] = () => `
  <div class="main-header">
    <h1 class="main-title">合规标准问答</h1>
    <p class="main-subtitle">智能问答，快速了解合规标准要求</p>
  </div>

  <div class="card">
    <div class="form-group">
      <label class="form-label">合规问题</label>
      <textarea id="qa-question" class="input" placeholder="输入合规相关问题...&#10;&#10;示例:&#10;- 日志需要留存多久？&#10;- 等保三级有哪些日志审计要求？&#10;- 网络安全法对日志保存有什么规定？" style="min-height: 100px;"></textarea>
    </div>
    <div class="form-group">
      <label class="form-label">资产类型（可选）</label>
      <select id="qa-asset" class="input">
        <option value="">不限</option>
        <option value="server">服务器</option>
        <option value="firewall">防火墙</option>
        <option value="web">Web应用</option>
        <option value="db">数据库</option>
        <option value="network">网络设备</option>
      </select>
    </div>
    <div class="form-group">
      <label class="form-label">标准筛选（可选）</label>
      <select id="qa-standard" class="input">
        <option value="">全部标准</option>
        <option value="等保">等保2.0</option>
        <option value="网安法">网络安全法</option>
        <option value="数安法">数据安全法</option>
        <option value="个人信息保护法">个人信息保护法</option>
      </select>
    </div>
    <button id="qa-btn" class="btn btn-primary">查询</button>
  </div>

  <div id="qa-result" class="result-area" style="display: none;">
    <div class="result-area-header">
      <span class="result-area-title">回答</span>
      <span id="qa-count" style="font-size: 12px; color: var(--n-500);"></span>
    </div>
    <div id="qa-result-content"></div>
  </div>
`;

window.PageInit['qa'] = () => {
  const questionInput = document.getElementById('qa-question');
  const assetSelect = document.getElementById('qa-asset');
  const standardSelect = document.getElementById('qa-standard');
  const btn = document.getElementById('qa-btn');
  const resultArea = document.getElementById('qa-result');
  const resultContent = document.getElementById('qa-result-content');
  const countSpan = document.getElementById('qa-count');

  btn.addEventListener('click', async () => {
    const question = questionInput.value.trim();
    const assetType = assetSelect.value;
    const standardFilter = standardSelect.value;

    if (!question) {
      alert('请输入合规问题');
      return;
    }

    btn.disabled = true;
    btn.textContent = '查询中...';
    resultArea.style.display = 'none';

    const result = await api.compliance.qa(question, assetType, standardFilter);

    btn.disabled = false;
    btn.textContent = '查询';

    if (result.code === 0) {
      resultArea.style.display = 'block';
      const data = result.data;
      
      countSpan.textContent = `匹配 ${data.matched_count || 0} 条标准`;
      
      let html = '';
      
      // 回答
      if (data.answer) {
        html += `<div class="result-card" style="margin-bottom: 16px;">
          <div style="font-size: 13px; line-height: 1.8; white-space: pre-wrap;">${data.answer}</div>
        </div>`;
      }
      
      // 相关标准
      if (data.standards && data.standards.length > 0) {
        html += '<div style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">相关标准</div>';
        data.standards.forEach(std => {
          html += `<div class="result-card" style="margin-bottom: 8px;">`;
          html += `<div style="font-size: 14px; font-weight: 600; margin-bottom: 8px;">${std.name}</div>`;
          if (std.items && std.items.length > 0) {
            std.items.forEach(item => {
              html += `<div style="padding: 8px; background: var(--n-100); border-radius: 4px; margin-bottom: 4px; font-size: 12px;">`;
              html += `<div style="font-weight: 500;">${item.requirement}</div>`;
              if (item.detail) {
                html += `<div style="color: var(--n-600); margin-top: 4px;">${item.detail}</div>`;
              }
              html += '</div>';
            });
          }
          html += '</div>';
        });
      }
      
      if (data.note) {
        html += `<div style="margin-top: 12px; padding: 8px; background: var(--n-100); border-radius: 4px; font-size: 12px; color: var(--n-600);">${data.note}</div>`;
      }
      
      resultContent.innerHTML = html;
    } else {
      alert(`查询失败: ${result.msg}`);
    }
  });

  questionInput.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'Enter') {
      btn.click();
    }
  });
};
