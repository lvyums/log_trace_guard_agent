/**
 * 实训场景页面
 */
window.Pages = window.Pages || {};
window.PageInit = window.PageInit || {};

window.Pages['scenarios'] = () => `
  <div class="main-header">
    <h1 class="main-title">攻防实训</h1>
    <p class="main-subtitle">交互式安全实训场景，提升实战能力</p>
  </div>

  <div class="card">
    <div class="form-group">
      <label class="form-label">选择场景</label>
      <select id="tr-scenario" class="input">
        <option value="">全部场景</option>
        <option value="S001">S001 - 日志基础认知（入门）</option>
        <option value="S002">S002 - 日志采集配置（初级）</option>
        <option value="S003">S003 - 日志清洗筛查（中级）</option>
        <option value="S004">S004 - Web攻击溯源（高级）</option>
        <option value="S005">S005 - 内网渗透溯源（高级）</option>
        <option value="S006">S006 - 合规审计整改（中级）</option>
      </select>
    </div>
    <button id="tr-load-btn" class="btn btn-primary">加载场景</button>
  </div>

  <div id="tr-scenarios" class="result-area"></div>
  
  <div id="tr-task-area" class="result-area" style="display: none;">
    <div class="result-area-header">
      <span class="result-area-title" id="tr-task-title">任务详情</span>
    </div>
    <div id="tr-task-content"></div>
  </div>
`;

window.PageInit['scenarios'] = () => {
  const scenarioSelect = document.getElementById('tr-scenario');
  const loadBtn = document.getElementById('tr-load-btn');
  const scenariosArea = document.getElementById('tr-scenarios');
  const taskArea = document.getElementById('tr-task-area');
  const taskTitle = document.getElementById('tr-task-title');
  const taskContent = document.getElementById('tr-task-content');

  loadBtn.addEventListener('click', async () => {
    const scenarioId = scenarioSelect.value;

    loadBtn.disabled = true;
    loadBtn.textContent = '加载中...';
    scenariosArea.innerHTML = '';

    const result = await api.training.dispatch(scenarioId);

    loadBtn.disabled = false;
    loadBtn.textContent = '加载场景';

    if (result.code === 0) {
      const data = result.data;
      
      if (data.scenarios && data.scenarios.length > 0) {
        let html = '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px;">';
        
        data.scenarios.forEach(sc => {
          const scenario = sc.scenario || sc;
          const difficultyColor = scenario.difficulty === '入门' ? 'var(--success)' :
                                  scenario.difficulty === '初级' ? 'var(--info)' :
                                  scenario.difficulty === '中级' ? 'var(--warning)' : 'var(--error)';
          
          html += `<div class="result-card" style="cursor: pointer;" onclick="loadScenarioTasks('${scenario.scenario_id}')">`;
          html += `<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">`;
          html += `<span style="font-weight: 600;">${scenario.name}</span>`;
          html += `<span style="font-size: 11px; padding: 2px 6px; background: ${difficultyColor}; color: white; border-radius: 4px;">${scenario.difficulty}</span>`;
          html += '</div>';
          if (scenario.description) {
            html += `<div style="font-size: 12px; color: var(--n-600); margin-bottom: 8px;">${scenario.description}</div>`;
          }
          html += `<div style="font-size: 11px; color: var(--n-500);">任务数: ${sc.total_tasks || 0}</div>`;
          html += '</div>';
        });
        
        html += '</div>';
        scenariosArea.innerHTML = html;
      } else {
        scenariosArea.innerHTML = '<div class="empty-state"><div class="empty-state-title">暂无场景数据</div></div>';
      }
    } else {
      alert(`加载失败: ${result.msg}`);
    }
  });

  // 全局函数：加载场景任务
  window.loadScenarioTasks = async (scenarioId) => {
    const result = await api.training.dispatch(scenarioId);
    if (result.code === 0 && result.data.scenarios && result.data.scenarios.length > 0) {
      const sc = result.data.scenarios[0];
      const scenario = sc.scenario || sc;
      
      taskArea.style.display = 'block';
      taskTitle.textContent = scenario.name;
      
      let html = '';
      
      // 场景信息
      html += `<div class="result-card" style="margin-bottom: 16px;">`;
      html += `<div style="font-size: 13px; color: var(--n-600); margin-bottom: 8px;">${scenario.description || ''}</div>`;
      if (scenario.objectives && scenario.objectives.length > 0) {
        html += '<div style="font-size: 12px; font-weight: 500; margin-bottom: 4px;">学习目标:</div>';
        html += '<ul style="margin: 0; padding-left: 16px; font-size: 12px; color: var(--n-600);">';
        scenario.objectives.forEach(obj => { html += `<li>${obj}</li>`; });
        html += '</ul>';
      }
      html += '</div>';
      
      // 任务列表
      if (sc.tasks && sc.tasks.length > 0) {
        html += '<div style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">任务列表</div>';
        sc.tasks.forEach((task, idx) => {
          html += `<div class="result-card" style="margin-bottom: 8px;">`;
          html += `<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">`;
          html += `<span style="font-weight: 500;">${idx + 1}. ${task.title}</span>`;
          html += `<span style="font-size: 11px; color: var(--n-500);">${task.submit_type}</span>`;
          html += '</div>';
          if (task.description) {
            html += `<div style="font-size: 12px; color: var(--n-600);">${task.description}</div>`;
          }
          if (task.hint) {
            html += `<div style="font-size: 11px; color: var(--accent-primary); margin-top: 4px;">提示: ${task.hint}</div>`;
          }
          html += '</div>';
        });
      }
      
      taskContent.innerHTML = html;
    }
  };
};
