/**
 * 结构化解析页面
 */
window.Pages = window.Pages || {};
window.PageInit = window.PageInit || {};

window.Pages['parse'] = () => `
  <div class="main-header">
    <h1 class="main-title">结构化解析</h1>
    <p class="main-subtitle">将原始日志解析为结构化字段</p>
  </div>

  <div class="card">
    <div class="log-input-area">
      <textarea id="parse-input" class="input" placeholder="粘贴日志内容...&#10;&#10;示例: Jul 15 11:30:01 server sshd[12345]: Failed password for root from 192.168.1.100 port 22 ssh2"></textarea>
    </div>
    <div class="log-input-actions">
      <button id="parse-btn" class="btn btn-primary">解析日志</button>
      <button id="parse-clear" class="btn btn-ghost">清空</button>
    </div>
  </div>

  <div id="parse-result" class="result-area" style="display: none;">
    <div class="result-area-header">
      <span class="result-area-title">解析结果</span>
    </div>
    <div id="parse-result-content"></div>
  </div>
`;

window.PageInit['parse'] = () => {
  const input = document.getElementById('parse-input');
  const btn = document.getElementById('parse-btn');
  const clearBtn = document.getElementById('parse-clear');
  const resultArea = document.getElementById('parse-result');
  const resultContent = document.getElementById('parse-result-content');

  btn.addEventListener('click', async () => {
    const logLine = input.value.trim();
    if (!logLine) {
      alert('请输入日志内容');
      return;
    }

    btn.disabled = true;
    btn.textContent = '解析中...';
    resultArea.style.display = 'none';

    const result = await api.logParse.parse(logLine);

    btn.disabled = false;
    btn.textContent = '解析日志';

    if (result.code === 0) {
      resultArea.style.display = 'block';
      const data = result.data;
      
      // 构建表格
      const fields = ['timestamp', 'src_ip', 'dst_ip', 'src_port', 'dst_port', 'user', 'url', 'method', 'command', 'status', 'device_type'];
      let tableHTML = '<table class="table"><thead><tr><th>字段</th><th>值</th></tr></thead><tbody>';
      
      fields.forEach(field => {
        const value = data[field];
        const isMissing = data.missing_fields && data.missing_fields.includes(field);
        tableHTML += `<tr>
          <td style="font-weight: 500; ${isMissing ? 'color: var(--n-400);' : ''}">${field}</td>
          <td style="${isMissing ? 'color: var(--n-400); font-style: italic;' : ''}">${value || '(未提取)'}</td>
        </tr>`;
      });
      
      tableHTML += '</tbody></table>';
      
      // 缺失字段提示
      if (data.missing_fields && data.missing_fields.length > 0) {
        tableHTML += `<div style="margin-top: 12px; font-size: 12px; color: var(--n-500);">
          缺失字段: ${data.missing_fields.join(', ')}
        </div>`;
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

  input.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'Enter') {
      btn.click();
    }
  });
};
