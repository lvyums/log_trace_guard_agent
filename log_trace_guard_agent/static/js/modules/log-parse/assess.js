/**
 * 风险研判页面
 */
window.Pages = window.Pages || {};
window.PageInit = window.PageInit || {};

window.Pages['assess'] = () => `
  <div class="main-header">
    <h1 class="main-title">风险研判</h1>
    <p class="main-subtitle">分析日志中的安全风险</p>
  </div>

  <div class="card">
    <div class="log-input-area">
      <textarea id="assess-input" class="input" placeholder="粘贴日志内容...&#10;&#10;示例: Jul 15 11:30:01 server sshd[12345]: Failed password for root from 192.168.1.100 port 22 ssh2"></textarea>
    </div>
    <div class="log-input-actions">
      <button id="assess-btn" class="btn btn-primary">分析风险</button>
      <button id="assess-clear" class="btn btn-ghost">清空</button>
    </div>
  </div>

  <div id="assess-result" class="result-area" style="display: none;">
    <div class="result-area-header">
      <span class="result-area-title">风险研判结果</span>
    </div>
    <div id="assess-result-content"></div>
  </div>
`;

window.PageInit['assess'] = () => {
  const input = document.getElementById('assess-input');
  const btn = document.getElementById('assess-btn');
  const clearBtn = document.getElementById('assess-clear');
  const resultArea = document.getElementById('assess-result');
  const resultContent = document.getElementById('assess-result-content');

  btn.addEventListener('click', async () => {
    const logLine = input.value.trim();
    if (!logLine) {
      alert('请输入日志内容');
      return;
    }

    btn.disabled = true;
    btn.textContent = '分析中...';
    resultArea.style.display = 'none';

    const result = await api.logParse.assess(logLine);

    btn.disabled = false;
    btn.textContent = '分析风险';

    if (result.code === 0) {
      resultArea.style.display = 'block';
      const data = result.data;
      
      // 解析风险等级
      const riskLevel = data.risk_level || 'P3_噪音';
      const riskClass = riskLevel.includes('高危') ? 'critical' : 
                        riskLevel.includes('中危') ? 'high' : 
                        riskLevel.includes('低危') ? 'medium' : 'noise';
      
      resultContent.innerHTML = `
        <div class="risk-card ${riskClass}">
          <div class="risk-header">
            <span class="risk-level">${riskLevel}</span>
            <span class="badge badge-${riskClass === 'critical' ? 'critical' : riskClass === 'high' ? 'high' : riskClass === 'medium' ? 'medium' : 'low'}">${riskLevel}</span>
            <span class="risk-confidence">置信度: ${data.confidence}%</span>
          </div>
          <div class="risk-details">
            ${data.attack_type ? `
            <div class="risk-detail-row">
              <span class="risk-detail-label">攻击类型</span>
              <span class="risk-detail-value">${data.attack_type}</span>
            </div>` : ''}
            ${data.risk_desc ? `
            <div class="risk-detail-row">
              <span class="risk-detail-label">风险描述</span>
              <span class="risk-detail-value">${data.risk_desc}</span>
            </div>` : ''}
            ${data.match_rule_ids && data.match_rule_ids.length > 0 ? `
            <div class="risk-detail-row">
              <span class="risk-detail-label">命中规则</span>
              <span class="risk-detail-value">${data.match_rule_ids.join(', ')}</span>
            </div>` : ''}
            ${data.suggestion ? `
            <div class="risk-detail-row">
              <span class="risk-detail-label">处置建议</span>
              <span class="risk-detail-value">${data.suggestion}</span>
            </div>` : ''}
          </div>
        </div>
      `;
    } else {
      alert(`分析失败: ${result.msg}`);
    }
  });

  clearBtn.addEventListener('click', () => {
    input.value = '';
    resultArea.style.display = 'none';
  });

  input.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'Enter') {
      btn.click();
    }
  });
};
