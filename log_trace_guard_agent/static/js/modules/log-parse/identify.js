/**
 * 日志识别页面
 */
window.Pages = window.Pages || {};
window.PageInit = window.PageInit || {};

window.Pages['identify'] = () => `
  <div class="main-header">
    <h1 class="main-title">日志识别</h1>
    <p class="main-subtitle">自动识别日志的设备类型和来源</p>
  </div>

  <div class="card">
    <div class="log-input-area">
      <textarea id="identify-input" class="input" placeholder="粘贴日志内容...&#10;&#10;示例: Jul 15 11:30:01 server sshd[12345]: Failed password for root from 192.168.1.100 port 22 ssh2"></textarea>
    </div>
    <div class="log-input-actions">
      <button id="identify-btn" class="btn btn-primary">识别日志类型</button>
      <button id="identify-clear" class="btn btn-ghost">清空</button>
    </div>
  </div>

  <div id="identify-result" class="result-area" style="display: none;">
    <div class="result-area-header">
      <span class="result-area-title">识别结果</span>
    </div>
    <div id="identify-result-content"></div>
  </div>
`;

window.PageInit['identify'] = () => {
  const input = document.getElementById('identify-input');
  const btn = document.getElementById('identify-btn');
  const clearBtn = document.getElementById('identify-clear');
  const resultArea = document.getElementById('identify-result');
  const resultContent = document.getElementById('identify-result-content');

  btn.addEventListener('click', async () => {
    const logLine = input.value.trim();
    if (!logLine) {
      alert('请输入日志内容');
      return;
    }

    btn.disabled = true;
    btn.textContent = '识别中...';
    resultArea.style.display = 'none';

    const result = await api.logParse.identify(logLine);

    btn.disabled = false;
    btn.textContent = '识别日志类型';

    if (result.code === 0) {
      resultArea.style.display = 'block';
      const data = result.data;
      resultContent.innerHTML = `
        <div class="result-card">
          <div class="result-row">
            <span class="result-label">设备类型</span>
            <span class="result-value"><span class="badge badge-info">${data.device_type}</span></span>
          </div>
          <div class="result-row">
            <span class="result-label">置信度</span>
            <span class="result-value">
              <div class="progress" style="width: 200px; display: inline-block; vertical-align: middle;">
                <div class="progress-bar" style="width: ${data.confidence}%"></div>
              </div>
              <span style="margin-left: 8px;">${data.confidence}%</span>
            </span>
          </div>
          <div class="result-row">
            <span class="result-label">识别依据</span>
            <span class="result-value">${data.identify_reason}</span>
          </div>
        </div>
      `;
    } else {
      alert(`识别失败: ${result.msg}`);
    }
  });

  clearBtn.addEventListener('click', () => {
    input.value = '';
    resultArea.style.display = 'none';
  });

  // Ctrl+Enter 提交
  input.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'Enter') {
      btn.click();
    }
  });
};
