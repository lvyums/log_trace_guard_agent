/**
 * 采集方案页面
 */
window.Pages = window.Pages || {};
window.PageInit = window.PageInit || {};

window.Pages['plan'] = () => `
  <div class="main-header">
    <h1 class="main-title">采集方案</h1>
    <p class="main-subtitle">生成设备日志采集方案</p>
  </div>

  <div class="card">
    <div class="form-group">
      <label class="form-label">设备类型</label>
      <select id="plan-type" class="input">
        <option value="firewall">防火墙</option>
        <option value="waf">WAF</option>
        <option value="ids">IDS</option>
        <option value="router">路由器</option>
        <option value="server">服务器</option>
        <option value="web">Web应用</option>
        <option value="db">数据库</option>
      </select>
    </div>
    <div class="form-group">
      <label class="form-label">设备型号（可选）</label>
      <input id="plan-model" class="input" placeholder="如: 华为USG6000V">
    </div>
    <div class="form-group">
      <label class="form-label">企业规模</label>
      <select id="plan-scale" class="input">
        <option value="small">小型</option>
        <option value="medium">中型</option>
        <option value="large">大型</option>
      </select>
    </div>
    <div class="checkbox">
      <input type="checkbox" id="plan-config" checked>
      <label for="plan-config">包含配置模板</label>
    </div>
    <div style="margin-top: 16px;">
      <button id="plan-btn" class="btn btn-primary">生成方案</button>
    </div>
  </div>

  <div id="plan-result" class="result-area" style="display: none;">
    <div class="result-area-header">
      <span class="result-area-title">采集方案</span>
    </div>
    <div id="plan-result-content"></div>
  </div>
`;

window.PageInit['plan'] = () => {
  const typeSelect = document.getElementById('plan-type');
  const modelInput = document.getElementById('plan-model');
  const scaleSelect = document.getElementById('plan-scale');
  const configCheckbox = document.getElementById('plan-config');
  const btn = document.getElementById('plan-btn');
  const resultArea = document.getElementById('plan-result');
  const resultContent = document.getElementById('plan-result-content');

  btn.addEventListener('click', async () => {
    const deviceType = typeSelect.value;
    const deviceModel = modelInput.value.trim();
    const scale = scaleSelect.value;
    const includeConfig = configCheckbox.checked;

    btn.disabled = true;
    btn.textContent = '生成中...';
    resultArea.style.display = 'none';

    const result = await api.logCollect.plan(deviceType, deviceModel, scale, includeConfig);

    btn.disabled = false;
    btn.textContent = '生成方案';

    if (result.code === 0) {
      resultArea.style.display = 'block';
      const data = result.data;
      
      let html = '<div class="result-card">';
      html += `<div class="result-row"><span class="result-label">设备类型</span><span class="result-value">${data.device_type || '-'}</span></div>`;
      html += `<div class="result-row"><span class="result-label">采集协议</span><span class="result-value"><span class="badge badge-info">${data.protocol || '-'}</span></span></div>`;
      html += `<div class="result-row"><span class="result-label">架构</span><span class="result-value">${data.architecture || '-'}</span></div>`;
      
      if (data.steps && data.steps.length > 0) {
        html += '<div style="margin-top: 16px;"><div style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">实施步骤</div>';
        html += '<ol style="margin: 0; padding-left: 16px; font-size: 13px;">';
        data.steps.forEach(step => {
          html += `<li style="margin-bottom: 8px;">${step}</li>`;
        });
        html += '</ol></div>';
      }
      
      if (data.notes && data.notes.length > 0) {
        html += '<div style="margin-top: 16px;"><div style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">注意事项</div>';
        html += '<ul style="margin: 0; padding-left: 16px; font-size: 13px; color: var(--n-600);">';
        data.notes.forEach(note => {
          html += `<li style="margin-bottom: 4px;">${note}</li>`;
        });
        html += '</ul></div>';
      }
      
      if (data.config_template) {
        html += '<div style="margin-top: 16px;"><div style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">配置模板</div>';
        html += `<div class="code-block">${JSON.stringify(data.config_template, null, 2)}</div>`;
        html += '</div>';
      }
      
      html += '</div>';
      resultContent.innerHTML = html;
    } else {
      alert(`生成失败: ${result.msg}`);
    }
  });
};
