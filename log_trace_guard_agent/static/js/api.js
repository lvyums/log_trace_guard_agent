/**
 * API 统一封装 — 所有后端接口调用集中管理
 */
const API_BASE = '/api/v1';

/**
 * 通用请求函数
 */
async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const config = {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  };
  
  try {
    const response = await fetch(url, config);
    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`API 请求失败: ${path}`, error);
    return { code: -1, msg: `网络请求失败: ${error.message}`, data: null };
  }
}

/**
 * 模块一：日志解析
 */
const logParse = {
  /** 识别日志类型 */
  identify: (logLine, inputType = 'text') => 
    request('/log-parse/identify', {
      method: 'POST',
      body: JSON.stringify({ log_line: logLine, input_type: inputType }),
    }),

  /** 结构化解析 */
  parse: (logLine) => 
    request('/log-parse/parse', {
      method: 'POST',
      body: JSON.stringify({ log_line: logLine }),
    }),

  /** 风险研判 */
  assess: (logLine) => 
    request('/log-parse/assess', {
      method: 'POST',
      body: JSON.stringify({ log_line: logLine }),
    }),

  /** 字段释义 */
  explain: (fieldName, deviceType) => 
    request('/log-parse/explain', {
      method: 'POST',
      body: JSON.stringify({ field_name: fieldName, device_type: deviceType }),
    }),

  /** 批量解析 */
  batchParse: (logs, assess = false) => 
    request('/log-parse/parse/batch', {
      method: 'POST',
      body: JSON.stringify({ logs, assess }),
    }),
};

/**
 * 模块二：日志采集
 */
const logCollect = {
  /** 设备匹配 */
  match: (deviceType, deviceModel = '', scale = 'small') => 
    request('/log-collect/match', {
      method: 'POST',
      body: JSON.stringify({ device_type: deviceType, device_model: deviceModel, scale }),
    }),

  /** 采集方案 */
  plan: (deviceType, deviceModel = '', scale = 'small', includeConfig = true) => 
    request('/log-collect/plan', {
      method: 'POST',
      body: JSON.stringify({ device_type: deviceType, device_model: deviceModel, scale, include_config: includeConfig }),
    }),

  /** 故障诊断 */
  diagnose: (symptom, deviceType = null, protocol = null, errorLog = null) => 
    request('/log-collect/fault/diagnose', {
      method: 'POST',
      body: JSON.stringify({ symptom, device_type: deviceType, protocol, error_log: errorLog }),
    }),

  /** 架构推荐 */
  recommendArch: (deviceCount, dailyLogVolume, budget, teamSkill) => 
    request('/log-collect/architecture/recommend', {
      method: 'POST',
      body: JSON.stringify({ device_count: deviceCount, daily_log_volume: dailyLogVolume, budget, team_skill: teamSkill }),
    }),
};

/**
 * 模块三：脚本生成
 */
const scriptGen = {
  /** 正则生成 */
  regex: (scenario, logSample = '', deviceType = '') => 
    request('/script-gen/regex', {
      method: 'POST',
      body: JSON.stringify({ scenario, log_sample: logSample, device_type: deviceType }),
    }),

  /** ES 查询生成 */
  esQuery: (searchScenario, indexPattern = '', timeRange = '') => 
    request('/script-gen/es-query', {
      method: 'POST',
      body: JSON.stringify({ search_scenario: searchScenario, index_pattern: indexPattern, time_range: timeRange }),
    }),

  /** 平台选型 */
  platform: (deviceCount, dailyLogVolume, budget, teamSkill, requirements = []) => 
    request('/script-gen/platform', {
      method: 'POST',
      body: JSON.stringify({ device_count: deviceCount, daily_log_volume: dailyLogVolume, budget, team_skill: teamSkill, requirements }),
    }),

  /** 攻击溯源 */
  trace: (logs, attackType = '', startTime = '', endTime = '') => 
    request('/script-gen/trace', {
      method: 'POST',
      body: JSON.stringify({ logs, attack_type: attackType, start_time: startTime, end_time: endTime }),
    }),

  /** 脚本优化 */
  optimize: (script, scriptType, scenario = '') => 
    request('/script-gen/optimize', {
      method: 'POST',
      body: JSON.stringify({ script, script_type: scriptType, scenario }),
    }),
};

/**
 * 模块四：合规审计基线
 */
const compliance = {
  /** 合规标准智能问答 */
  qa: (question, assetType = '', standardFilter = '') => 
    request('/compliance/qa', {
      method: 'POST',
      body: JSON.stringify({ question, asset_type: assetType, standard_filter: standardFilter }),
    }),

  /** 合规基线自动生成 */
  baseline: (assetCount, businessType, deviceTypes = [], monitorScenarios = [], industry = '') => 
    request('/compliance/baseline', {
      method: 'POST',
      body: JSON.stringify({ asset_count: assetCount, business_type: businessType, device_types: deviceTypes, monitor_scenarios: monitorScenarios, industry }),
    }),

  /** 合规自查 */
  check: (params) => 
    request('/compliance/check', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
};

/**
 * 模块五：交互式攻防实训
 */
const training = {
  /** 下发实训任务 */
  dispatch: (scenarioId = '', category = '') => 
    request('/training/dispatch', {
      method: 'POST',
      body: JSON.stringify({ scenario_id: scenarioId, category }),
    }),

  /** 提交实训答案 */
  submit: (scenarioId, taskId, submitType, content, studentId = '') => 
    request('/training/submit', {
      method: 'POST',
      body: JSON.stringify({ scenario_id: scenarioId, task_id: taskId, submit_type: submitType, content, student_id: studentId }),
    }),

  /** 生成实训报告 */
  report: (studentId = '', scenarioId = '') => 
    request('/training/report', {
      method: 'POST',
      body: JSON.stringify({ student_id: studentId, scenario_id: scenarioId }),
    }),
};

// 导出到全局
window.api = { logParse, logCollect, scriptGen, compliance, training };
