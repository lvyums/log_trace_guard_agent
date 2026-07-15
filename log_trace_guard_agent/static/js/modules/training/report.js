/**
 * 实训报告页面
 */
window.Pages = window.Pages || {};
window.PageInit = window.PageInit || {};

window.Pages['report'] = () => `
  <div class="main-header">
    <h1 class="main-title">实训报告</h1>
    <p class="main-subtitle">查看实训成绩、薄弱项分析和能力提升方案</p>
  </div>

  <div class="card">
    <div class="form-group">
      <label class="form-label">学员 ID（可选）</label>
      <input id="rpt-student" class="input" placeholder="留空查看所有学员">
    </div>
    <div class="form-group">
      <label class="form-label">场景 ID（可选）</label>
      <select id="rpt-scenario" class="input">
        <option value="">全部场景</option>
        <option value="S001">S001 - 日志基础认知</option>
        <option value="S002">S002 - 日志采集配置</option>
        <option value="S003">S003 - 日志清洗筛查</option>
        <option value="S004">S004 - Web攻击溯源</option>
        <option value="S005">S005 - 内网渗透溯源</option>
        <option value="S006">S006 - 合规审计整改</option>
      </select>
    </div>
    <button id="rpt-btn" class="btn btn-primary">生成报告</button>
  </div>

  <div id="rpt-result" class="result-area" style="display: none;">
    <div class="result-area-header">
      <span class="result-area-title">实训报告</span>
    </div>
    <div id="rpt-result-content"></div>
  </div>
`;

window.PageInit['report'] = () => {
  const btn = document.getElementById('rpt-btn');
  const resultArea = document.getElementById('rpt-result');
  const resultContent = document.getElementById('rpt-result-content');

  btn.addEventListener('click', async () => {
    const studentId = document.getElementById('rpt-student').value.trim();
    const scenarioId = document.getElementById('rpt-scenario').value;

    btn.disabled = true;
    btn.textContent = '生成中...';
    resultArea.style.display = 'none';

    const result = await api.training.report(studentId, scenarioId);

    btn.disabled = false;
    btn.textContent = '生成报告';

    if (result.code === 0) {
      resultArea.style.display = 'block';
      const data = result.data;
      
      let html = '';
      
      // 概览卡片
      const scoreColor = data.average_score >= 80 ? 'var(--success)' : 
                         data.average_score >= 60 ? 'var(--warning)' : 'var(--error)';
      html += `<div class="result-card" style="margin-bottom: 16px;">`;
      html += '<div style="display: flex; gap: 24px; align-items: center;">';
      html += `<div style="text-align: center;">`;
      html += `<div style="font-size: 48px; font-weight: 700; color: ${scoreColor};">${data.average_score.toFixed(0)}</div>`;
      html += `<div style="font-size: 12px; color: var(--n-500);">平均分</div>`;
      html += '</div>';
      html += '<div style="flex: 1;">';
      html += `<div style="font-size: 13px; color: var(--n-600);">综合评级: <span style="font-weight: 600; font-size: 16px;">${data.overall_grade}</span></div>`;
      html += `<div style="font-size: 12px; color: var(--n-500); margin-top: 4px;">完成 ${data.completed_tasks}/${data.total_tasks} 个任务</div>`;
      if (data.scenario_name) {
        html += `<div style="font-size: 12px; color: var(--n-500);">场景: ${data.scenario_name}</div>`;
      }
      html += '</div></div></div>';
      
      // 任务记录
      if (data.task_records && data.task_records.length > 0) {
        html += '<div style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">任务记录</div>';
        html += '<table class="table"><thead><tr><th>任务</th><th>得分</th><th>等级</th><th>尝试次数</th><th>状态</th></tr></thead><tbody>';
        data.task_records.forEach(record => {
          const gradeColor = record.grade === 'A' ? 'var(--success)' : 
                            record.grade === 'B' ? 'var(--warning)' : 'var(--error)';
          html += `<tr>`;
          html += `<td style="font-weight: 500;">${record.title || record.task_id}</td>`;
          html += `<td style="color: ${gradeColor}; font-weight: 600;">${record.score}</td>`;
          html += `<td><span class="badge badge-${record.grade === 'A' ? 'low' : record.grade === 'B' ? 'medium' : 'high'}">${record.grade}</span></td>`;
          html += `<td>${record.attempts}</td>`;
          html += `<td>${record.status}</td>`;
          html += '</tr>';
        });
        html += '</tbody></table>';
      }
      
      // 薄弱项分析
      if (data.weaknesses && data.weaknesses.length > 0) {
        html += '<div style="font-size: 13px; font-weight: 600; margin: 16px 0 8px;">薄弱项分析</div>';
        data.weaknesses.forEach(w => {
          html += `<div class="result-card" style="margin-bottom: 8px; border-left: 4px solid var(--risk-high);">`;
          html += `<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">`;
          html += `<span style="font-weight: 500;">${w.category}</span>`;
          html += `<span style="font-size: 11px; color: var(--n-500);">得分: ${w.score}</span>`;
          html += '</div>';
          if (w.description) html += `<div style="font-size: 12px; color: var(--n-600);">${w.description}</div>`;
          if (w.suggestion) html += `<div style="font-size: 11px; color: var(--accent-primary); margin-top: 4px;">建议: ${w.suggestion}</div>`;
          html += '</div>';
        });
      }
      
      // 提升方案
      if (data.improvement_plan) {
        html += `<div class="result-card" style="margin-top: 16px;">
          <div style="font-weight: 600; margin-bottom: 8px;">能力提升方案</div>
          <div style="font-size: 13px; color: var(--n-600); white-space: pre-wrap;">${data.improvement_plan}</div>
        </div>`;
      }
      
      // 总结
      if (data.summary) {
        html += `<div class="result-card" style="margin-top: 16px;">
          <div style="font-weight: 600; margin-bottom: 8px;">实训总结</div>
          <div style="font-size: 13px; color: var(--n-600);">${data.summary}</div>
        </div>`;
      }
      
      resultContent.innerHTML = html;
    } else {
      alert(`生成失败: ${result.msg}`);
    }
  });
};
