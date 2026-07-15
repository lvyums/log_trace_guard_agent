/**
 * 路由 + 全局状态管理
 */
const App = {
  /** 路由表 */
  routes: {
    '/log-parse/identify': { module: 'log-parse', page: 'identify', title: '日志识别' },
    '/log-parse/parse': { module: 'log-parse', page: 'parse', title: '结构化解析' },
    '/log-parse/assess': { module: 'log-parse', page: 'assess', title: '风险研判' },
    '/log-parse/batch': { module: 'log-parse', page: 'batch', title: '批量解析' },
    '/log-collect/match': { module: 'log-collect', page: 'match', title: '设备匹配' },
    '/log-collect/plan': { module: 'log-collect', page: 'plan', title: '采集方案' },
    '/log-collect/fault': { module: 'log-collect', page: 'fault', title: '故障诊断' },
    '/log-collect/arch': { module: 'log-collect', page: 'arch', title: '架构推荐' },
    '/script-gen/regex': { module: 'script-gen', page: 'regex', title: '正则生成' },
    '/script-gen/es-query': { module: 'script-gen', page: 'es-query', title: 'ES 查询生成' },
    '/script-gen/platform': { module: 'script-gen', page: 'platform', title: '平台选型' },
    '/script-gen/trace': { module: 'script-gen', page: 'trace', title: '攻击溯源' },
    '/script-gen/optimize': { module: 'script-gen', page: 'optimize', title: '脚本优化' },
    '/compliance/qa': { module: 'compliance', page: 'qa', title: '合规问答' },
    '/compliance/baseline': { module: 'compliance', page: 'baseline', title: '基线生成' },
    '/compliance/check': { module: 'compliance', page: 'check', title: '合规自查' },
    '/training/scenarios': { module: 'training', page: 'scenarios', title: '实训场景' },
    '/training/submit': { module: 'training', page: 'submit', title: '提交答案' },
    '/training/report': { module: 'training', page: 'report', title: '实训报告' },
  },

  /** 当前路由 */
  currentRoute: null,

  /** 初始化 */
  init() {
    window.addEventListener('hashchange', () => this.navigate());
    this.navigate();
  },

  /** 导航 */
  navigate() {
    const hash = window.location.hash.slice(1) || '/log-parse/identify';
    const route = this.routes[hash];
    
    if (!route) {
      console.warn('未知路由:', hash);
      return;
    }

    this.currentRoute = { ...route, path: hash };
    this.render();
  },

  /** 渲染页面 */
  render() {
    const currentModule = this.currentRoute.module;

    // 切换侧边栏模块显示
    document.querySelectorAll('.sidebar-section').forEach(section => {
      section.style.display = section.dataset.module === currentModule ? 'block' : 'none';
    });

    // 更新顶部导航高亮
    document.querySelectorAll('.header-nav-item').forEach(item => {
      item.classList.toggle('active', item.dataset.module === currentModule);
    });

    // 更新侧边栏项高亮
    document.querySelectorAll('.sidebar-item').forEach(item => {
      item.classList.toggle('active', item.dataset.path === this.currentRoute.path);
    });

    // 更新主内容区
    const main = document.getElementById('main-content');
    if (main && window.Pages && window.Pages[this.currentRoute.page]) {
      main.innerHTML = window.Pages[this.currentRoute.page]();
      // 初始化页面事件
      if (window.PageInit && window.PageInit[this.currentRoute.page]) {
        window.PageInit[this.currentRoute.page]();
      }
    }
  },

  /** 导航到指定路径 */
  goto(path) {
    window.location.hash = path;
  },
};

// 页面注册表
window.Pages = {};
window.PageInit = {};

// 启动
document.addEventListener('DOMContentLoaded', () => App.init());
