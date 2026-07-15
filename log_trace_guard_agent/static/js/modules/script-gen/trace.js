/**
 * 攻击溯源页面
 */
window.Pages = window.Pages || {};
window.PageInit = window.PageInit || {};

window.Pages['trace'] = () => `
  <div class="main-header">
    <h1 class="main-title">攻击溯源</h1>
    <p class="main-subtitle">追踪攻击链路，还原攻击过程</p>
  </div>

  <div class="card">
    <div class="form-group">
      <label class="form-label">攻击类型（可选）</label>
      <select id="trace-type" class="input">
        <option value="">自动识别</option>
        <option value="SSH暴力破解">SSH暴力破解</option>
        <option value="SQL注入">SQL注入</option>
        <option value="Web扫描">Web扫描</option>
        <option value="提权攻击">提权攻击</option>
      </select>
    </div>
    <div class="form-group">
      <label class="form-label">日志列表（每行一条）</label>
      <textarea id="trace-logs" class="input" placeholder="粘贴多条日志...&#10;&#10;示例:&#10;Jul 15 11:30:01 server sshd[12345]: Failed password for root from 192.168.1.100 port 22 ssh2&#10;Jul 15 11:30:05 server sshd[12346]: Failed password for admin from 192.168.1.100 port 22 ssh2&#10;Jul 15 11:31:00 server sshd[12347]: Accepted password for root from 192.168.1.100 port 22 ssh2" style="min-height: 160px; font-family: var(--font-code); font-size: 11px;"></textarea>
    </div>
    <button id="trace-btn" class="btn btn-primary">溯源分析</button>
  </div>

  <div id="trace-result" class="result-area" style="display: none;">
    <div class="result-area-header">
      <span class="result-area-title">攻击链路</span>
    </div>
    <div id="trace-result-content"></div>
  </div>
`;

window.PageInit['trace'] = () => {
  const typeSelect = document.getElementById('trace-type');
  const logsInput = document.getElementById('trace-logs');
  const btn = document.getElementById('trace-btn');
  const resultArea = document.getElementById('trace-result');
  const resultContent = document.getElementById('trace-result-content');

  btn.addEventListener('click', async () => {
    const text = logsInput.value.trim();
    const attackType = typeSelect.value;

    if (!text) {
      alert('请输入日志');
      return;
    }

    const logs = text.split('\n').filter(line => line.trim());

    btn.disabled = true;
    btn.textContent = '分析中...';
    resultArea.style.display = 'none';

    const result = await api.scriptGen.trace(logs, attackType);

    btn.disabled = false;
    btn.textContent = '溯源分析';

    if (result.code === 0) {
      resultArea.style.display = 'block';
      const data = result.data;
      
      let html = '';
      
      // 攻击链路时间线
      if (data.attack_chain && data.attack_chain.length > 0) {
        html += '<div class="timeline">';
        data.attack_chain.forEach(event => {
          const riskClass = (event.risk_level || '').includes('高危') ? 'critical' : 
                            (event.risk_level || '').includes('中危') ? 'high' : '';
          html += `<div class="timeline-item ${riskClass}">`;
          html += `<div class="timeline-time">${event.timestamp || '-'}</div>`;
          html += '<div class="timeline-content">';
          html += `<div class="timeline-event">${event.event_type || event.action || '-'}</div>`;
          if (event.source || event.target) {
            html += `<div class="timeline-detail">${event.source || ''} → ${event.target || ''}</div>`;
          }
          if (event.detail) {
            html += `<div class="timeline-detail">${event.detail}</div>`;
          }
          html += '</div></div>';
        });
        html += '</div>';
      }
      
      // 其他信息
      html += '<div class="result-card" style="margin-top: 16px;">';
      if (data.entry_point) {
        html += `<div class="result-row"><span class="result-label">入口点</span><span class="result-value">${data.entry_point}</span></div>`;
      }
      if (data.affected_assets && data.affected_assets.length > 0) {
        html += `<div class="result-row"><span class="result-label">受影响资产</span><span class="result-value">${data.affected_assets.join(', ')}</span></div>`;
      }
      if (data.attack_stage) {
        html += `<div class="result-row"><span class="result-label">攻击阶段</span><span class="result-value">${data.attack_stage}</span></div>`;
      }
      if (data.summary) {
        html += `<div class="result-row"><span class="result-label">总结</span><span class="result-value">${data.summary}</span></div>`;
      }
      html += '</div>';
      
      resultContent.innerHTML = html;
    } else {
      alert(`分析失败: ${result.msg}`);
    }
  });
};
