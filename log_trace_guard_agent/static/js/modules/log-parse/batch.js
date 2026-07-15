/**
 * 批量解析页面
 */
window.Pages = window.Pages || {};
window.PageInit = window.PageInit || {};

window.Pages['batch'] = () => `
  <div class="main-header">
    <h1 class="main-title">批量解析</h1>
    <p class="main-subtitle">批量解析多条日志，可选风险研判</p>
  </div>

  <div class="card">
    <div class="log-input-area">
      <textarea id="batch-input" class="input" placeholder="粘贴多行日志（每行一条）...&#10;&#10;示例:&#10;Jul 15 11:30:01 server sshd[12345]: Failed password for root from 192.168.1.100 port 22 ssh2&#10;Jul 15 11:30:05 server nginx[12346]: 192.168.1.101 - GET /admin HTTP/1.1 404" style="min-height: 160px;"></textarea>
    </div>
    <div class="log-input-actions">
      <label class="checkbox">
        <input type="checkbox" id="batch-assess">
        <label for="batch-assess">同时进行风险研判</label>
      </label>
      <button id="batch-btn" class="btn btn-primary">批量解析</button>
      <button id="batch-clear" class="btn btn-ghost">清空</button>
    </div>
  </div>

  <div id="batch-result" class="result-area" style="display: none;">
    <div class="result-area-header">
      <span class="result-area-title">解析结果</span>
      <span id="batch-summary"></span>
    </div>
    <div id="batch-result-content"></div>
  </div>
`;

window.PageInit['batch'] = () => {
  const input = document.getElementById('batch-input');
  const btn = document.getElementById('batch-btn');
  const clearBtn = document.getElementById('batch-clear');
  const assessCheckbox = document.getElementById('batch-assess');
  const resultArea = document.getElementById('batch-result');
  const resultContent = document.getElementById('batch-result-content');
  const summary = document.getElementById('batch-summary');

  btn.addEventListener('click', async () => {
    const text = input.value.trim();
    if (!text) {
      alert('请输入日志内容');
      return;
    }

    const logs = text.split('\n').filter(line => line.trim());
    if (logs.length === 0) {
      alert('请输入至少一条日志');
      return;
    }

    btn.disabled = true;
    btn.textContent = '解析中...';
    resultArea.style.display = 'none';

    const result = await api.logParse.batchParse(logs, assessCheckbox.checked);

    btn.disabled = false;
    btn.textContent = '批量解析';

    if (result.code === 0) {
      resultArea.style.display = 'block';
      const data = result.data;
      
      summary.innerHTML = `<span style="font-size: 12px; color: var(--n-500);">
        共 ${data.total} 条 | 成功 ${data.success_count} | 失败 ${data.fail_count}
      </span>`;
      
      let tableHTML = '<table class="table"><thead><tr><th>#</th><th>日志内容</th><th>设备类型</th><th>状态</th>';
      if (assessCheckbox.checked) {
        tableHTML += '<th>风险等级</th>';
      }
      tableHTML += '</tr></thead><tbody>';
      
      data.items.forEach(item => {
        tableHTML += '<tr>';
        tableHTML += `<td>${item.index + 1}</td>`;
        tableHTML += `<td style="font-family: var(--font-code); font-size: 11px; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${item.log_line}</td>`;
        
        if (item.parse_result) {
          tableHTML += `<td><span class="badge badge-info">${item.parse_result.device_type || 'unknown'}</span></td>`;
          tableHTML += `<td style="color: var(--success);">成功</td>`;
        } else if (item.error) {
          tableHTML += `<td>-</td>`;
          tableHTML += `<td style="color: var(--error);">${item.error}</td>`;
        } else {
          tableHTML += `<td>-</td>`;
          tableHTML += `<td>-</td>`;
        }
        
        if (assessCheckbox.checked && item.risk_result) {
          const riskLevel = item.risk_result.risk_level || 'P3_噪音';
          const riskClass = riskLevel.includes('高危') ? 'critical' : 
                            riskLevel.includes('中危') ? 'high' : 
                            riskLevel.includes('低危') ? 'medium' : 'noise';
          tableHTML += `<td><span class="badge badge-${riskClass}">${riskLevel}</span></td>`;
        } else if (assessCheckbox.checked) {
          tableHTML += '<td>-</td>';
        }
        
        tableHTML += '</tr>';
      });
      
      tableHTML += '</tbody></table>';
      
      // 风险汇总
      if (data.risk_summary) {
        tableHTML += '<div style="margin-top: 16px; padding: 12px; background: var(--n-100); border-radius: 6px;">';
        tableHTML += '<div style="font-size: 12px; font-weight: 600; margin-bottom: 8px;">风险分布</div>';
        tableHTML += '<div style="display: flex; gap: 16px; font-size: 12px;">';
        Object.entries(data.risk_summary).forEach(([level, count]) => {
          if (count > 0) {
            const riskClass = level.includes('高危') ? 'critical' : 
                              level.includes('中危') ? 'high' : 
                              level.includes('低危') ? 'medium' : 'noise';
            tableHTML += `<span class="badge badge-${riskClass}">${level}: ${count}</span>`;
          }
        });
        tableHTML += '</div></div>';
      }
      
      resultContent.innerHTML = `<div class="result-card">${tableHTML}</div>`;
    } else {
      alert(`解析失败: ${result.msg}`);
    }
  });

  clearBtn.addEventListener('click', () => {
    input.value = '';
    resultArea.style.display = 'none';
  });
};
