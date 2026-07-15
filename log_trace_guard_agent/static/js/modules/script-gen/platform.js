/**
 * 平台选型页面
 */
window.Pages = window.Pages || {};
window.PageInit = window.PageInit || {};

window.Pages['platform'] = () => `
  <div class="main-header">
    <h1 class="main-title">平台选型</h1>
    <p class="main-subtitle">根据需求推荐日志管理平台</p>
  </div>

  <div class="card">
    <div class="form-group">
      <label class="form-label">设备数量</label>
      <input id="plat-count" class="input" type="number" value="100" min="1">
    </div>
    <div class="form-group">
      <label class="form-label">日志量级</label>
      <select id="plat-volume" class="input">
        <option value="small">小型（<1GB/天）</option>
        <option value="medium" selected>中型（1-10GB/天）</option>
        <option value="large">大型（>10GB/天）</option>
      </select>
    </div>
    <div class="form-group">
      <label class="form-label">预算范围</label>
      <select id="plat-budget" class="input">
        <option value="low">低预算</option>
        <option value="medium" selected>中等预算</option>
        <option value="high">高预算</option>
      </select>
    </div>
    <div class="form-group">
      <label class="form-label">团队技能</label>
      <select id="plat-skill" class="input">
        <option value="basic">初级</option>
        <option value="intermediate" selected>中级</option>
        <option value="advanced">高级</option>
      </select>
    </div>
    <button id="plat-btn" class="btn btn-primary">推荐平台</button>
  </div>

  <div id="plat-result" class="result-area" style="display: none;">
    <div class="result-area-header">
      <span class="result-area-title">推荐结果</span>
    </div>
    <div id="plat-result-content"></div>
  </div>
`;

window.PageInit['platform'] = () => {
  const countInput = document.getElementById('plat-count');
  const volumeSelect = document.getElementById('plat-volume');
  const budgetSelect = document.getElementById('plat-budget');
  const skillSelect = document.getElementById('plat-skill');
  const btn = document.getElementById('plat-btn');
  const resultArea = document.getElementById('plat-result');
  const resultContent = document.getElementById('plat-result-content');

  btn.addEventListener('click', async () => {
    const deviceCount = parseInt(countInput.value) || 100;
    const dailyLogVolume = volumeSelect.value;
    const budget = budgetSelect.value;
    const teamSkill = skillSelect.value;

    btn.disabled = true;
    btn.textContent = '推荐中...';
    resultArea.style.display = 'none';

    const result = await api.scriptGen.platform(deviceCount, dailyLogVolume, budget, teamSkill);

    btn.disabled = false;
    btn.textContent = '推荐平台';

    if (result.code === 0) {
      resultArea.style.display = 'block';
      const data = result.data;
      
      let html = '';
      
      // 推荐平台
      if (data.recommendation) {
        const rec = data.recommendation;
        html += '<div class="result-card" style="border-left: 4px solid var(--accent-primary);">';
        html += `<div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">${rec.name}</div>`;
        html += `<div style="font-size: 12px; color: var(--n-500); margin-bottom: 12px;">${rec.type || ''}</div>`;
        
        if (rec.pros && rec.pros.length > 0) {
          html += '<div style="margin-bottom: 8px;"><div style="font-size: 12px; font-weight: 600; margin-bottom: 4px;">优势</div>';
          html += '<ul style="margin: 0; padding-left: 16px; font-size: 12px; color: var(--success);">';
          rec.pros.forEach(pro => { html += `<li>${pro}</li>`; });
          html += '</ul></div>';
        }
        
        if (rec.cons && rec.cons.length > 0) {
          html += '<div style="margin-bottom: 8px;"><div style="font-size: 12px; font-weight: 600; margin-bottom: 4px;">劣势</div>';
          html += '<ul style="margin: 0; padding-left: 16px; font-size: 12px; color: var(--error);">';
          rec.cons.forEach(con => { html += `<li>${con}</li>`; });
          html += '</ul></div>';
        }
        
        if (rec.estimated_cost) {
          html += `<div style="font-size: 12px; color: var(--n-600);">预估成本: ${rec.estimated_cost}</div>`;
        }
        
        html += '</div>';
      }
      
      // 备选方案
      if (data.alternatives && data.alternatives.length > 0) {
        html += '<div style="margin-top: 16px;"><div style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">备选方案</div>';
        data.alternatives.forEach(alt => {
          html += '<div class="result-card" style="margin-bottom: 8px;">';
          html += `<div style="font-size: 14px; font-weight: 500;">${alt.name}</div>`;
          html += `<div style="font-size: 12px; color: var(--n-500);">${alt.type || ''}</div>`;
          if (alt.estimated_cost) {
            html += `<div style="font-size: 12px; color: var(--n-600); margin-top: 4px;">预估成本: ${alt.estimated_cost}</div>`;
          }
          html += '</div>';
        });
        html += '</div>';
      }
      
      // 总结
      if (data.summary) {
        html += `<div style="margin-top: 16px; padding: 12px; background: var(--n-100); border-radius: 6px; font-size: 13px; color: var(--n-600);">${data.summary}</div>`;
      }
      
      resultContent.innerHTML = html;
    } else {
      alert(`推荐失败: ${result.msg}`);
    }
  });
};
