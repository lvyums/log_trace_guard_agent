/**
 * 故障诊断页面
 */
window.Pages = window.Pages || {};
window.PageInit = window.PageInit || {};

window.Pages['fault'] = () => `
  <div class="main-header">
    <h1 class="main-title">故障诊断</h1>
    <p class="main-subtitle">多维度联合诊断日志采集故障</p>
  </div>

  <div class="card">
    <div class="form-group">
      <label class="form-label">故障症状</label>
      <textarea id="fault-symptom" class="input" placeholder="描述故障现象...&#10;&#10;示例: SSH连接超时，无法登录服务器" style="min-height: 80px;"></textarea>
    </div>
    <div class="form-group">
      <label class="form-label">设备类型（可选）</label>
      <select id="fault-type" class="input">
        <option value="">自动识别</option>
        <option value="server">服务器</option>
        <option value="firewall">防火墙</option>
        <option value="router">路由器</option>
        <option value="db">数据库</option>
      </select>
    </div>
    <div class="form-group">
      <label class="form-label">错误日志（可选）</label>
      <textarea id="fault-log" class="input" placeholder="粘贴错误日志片段..." style="min-height: 60px; font-family: var(--font-code); font-size: 11px;"></textarea>
    </div>
    <button id="fault-btn" class="btn btn-primary">诊断故障</button>
  </div>

  <div id="fault-result" class="result-area" style="display: none;">
    <div class="result-area-header">
      <span class="result-area-title">诊断结果</span>
    </div>
    <div id="fault-result-content"></div>
  </div>
`;

window.PageInit['fault'] = () => {
  const symptomInput = document.getElementById('fault-symptom');
  const typeSelect = document.getElementById('fault-type');
  const logInput = document.getElementById('fault-log');
  const btn = document.getElementById('fault-btn');
  const resultArea = document.getElementById('fault-result');
  const resultContent = document.getElementById('fault-result-content');

  btn.addEventListener('click', async () => {
    const symptom = symptomInput.value.trim();
    const deviceType = typeSelect.value || null;
    const errorLog = logInput.value.trim() || null;

    if (!symptom) {
      alert('请输入故障症状');
      return;
    }

    btn.disabled = true;
    btn.textContent = '诊断中...';
    resultArea.style.display = 'none';

    const result = await api.logCollect.diagnose(symptom, deviceType, null, errorLog);

    btn.disabled = false;
    btn.textContent = '诊断故障';

    if (result.code === 0) {
      resultArea.style.display = 'block';
      const data = result.data;
      
      let html = '<div class="result-card">';
      html += `<div class="result-row"><span class="result-label">故障类型</span><span class="result-value"><span class="badge badge-info">${data.fault_type}</span></span></div>`;
      html += `<div class="result-row"><span class="result-label">严重程度</span><span class="result-value">${data.severity || '未知'}</span></div>`;
      html += `<div class="result-row"><span class="result-label">匹配度</span><span class="result-value">${data.match_score || 0}%</span></div>`;
      
      if (data.possible_causes && data.possible_causes.length > 0) {
        html += '<div style="margin-top: 16px;"><div style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">可能原因</div>';
        html += '<ol style="margin: 0; padding-left: 16px; font-size: 13px;">';
        data.possible_causes.forEach(cause => {
          html += `<li style="margin-bottom: 4px;">${cause}</li>`;
        });
        html += '</ol></div>';
      }
      
      if (data.fix_steps && data.fix_steps.length > 0) {
        html += '<div style="margin-top: 16px;"><div style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">修复步骤</div>';
        html += '<ol style="margin: 0; padding-left: 16px; font-size: 13px;">';
        data.fix_steps.forEach(step => {
          html += `<li style="margin-bottom: 4px;">${step}</li>`;
        });
        html += '</ol></div>';
      }
      
      if (data.prevention && data.prevention.length > 0) {
        html += '<div style="margin-top: 16px;"><div style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">预防措施</div>';
        html += '<ul style="margin: 0; padding-left: 16px; font-size: 13px; color: var(--n-600);">';
        data.prevention.forEach(item => {
          html += `<li style="margin-bottom: 4px;">${item}</li>`;
        });
        html += '</ul></div>';
      }
      
      html += '</div>';
      resultContent.innerHTML = html;
    } else {
      alert(`诊断失败: ${result.msg}`);
    }
  });
};
