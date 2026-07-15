/**
 * ES 查询生成页面
 */
window.Pages = window.Pages || {};
window.PageInit = window.PageInit || {};

window.Pages['es-query'] = () => `
  <div class="main-header">
    <h1 class="main-title">ES 查询生成</h1>
    <p class="main-subtitle">根据自然语言生成 Elasticsearch 查询语句</p>
  </div>

  <div class="card">
    <div class="form-group">
      <label class="form-label">搜索场景</label>
      <input id="es-scenario" class="input" placeholder="如: 查询过去1小时SSH暴力破解日志">
    </div>
    <div class="form-group">
      <label class="form-label">索引模式（可选）</label>
      <input id="es-index" class="input" placeholder="如: ssh-*, log-*">
    </div>
    <div class="form-group">
      <label class="form-label">时间范围（可选）</label>
      <select id="es-time" class="input">
        <option value="">自动</option>
        <option value="1h">1小时</option>
        <option value="24h">24小时</option>
        <option value="7d">7天</option>
        <option value="30d">30天</option>
      </select>
    </div>
    <button id="es-btn" class="btn btn-primary">生成查询</button>
  </div>

  <div id="es-result" class="result-area" style="display: none;">
    <div class="result-area-header">
      <span class="result-area-title">生成结果</span>
      <button id="es-copy" class="btn btn-sm btn-secondary">复制查询</button>
    </div>
    <div id="es-result-content"></div>
  </div>
`;

window.PageInit['es-query'] = () => {
  const scenarioInput = document.getElementById('es-scenario');
  const indexInput = document.getElementById('es-index');
  const timeSelect = document.getElementById('es-time');
  const btn = document.getElementById('es-btn');
  const copyBtn = document.getElementById('es-copy');
  const resultArea = document.getElementById('es-result');
  const resultContent = document.getElementById('es-result-content');

  let generatedQuery = '';

  btn.addEventListener('click', async () => {
    const scenario = scenarioInput.value.trim();
    const indexPattern = indexInput.value.trim();
    const timeRange = timeSelect.value;

    if (!scenario) {
      alert('请输入搜索场景');
      return;
    }

    btn.disabled = true;
    btn.textContent = '生成中...';
    resultArea.style.display = 'none';

    const result = await api.scriptGen.esQuery(scenario, indexPattern, timeRange);

    btn.disabled = false;
    btn.textContent = '生成查询';

    if (result.code === 0) {
      resultArea.style.display = 'block';
      const data = result.data;
      generatedQuery = data.query || '';
      
      let html = '';
      
      if (generatedQuery) {
        html += '<div class="code-block">';
        html += '<div class="code-block-header">';
        html += '<span class="code-block-lang">Elasticsearch DSL</span>';
        html += '</div>';
        html += `<pre>${escapeHtml(generatedQuery)}</pre>`;
        html += '</div>';
      }
      
      if (data.explanation) {
        html += '<div style="margin-top: 16px; padding: 12px; background: var(--n-100); border-radius: 6px; font-size: 13px;">';
        html += `<div style="font-weight: 600; margin-bottom: 8px;">查询逻辑说明</div>`;
        html += `<div style="color: var(--n-600);">${data.explanation}</div>`;
        html += '</div>';
      }
      
      resultContent.innerHTML = html;
    } else {
      alert(`生成失败: ${result.msg}`);
    }
  });

  copyBtn.addEventListener('click', () => {
    if (generatedQuery) {
      navigator.clipboard.writeText(generatedQuery);
      copyBtn.textContent = '已复制';
      setTimeout(() => { copyBtn.textContent = '复制查询'; }, 2000);
    }
  });
};

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
