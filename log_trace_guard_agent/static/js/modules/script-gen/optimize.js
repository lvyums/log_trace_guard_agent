/**
 * 脚本优化页面
 */
window.Pages = window.Pages || {};
window.PageInit = window.PageInit || {};

window.Pages['optimize'] = () => `
  <div class="main-header">
    <h1 class="main-title">脚本优化</h1>
    <p class="main-subtitle">分析并优化正则、ES查询、SQL脚本</p>
  </div>

  <div class="card">
    <div class="form-group">
      <label class="form-label">脚本类型</label>
      <select id="opt-type" class="input">
        <option value="regex">正则表达式</option>
        <option value="es_query">ES 查询</option>
        <option value="sql">SQL</option>
      </select>
    </div>
    <div class="form-group">
      <label class="form-label">攻防场景（可选）</label>
      <input id="opt-scenario" class="input" placeholder="如: SSH暴力破解检测">
    </div>
    <div class="form-group">
      <label class="form-label">粘贴你的脚本</label>
      <textarea id="opt-script" class="input" placeholder="粘贴需要优化的正则/ES查询/SQL..." style="min-height: 120px; font-family: var(--font-code); font-size: 11px;"></textarea>
    </div>
    <button id="opt-btn" class="btn btn-primary">分析优化</button>
  </div>

  <div id="opt-result" class="result-area" style="display: none;">
    <div class="result-area-header">
      <span class="result-area-title">优化结果</span>
      <button id="opt-copy" class="btn btn-sm btn-secondary">复制优化后</button>
    </div>
    <div id="opt-result-content"></div>
  </div>
`;

window.PageInit['optimize'] = () => {
  const typeSelect = document.getElementById('opt-type');
  const scenarioInput = document.getElementById('opt-scenario');
  const scriptInput = document.getElementById('opt-script');
  const btn = document.getElementById('opt-btn');
  const copyBtn = document.getElementById('opt-copy');
  const resultArea = document.getElementById('opt-result');
  const resultContent = document.getElementById('opt-result-content');

  let optimizedScript = '';

  btn.addEventListener('click', async () => {
    const script = scriptInput.value.trim();
    const scriptType = typeSelect.value;
    const scenario = scenarioInput.value.trim();

    if (!script) {
      alert('请输入脚本');
      return;
    }

    btn.disabled = true;
    btn.textContent = '分析中...';
    resultArea.style.display = 'none';

    const result = await api.scriptGen.optimize(script, scriptType, scenario);

    btn.disabled = false;
    btn.textContent = '分析优化';

    if (result.code === 0) {
      resultArea.style.display = 'block';
      const data = result.data;
      optimizedScript = data.optimized || '';
      
      let html = '';
      
      // 评分
      if (data.score !== undefined) {
        const scoreColor = data.score >= 80 ? 'var(--success)' : 
                          data.score >= 60 ? 'var(--warning)' : 'var(--error)';
        html += `<div style="margin-bottom: 16px; padding: 12px; background: var(--n-100); border-radius: 6px;">`;
        html += `<div style="font-size: 13px; font-weight: 600; margin-bottom: 4px;">原始评分</div>`;
        html += `<div style="font-size: 24px; font-weight: 700; color: ${scoreColor};">${data.score}/100</div>`;
        html += '</div>';
      }
      
      // 发现问题
      if (data.issues && data.issues.length > 0) {
        html += '<div style="margin-bottom: 16px;"><div style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">发现问题</div>';
        html += '<ul style="margin: 0; padding-left: 16px; font-size: 13px; color: var(--error);">';
        data.issues.forEach(issue => {
          html += `<li style="margin-bottom: 4px;">${issue}</li>`;
        });
        html += '</ul></div>';
      }
      
      // 优化后代码
      if (optimizedScript) {
        html += '<div style="margin-bottom: 16px;"><div style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">优化后</div>';
        html += `<div class="code-block"><pre>${escapeHtml(optimizedScript)}</pre></div>`;
        html += '</div>';
      }
      
      // 优化说明
      if (data.explanation) {
        html += `<div style="padding: 12px; background: var(--n-100); border-radius: 6px; font-size: 13px; color: var(--n-600);">`;
        html += `<div style="font-weight: 600; margin-bottom: 4px;">优化说明</div>`;
        html += `<div>${data.explanation}</div>`;
        html += '</div>';
      }
      
      resultContent.innerHTML = html;
    } else {
      alert(`分析失败: ${result.msg}`);
    }
  });

  copyBtn.addEventListener('click', () => {
    if (optimizedScript) {
      navigator.clipboard.writeText(optimizedScript);
      copyBtn.textContent = '已复制';
      setTimeout(() => { copyBtn.textContent = '复制优化后'; }, 2000);
    }
  });
};

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
