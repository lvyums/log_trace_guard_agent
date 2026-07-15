/**
 * 合规自查页面
 */
window.Pages = window.Pages || {};
window.PageInit = window.PageInit || {};

window.Pages['check'] = () => `
  <div class="main-header">
    <h1 class="main-title">合规自查</h1>
    <p class="main-subtitle">检查当前合规状态，识别差距并获取整改建议</p>
  </div>

  <div class="card">
    <div class="form-group">
      <label class="form-label">日志留存天数</label>
      <input id="ck-retention" class="input" type="number" value="180" min="1" placeholder="当前日志保存天数">
    </div>
    <div class="form-group">
      <label class="form-label">设备数量</label>
      <input id="ck-devices" class="input" type="number" value="50" min="1">
    </div>
    <div class="form-group">
      <label class="form-label">安全措施</label>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
        <label class="checkbox"><input type="checkbox" id="ck-backup"> 日志备份</label>
        <label class="checkbox"><input type="checkbox" id="ck-tamper"> 防篡改机制</label>
        <label class="checkbox"><input type="checkbox" id="ck-audit"> 审计机制</label>
        <label class="checkbox"><input type="checkbox" id="ck-ntp"> NTP时钟同步</label>
        <label class="checkbox"><input type="checkbox" id="ck-alert"> 实时告警系统</label>
        <label class="checkbox"><input type="checkbox" id="ck-bastion"> 堡垒机</label>
      </div>
    </div>
    <div class="form-group">
      <label class="form-label">备份频率（如有备份）</label>
      <select id="ck-backup-freq" class="input">
        <option value="">不适用</option>
        <option value="daily">每日</option>
        <option value="weekly">每周</option>
        <option value="monthly">每月</option>
      </select>
    </div>
    <div class="form-group">
      <label class="form-label">补充信息（可选）</label>
      <textarea id="ck-extra" class="input" placeholder="其他需要说明的情况..." style="min-height: 60px;"></textarea>
    </div>
    <button id="ck-btn" class="btn btn-primary">开始自查</button>
  </div>

  <div id="ck-result" class="result-area" style="display: none;">
    <div class="result-area-header">
      <span class="result-area-title">自查结果</span>
    </div>
    <div id="ck-result-content"></div>
  </div>
`;

window.PageInit['check'] = () => {
  const btn = document.getElementById('ck-btn');
  const resultArea = document.getElementById('ck-result');
  const resultContent = document.getElementById('ck-result-content');

  btn.addEventListener('click', async () => {
    const params = {
      log_retention_days: parseInt(document.getElementById('ck-retention').value) || null,
      has_backup: document.getElementById('ck-backup').checked,
      has_tamper_proof: document.getElementById('ck-tamper').checked,
      has_audit_mechanism: document.getElementById('ck-audit').checked,
      has_ntp: document.getElementById('ck-ntp').checked,
      has_alert_system: document.getElementById('ck-alert').checked,
      has_bastion: document.getElementById('ck-bastion').checked,
      backup_frequency: document.getElementById('ck-backup-freq').value || null,
      device_count: parseInt(document.getElementById('ck-devices').value) || null,
      additional_info: document.getElementById('ck-extra').value.trim() || null,
    };

    btn.disabled = true;
    btn.textContent = '检查中...';
    resultArea.style.display = 'none';

    const result = await api.compliance.check(params);

    btn.disabled = false;
    btn.textContent = '开始自查';

    if (result.code === 0) {
      resultArea.style.display = 'block';
      const data = result.data;
      
      let html = '';
      
      // 评分卡片
      const scoreColor = data.overall_score >= 80 ? 'var(--success)' : 
                         data.overall_score >= 60 ? 'var(--warning)' : 'var(--error)';
      html += `<div class="result-card" style="text-align: center; margin-bottom: 16px;">`;
      html += `<div style="font-size: 48px; font-weight: 700; color: ${scoreColor};">${data.overall_score}</div>`;
      html += `<div style="font-size: 13px; color: var(--n-500);">合规评分</div>`;
      html += '<div style="display: flex; justify-content: center; gap: 16px; margin-top: 12px;">';
      if (data.critical_count > 0) html += `<span class="badge badge-critical">高风险: ${data.critical_count}</span>`;
      if (data.medium_count > 0) html += `<span class="badge badge-high">中风险: ${data.medium_count}</span>`;
      if (data.low_count > 0) html += `<span class="badge badge-medium">低风险: ${data.low_count}</span>`;
      html += '</div></div>';
      
      // 缺口列表
      if (data.gaps && data.gaps.length > 0) {
        html += '<div style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">合规缺口</div>';
        data.gaps.forEach(gap => {
          const severityClass = gap.risk_level === 'high' ? 'critical' : 
                               gap.risk_level === 'medium' ? 'high' : 'low';
          html += `<div class="result-card" style="margin-bottom: 8px; border-left: 4px solid var(--risk-${severityClass});">`;
          html += `<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">`;
          html += `<span style="font-weight: 500;">${gap.requirement}</span>`;
          html += `<span class="badge badge-${severityClass}">${gap.risk_level}</span>`;
          html += `<span style="font-size: 11px; color: var(--n-500);">优先级: ${gap.priority}</span>`;
          html += '</div>';
          if (gap.risk_description) {
            html += `<div style="font-size: 12px; color: var(--n-600); margin-bottom: 4px;">${gap.risk_description}</div>`;
          }
          if (gap.remediation_steps && gap.remediation_steps.length > 0) {
            html += '<div style="font-size: 11px; margin-top: 4px;"><span style="font-weight: 500;">整改步骤:</span>';
            html += '<ol style="margin: 4px 0 0 16px; padding: 0;">';
            gap.remediation_steps.forEach(step => {
              html += `<li style="margin-bottom: 2px;">${step}</li>`;
            });
            html += '</ol></div>';
          }
          html += '</div>';
        });
      }
      
      // 总结
      if (data.summary) {
        html += `<div class="result-card" style="margin-top: 16px;">
          <div style="font-weight: 600; margin-bottom: 8px;">自查总结</div>
          <div style="font-size: 13px; color: var(--n-600);">${data.summary}</div>
        </div>`;
      }
      
      resultContent.innerHTML = html;
    } else {
      alert(`自查失败: ${result.msg}`);
    }
  });
};
