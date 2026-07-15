/**
 * 实训提交页面
 */
window.Pages = window.Pages || {};
window.PageInit = window.PageInit || {};

window.Pages['submit'] = () => `
  <div class="main-header">
    <h1 class="main-title">提交答案</h1>
    <p class="main-subtitle">提交实训答案，获取智能校验反馈</p>
  </div>

  <div class="card">
    <div class="form-group">
      <label class="form-label">场景 ID</label>
      <input id="sub-scenario" class="input" placeholder="如: S001">
    </div>
    <div class="form-group">
      <label class="form-label">任务 ID</label>
      <input id="sub-task" class="input" placeholder="如: T001">
    </div>
    <div class="form-group">
      <label class="form-label">提交类型</label>
      <select id="sub-type" class="input">
        <option value="conclusion">结论</option>
        <option value="rule">规则</option>
        <option value="script">脚本</option>
        <option value="plan">方案</option>
      </select>
    </div>
    <div class="form-group">
      <label class="form-label">学员 ID（可选）</label>
      <input id="sub-student" class="input" placeholder="用于记录成绩">
    </div>
    <div class="form-group">
      <label class="form-label">提交内容（JSON 格式）</label>
      <textarea id="sub-content" class="input" placeholder='{"answer": "你的答案"}' style="min-height: 120px; font-family: var(--font-code); font-size: 11px;"></textarea>
    </div>
    <button id="sub-btn" class="btn btn-primary">提交答案</button>
  </div>

  <div id="sub-result" class="result-area" style="display: none;">
    <div class="result-area-header">
      <span class="result-area-title">校验结果</span>
    </div>
    <div id="sub-result-content"></div>
  </div>
`;

window.PageInit['submit'] = () => {
  const btn = document.getElementById('sub-btn');
  const resultArea = document.getElementById('sub-result');
  const resultContent = document.getElementById('sub-result-content');

  btn.addEventListener('click', async () => {
    const scenarioId = document.getElementById('sub-scenario').value.trim();
    const taskId = document.getElementById('sub-task').value.trim();
    const submitType = document.getElementById('sub-type').value;
    const studentId = document.getElementById('sub-student').value.trim();
    const contentStr = document.getElementById('sub-content').value.trim();

    if (!scenarioId || !taskId) {
      alert('请输入场景 ID 和任务 ID');
      return;
    }

    let content;
    try {
      content = contentStr ? JSON.parse(contentStr) : {};
    } catch (e) {
      alert('提交内容格式错误，请输入有效的 JSON');
      return;
    }

    btn.disabled = true;
    btn.textContent = '提交中...';
    resultArea.style.display = 'none';

    const result = await api.training.submit(scenarioId, taskId, submitType, content, studentId);

    btn.disabled = false;
    btn.textContent = '提交答案';

    if (result.code === 0) {
      resultArea.style.display = 'block';
      const data = result.data;
      
      // 评分卡片
      const scoreColor = data.score >= 90 ? 'var(--success)' : 
                         data.score >= 70 ? 'var(--warning)' : 'var(--error)';
      let html = `<div class="result-card" style="text-align: center; margin-bottom: 16px;">`;
      html += `<div style="font-size: 48px; font-weight: 700; color: ${scoreColor};">${data.score}</div>`;
      html += `<div style="font-size: 13px; color: var(--n-500);">得分 | 等级: ${data.grade}</div>`;
      html += `<div style="margin-top: 8px;"><span class="badge badge-${data.status === 'passed' ? 'low' : data.status === 'optimize' ? 'medium' : 'high'}">${data.status === 'passed' ? '通过' : data.status === 'optimize' ? '可优化' : '需重做'}</span></div>`;
      html += '</div>';
      
      // 检查项
      if (data.checks && data.checks.length > 0) {
        html += '<div style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">检查项</div>';
        data.checks.forEach(check => {
          const statusIcon = check.status === 'correct' ? '✓' : check.status === 'partial' ? '~' : '✗';
          const statusColor = check.status === 'correct' ? 'var(--success)' : 
                             check.status === 'partial' ? 'var(--warning)' : 'var(--error)';
          html += `<div style="display: flex; align-items: flex-start; gap: 8px; padding: 8px; background: var(--n-100); border-radius: 4px; margin-bottom: 4px; font-size: 12px;">`;
          html += `<span style="color: ${statusColor}; font-weight: 600;">${statusIcon}</span>`;
          html += `<div><span style="font-weight: 500;">${check.field}</span>`;
          if (check.detail) html += `<div style="color: var(--n-600);">${check.detail}</div>`;
          html += '</div></div>';
        });
      }
      
      // 分析
      if (data.analysis) {
        html += `<div class="result-card" style="margin-top: 16px;">
          <div style="font-weight: 600; margin-bottom: 8px;">分析与讲解</div>
          <div style="font-size: 13px; color: var(--n-600); white-space: pre-wrap;">${data.analysis}</div>
        </div>`;
      }
      
      // 优化建议
      if (data.suggestion) {
        html += `<div style="margin-top: 12px; padding: 12px; background: rgba(51, 154, 240, 0.1); border-radius: 6px; font-size: 12px;">
          <span style="font-weight: 500;">优化建议:</span> ${data.suggestion}
        </div>`;
      }
      
      // 标准答案（仅 C 等级）
      if (data.correct_answer) {
        html += `<div class="result-card" style="margin-top: 16px;">
          <div style="font-weight: 600; margin-bottom: 8px;">标准答案参考</div>
          <div class="code-block"><pre>${JSON.stringify(data.correct_answer, null, 2)}</pre></div>
        </div>`;
      }
      
      resultContent.innerHTML = html;
    } else {
      alert(`提交失败: ${result.msg}`);
    }
  });
};
