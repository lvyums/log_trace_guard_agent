/**
 * 设备匹配页面
 */
window.Pages = window.Pages || {};
window.PageInit = window.PageInit || {};

window.Pages['match'] = () => `
  <div class="main-header">
    <h1 class="main-title">设备匹配</h1>
    <p class="main-subtitle">自动识别设备类型并推荐采集方案</p>
  </div>

  <div class="card">
    <div class="form-group">
      <label class="form-label">设备类型</label>
      <select id="match-type" class="input">
        <option value="firewall">防火墙</option>
        <option value="waf">WAF</option>
        <option value="ids">IDS</option>
        <option value="router">路由器</option>
        <option value="switch">交换机</option>
        <option value="server">服务器</option>
        <option value="web">Web应用</option>
        <option value="db">数据库</option>
        <option value="bastion">堡垒机</option>
      </select>
    </div>
    <div class="form-group">
      <label class="form-label">设备型号（可选）</label>
      <input id="match-model" class="input" placeholder="如: 华为USG6000V, Cisco ASA 5500">
    </div>
    <div class="form-group">
      <label class="form-label">企业规模</label>
      <select id="match-scale" class="input">
        <option value="small">小型（10台以下）</option>
        <option value="medium">中型（10-100台）</option>
        <option value="large">大型（100台以上）</option>
      </select>
    </div>
    <button id="match-btn" class="btn btn-primary">匹配设备</button>
  </div>

  <div id="match-result" class="result-area" style="display: none;">
    <div class="result-area-header">
      <span class="result-area-title">匹配结果</span>
    </div>
    <div id="match-result-content"></div>
  </div>
`;

window.PageInit['match'] = () => {
  const typeSelect = document.getElementById('match-type');
  const modelInput = document.getElementById('match-model');
  const scaleSelect = document.getElementById('match-scale');
  const btn = document.getElementById('match-btn');
  const resultArea = document.getElementById('match-result');
  const resultContent = document.getElementById('match-result-content');

  btn.addEventListener('click', async () => {
    const deviceType = typeSelect.value;
    const deviceModel = modelInput.value.trim();
    const scale = scaleSelect.value;

    btn.disabled = true;
    btn.textContent = '匹配中...';
    resultArea.style.display = 'none';

    const result = await api.logCollect.match(deviceType, deviceModel, scale);

    btn.disabled = false;
    btn.textContent = '匹配设备';

    if (result.code === 0) {
      resultArea.style.display = 'block';
      const data = result.data;
      
      let html = '<div class="device-card">';
      html += `<div class="device-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="24" height="24">
          <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
          <line x1="8" y1="21" x2="16" y2="21"/>
          <line x1="12" y1="17" x2="12" y2="21"/>
        </svg>
      </div>`;
      html += '<div class="device-info">';
      html += `<div class="device-name">${data.device_info?.device_type || deviceType}</div>`;
      html += `<div class="device-meta">匹配置信度: ${data.match_confidence || 0}% | 匹配来源: ${data.match_source || '-'}</div>`;
      html += '</div></div>';
      
      if (data.plan) {
        html += '<div class="result-card" style="margin-top: 16px;">';
        html += '<div class="result-row"><span class="result-label">采集协议</span><span class="result-value">' + (data.plan.protocol || '-') + '</span></div>';
        html += '<div class="result-row"><span class="result-label">架构</span><span class="result-value">' + (data.plan.architecture || '-') + '</span></div>';
        if (data.plan.steps && data.plan.steps.length > 0) {
          html += '<div class="result-row"><span class="result-label">步骤</span><span class="result-value"><ol style="margin: 0; padding-left: 16px;">';
          data.plan.steps.forEach(step => {
            html += `<li style="margin-bottom: 4px;">${step}</li>`;
          });
          html += '</ol></span></div>';
        }
        html += '</div>';
      }
      
      if (data.low_confidence_note) {
        html += `<div style="margin-top: 12px; padding: 8px; background: rgba(252, 196, 25, 0.1); border-radius: 4px; font-size: 12px; color: var(--risk-medium);">
          ${data.low_confidence_note}
        </div>`;
      }
      
      resultContent.innerHTML = html;
    } else {
      alert(`匹配失败: ${result.msg}`);
    }
  });
};
