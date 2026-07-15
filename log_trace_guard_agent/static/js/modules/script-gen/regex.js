/**
 * 正则生成页面
 */
window.Pages = window.Pages || {};
window.PageInit = window.PageInit || {};

window.Pages['regex'] = () => `
  <div class="main-header">
    <h1 class="main-title">正则生成</h1>
    <p class="main-subtitle">根据攻防场景生成正则规则</p>
  </div>

  <div class="card">
    <div class="form-group">
      <label class="form-label">攻防场景</label>
      <input id="regex-scenario" class="input" placeholder="如: 检测SSH暴力破解, SQL注入攻击">
    </div>
    <div class="form-group">
      <label class="form-label">日志样本（可选）</label>
      <textarea id="regex-sample" class="input" placeholder="粘贴日志样本，帮助生成更精确的正则..." style="min-height: 80px; font-family: var(--font-code); font-size: 11px;"></textarea>
    </div>
    <div class="form-group">
      <label class="form-label">设备类型（可选）</label>
      <select id="regex-type" class="input">
        <option value="">自动识别</option>
        <option value="ssh">SSH</option>
        <option value="web">Web</option>
        <option value="waf">WAF</option>
        <option value="firewall">防火墙</option>
        <option value="db">数据库</option>
      </select>
    </div>
    <button id="regex-btn" class="btn btn-primary">生成正则</button>
  </div>

  <div id="regex-result" class="result-area" style="display: none;">
    <div class="result-area-header">
      <span class="result-area-title">生成结果</span>
    </div>
    <div id="regex-result-content"></div>
  </div>
`;

window.PageInit['regex'] = () => {
  const scenarioInput = document.getElementById('regex-scenario');
  const sampleInput = document.getElementById('regex-sample');
  const typeSelect = document.getElementById('regex-type');
  const btn = document.getElementById('regex-btn');
  const resultArea = document.getElementById('regex-result');
  const resultContent = document.getElementById('regex-result-content');

  btn.addEventListener('click', async () => {
    const scenario = scenarioInput.value.trim();
    const logSample = sampleInput.value.trim();
    const deviceType = typeSelect.value;

    if (!scenario) {
      alert('请输入攻防场景');
      return;
    }

    btn.disabled = true;
    btn.textContent = '生成中...';
    resultArea.style.display = 'none';

    const result = await api.scriptGen.regex(scenario, logSample, deviceType);

    btn.disabled = false;
    btn.textContent = '生成正则';

    if (result.code === 0) {
      resultArea.style.display = 'block';
      const data = result.data;
      
      let html = '';
      
      if (data.regexes && data.regexes.length > 0) {
        data.regexes.forEach((item, index) => {
          html += '<div class="regex-item">';
          html += '<div class="regex-header">';
          html += `<span class="regex-name">${index + 1}. ${item.name}</span>`;
          html += `<button class="btn btn-sm btn-ghost" onclick="navigator.clipboard.writeText('${item.pattern.replace(/'/g, "\\'")}')">复制</button>`;
          html += '</div>';
          html += `<div class="regex-pattern">${item.pattern}</div>`;
          html += '<div class="regex-meta">';
          html += `<span>优先级: ${item.priority}</span>`;
          if (item.description) {
            html += `<span>${item.description}</span>`;
          }
          html += '</div>';
          if (item.match_example) {
            html += `<div style="margin-top: 8px; font-size: 11px; color: var(--n-500);">示例: <code style="background: var(--n-100); padding: 2px 4px; border-radius: 2px;">${item.match_example}</code></div>`;
          }
          html += '</div>';
        });
      } else {
        html = '<div class="empty-state"><div class="empty-state-title">未生成正则规则</div></div>';
      }
      
      resultContent.innerHTML = html;
    } else {
      alert(`生成失败: ${result.msg}`);
    }
  });
};
