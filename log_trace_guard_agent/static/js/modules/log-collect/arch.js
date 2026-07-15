/**
 * 架构推荐页面
 */
window.Pages = window.Pages || {};
window.PageInit = window.PageInit || {};

window.Pages['arch'] = () => `
  <div class="main-header">
    <h1 class="main-title">架构推荐</h1>
    <p class="main-subtitle">根据企业规模推荐日志采集架构</p>
  </div>

  <div class="card">
    <div class="form-group">
      <label class="form-label">设备数量</label>
      <input id="arch-count" class="input" type="number" value="100" min="1">
    </div>
    <div class="form-group">
      <label class="form-label">日志量级</label>
      <select id="arch-volume" class="input">
        <option value="small">小型（<1GB/天）</option>
        <option value="medium" selected>中型（1-10GB/天）</option>
        <option value="large">大型（>10GB/天）</option>
      </select>
    </div>
    <div class="form-group">
      <label class="form-label">预算范围</label>
      <select id="arch-budget" class="input">
        <option value="low">低预算</option>
        <option value="medium" selected>中等预算</option>
        <option value="high">高预算</option>
      </select>
    </div>
    <div class="form-group">
      <label class="form-label">团队技能</label>
      <select id="arch-skill" class="input">
        <option value="basic">初级</option>
        <option value="intermediate" selected>中级</option>
        <option value="advanced">高级</option>
      </select>
    </div>
    <button id="arch-btn" class="btn btn-primary">推荐架构</button>
  </div>

  <div id="arch-result" class="result-area" style="display: none;">
    <div class="result-area-header">
      <span class="result-area-title">推荐方案</span>
    </div>
    <div id="arch-result-content"></div>
  </div>
`;

window.PageInit['arch'] = () => {
  const countInput = document.getElementById('arch-count');
  const volumeSelect = document.getElementById('arch-volume');
  const budgetSelect = document.getElementById('arch-budget');
  const skillSelect = document.getElementById('arch-skill');
  const btn = document.getElementById('arch-btn');
  const resultArea = document.getElementById('arch-result');
  const resultContent = document.getElementById('arch-result-content');

  btn.addEventListener('click', async () => {
    const deviceCount = parseInt(countInput.value) || 100;
    const dailyLogVolume = volumeSelect.value;
    const budget = budgetSelect.value;
    const teamSkill = skillSelect.value;

    btn.disabled = true;
    btn.textContent = '推荐中...';
    resultArea.style.display = 'none';

    const result = await api.logCollect.recommendArch(deviceCount, dailyLogVolume, budget, teamSkill);

    btn.disabled = false;
    btn.textContent = '推荐架构';

    if (result.code === 0) {
      resultArea.style.display = 'block';
      const data = result.data;
      
      let html = '<div class="arch-card">';
      html += `<div class="arch-title">${data.recommended_arch || '未知架构'}</div>`;
      
      if (data.architecture_desc) {
        html += `<p style="font-size: 13px; color: var(--n-600); margin-bottom: 16px;">${data.architecture_desc}</p>`;
      }
      
      if (data.components && data.components.length > 0) {
        html += '<div class="arch-section">';
        html += '<div class="arch-section-title">核心组件</div>';
        html += '<ul class="arch-list">';
        data.components.forEach(comp => {
          html += `<li>${comp}</li>`;
        });
        html += '</ul></div>';
      }
      
      if (data.data_flow && data.data_flow.length > 0) {
        html += '<div class="arch-section">';
        html += '<div class="arch-section-title">数据流向</div>';
        html += `<div style="font-size: 13px; color: var(--n-700);">${data.data_flow.join(' → ')}</div>`;
        html += '</div>';
      }
      
      if (data.estimated_cost) {
        html += '<div class="arch-section">';
        html += '<div class="arch-section-title">预估成本</div>';
        html += `<div style="font-size: 13px; color: var(--n-700);">${data.estimated_cost}</div>`;
        html += '</div>';
      }
      
      if (data.pros && data.pros.length > 0) {
        html += '<div class="arch-section">';
        html += '<div class="arch-section-title">优势</div>';
        html += '<ul class="arch-list arch-pros">';
        data.pros.forEach(pro => {
          html += `<li>${pro}</li>`;
        });
        html += '</ul></div>';
      }
      
      if (data.cons && data.cons.length > 0) {
        html += '<div class="arch-section">';
        html += '<div class="arch-section-title">劣势</div>';
        html += '<ul class="arch-list arch-cons">';
        data.cons.forEach(con => {
          html += `<li>${con}</li>`;
        });
        html += '</ul></div>';
      }
      
      html += '</div>';
      resultContent.innerHTML = html;
    } else {
      alert(`推荐失败: ${result.msg}`);
    }
  });
};
