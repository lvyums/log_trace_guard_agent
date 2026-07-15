/**
 * 合规基线生成页面
 */
window.Pages = window.Pages || {};
window.PageInit = window.PageInit || {};

window.Pages['baseline'] = () => `
  <div class="main-header">
    <h1 class="main-title">合规基线生成</h1>
    <p class="main-subtitle">根据业务场景自动生成合规监控基线</p>
  </div>

  <div class="card">
    <div class="form-group">
      <label class="form-label">资产数量</label>
      <input id="bl-count" class="input" type="number" value="50" min="1">
    </div>
    <div class="form-group">
      <label class="form-label">业务类型</label>
      <select id="bl-business" class="input">
        <option value="enterprise">企业</option>
        <option value="gov">政府</option>
        <option value="education">教育</option>
        <option value="finance">金融</option>
        <option value="medical">医疗</option>
      </select>
    </div>
    <div class="form-group">
      <label class="form-label">设备类型（多选）</label>
      <div style="display: flex; gap: 12px; flex-wrap: wrap;">
        <label class="checkbox"><input type="checkbox" value="server" checked> 服务器</label>
        <label class="checkbox"><input type="checkbox" value="firewall"> 防火墙</label>
        <label class="checkbox"><input type="checkbox" value="web"> Web应用</label>
        <label class="checkbox"><input type="checkbox" value="db"> 数据库</label>
        <label class="checkbox"><input type="checkbox" value="network"> 网络设备</label>
      </div>
    </div>
    <div class="form-group">
      <label class="form-label">行业（可选）</label>
      <input id="bl-industry" class="input" placeholder="如: 教育、政企、金融">
    </div>
    <button id="bl-btn" class="btn btn-primary">生成基线</button>
  </div>

  <div id="bl-result" class="result-area" style="display: none;">
    <div class="result-area-header">
      <span class="result-area-title">监控基线</span>
    </div>
    <div id="bl-result-content"></div>
  </div>
`;

window.PageInit['baseline'] = () => {
  const countInput = document.getElementById('bl-count');
  const businessSelect = document.getElementById('bl-business');
  const industryInput = document.getElementById('bl-industry');
  const btn = document.getElementById('bl-btn');
  const resultArea = document.getElementById('bl-result');
  const resultContent = document.getElementById('bl-result-content');

  btn.addEventListener('click', async () => {
    const assetCount = parseInt(countInput.value) || 50;
    const businessType = businessSelect.value;
    const industry = industryInput.value.trim();
    
    // 获取选中的设备类型
    const deviceTypes = [];
    document.querySelectorAll('#bl-result').previousElementSibling.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => {
      deviceTypes.push(cb.value);
    });

    btn.disabled = true;
    btn.textContent = '生成中...';
    resultArea.style.display = 'none';

    const result = await api.compliance.baseline(assetCount, businessType, deviceTypes, [], industry);

    btn.disabled = false;
    btn.textContent = '生成基线';

    if (result.code === 0) {
      resultArea.style.display = 'block';
      const data = result.data;
      
      let html = '';
      
      if (data.baselines && data.baselines.length > 0) {
        data.baselines.forEach(bl => {
          const severityClass = bl.severity === 'high' ? 'critical' : 
                               bl.severity === 'medium' ? 'high' : 'low';
          html += `<div class="result-card" style="margin-bottom: 12px; border-left: 4px solid var(--risk-${severityClass});">`;
          html += `<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">`;
          html += `<span style="font-weight: 600;">${bl.name}</span>`;
          html += `<span class="badge badge-${severityClass}">${bl.severity}</span>`;
          html += `<span style="font-size: 11px; color: var(--n-500);">${bl.category}</span>`;
          html += '</div>';
          
          if (bl.description) {
            html += `<div style="font-size: 12px; color: var(--n-600); margin-bottom: 8px;">${bl.description}</div>`;
          }
          
          if (bl.thresholds && bl.thresholds.length > 0) {
            html += '<div style="font-size: 11px; font-weight: 500; margin-bottom: 4px;">阈值配置:</div>';
            bl.thresholds.forEach(t => {
              html += `<div style="font-size: 11px; color: var(--n-600); padding-left: 12px;">• ${t.name}: ${t.description}</div>`;
            });
          }
          
          html += '<div style="display: flex; gap: 16px; margin-top: 8px; font-size: 11px; color: var(--n-500);">';
          if (bl.check_frequency) html += `<span>检查频率: ${bl.check_frequency}</span>`;
          if (bl.alert_standard) html += `<span>告警标准: ${bl.alert_standard}</span>`;
          html += '</div>';
          
          if (bl.remediation) {
            html += `<div style="margin-top: 8px; padding: 8px; background: var(--n-100); border-radius: 4px; font-size: 11px;">
              <span style="font-weight: 500;">整改建议:</span> ${bl.remediation}
            </div>`;
          }
          
          html += '</div>';
        });
      }
      
      if (data.summary) {
        html += `<div class="result-card" style="margin-top: 16px;">
          <div style="font-weight: 600; margin-bottom: 8px;">总结</div>
          <div style="font-size: 13px; color: var(--n-600);">${data.summary}</div>
        </div>`;
      }
      
      resultContent.innerHTML = html;
    } else {
      alert(`生成失败: ${result.msg}`);
    }
  });
};
