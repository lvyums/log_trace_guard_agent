// API request wrapper - paths aligned to backend modules/*/router.py

var Api = {
  base: (typeof APP_CONFIG !== 'undefined') ? APP_CONFIG.apiBase : '',

  async request(method, url, data, options) {
    options = options || {};
    var config = Object.assign({
      method: method,
      headers: { 'Content-Type': 'application/json' },
    }, options);

    if (data && method !== 'GET') {
      if (data instanceof FormData) {
        delete config.headers['Content-Type'];
        config.body = data;
      } else {
        config.body = JSON.stringify(data);
      }
    }

    try {
      var resp = await fetch(this.base + url, config);
      if (!resp.ok) {
        return { success: false, data: null, msg: 'HTTP ' + resp.status };
      }
      var json = await resp.json();
      if (json.code === 0 || json.code === 200) {
        return { success: true, data: json.data, msg: json.msg };
      }
      return { success: false, data: null, msg: json.msg || 'request failed' };
    } catch (err) {
      return { success: false, data: null, msg: 'Network error: ' + err.message };
    }
  },

  get: function(url, params) {
    var query = params ? '?' + new URLSearchParams(params).toString() : '';
    return this.request('GET', url + query);
  },

  post: function(url, data) {
    return this.request('POST', url, data);
  },

  upload: function(url, formData) {
    return this.request('POST', url, formData);
  },

  // Module 1: Log Parse (prefix: /api/v1/log-parse)
  logParse: {
    identify: function(data) { return Api.post('/api/v1/log-parse/identify', data); },
    parse: function(data) { return Api.post('/api/v1/log-parse/parse', data); },
    assess: function(data) { return Api.post('/api/v1/log-parse/assess', data); },
    batch: function(data) { return Api.post('/api/v1/log-parse/parse/batch', data); },
  },

  // Module 2: Log Collect (prefix: /api/v1/log-collect)
  logCollect: {
    match: function(data) { return Api.post('/api/v1/log-collect/match', data); },
    plan: function(data) { return Api.post('/api/v1/log-collect/plan', data); },
    fault: function(data) { return Api.post('/api/v1/log-collect/fault/diagnose', data); },
    arch: function(data) { return Api.post('/api/v1/log-collect/architecture/recommend', data); },
  },

  // Module 3: Script Gen (prefix: /api/v1/script-gen)
  scriptGen: {
    regex: function(data) { return Api.post('/api/v1/script-gen/regex', data); },
    esQuery: function(data) { return Api.post('/api/v1/script-gen/es-query', data); },
    platform: function(data) { return Api.post('/api/v1/script-gen/platform', data); },
    trace: function(data) { return Api.post('/api/v1/script-gen/trace', data); },
    optimize: function(data) { return Api.post('/api/v1/script-gen/optimize', data); },
  },

  // Module 4: Compliance (prefix: /api/v1/compliance)
  compliance: {
    qa: function(data) { return Api.post('/api/v1/compliance/qa', data); },
    baseline: function(data) { return Api.post('/api/v1/compliance/baseline', data); },
    check: function(data) { return Api.post('/api/v1/compliance/check', data); },
  },

  // Module 5: Training (prefix: /api/v1/training)
  training: {
    scenarios: function() { return Api.post('/api/v1/training/dispatch', { scenario_id: '', category: '' }); },
    submit: function(data) { return Api.post('/api/v1/training/submit', data); },
    report: function(data) { return Api.post('/api/v1/training/report', data); },
  },
};
