/* ============================================
   主应用入口 — Vue3 + Element Plus 初始化
   ============================================ */

(function() {
  try {
    const { createApp } = Vue;

    // 路由映射：path → 组件名
    const ROUTE_MAP = {
      '/log-parse/identify': 'log-parse-identify',
      '/log-parse/parse': 'log-parse-parse',
      '/log-parse/assess': 'log-parse-assess',
      '/log-parse/batch': 'log-parse-batch',
      '/log-collect/match': 'log-collect-match',
      '/log-collect/plan': 'log-collect-plan',
      '/log-collect/fault': 'log-collect-fault',
      '/log-collect/arch': 'log-collect-arch',
      '/script-gen/regex': 'script-gen-regex',
      '/script-gen/es-query': 'script-gen-esquery',
      '/script-gen/platform': 'script-gen-platform',
      '/script-gen/trace': 'script-gen-trace',
      '/script-gen/optimize': 'script-gen-optimize',
      '/compliance/qa': 'compliance-qa',
      '/compliance/baseline': 'compliance-baseline',
      '/compliance/check': 'compliance-check',
      '/training/scenarios': 'training-scenarios',
      '/training/submit': 'training-submit',
      '/training/report': 'training-report',
    };

    const app = createApp({
      data() {
        return {
          ready: false,
          currentModule: 'log-parse',
          currentPath: '/log-parse/identify',
          sidebarCollapsed: false,
          isDark: true,
          isTrainingMode: false,
          showTour: false,
          modules: APP_CONFIG.modules,
        };
      },
      computed: {
        currentMode() {
          return this.isTrainingMode ? 'training' : 'ops';
        },
        viewComponent() {
          return ROUTE_MAP[this.currentPath] || '';
        },
      },
      methods: {
        switchModule(key) {
          this.currentModule = key;
          const mod = this.modules.find(m => m.key === key);
          if (mod && mod.children.length) {
            this.currentPath = mod.children[0].path;
          }
          this.updateUrl();
        },
        navigate(path) {
          this.currentPath = path;
          const mod = this.modules.find(m => m.children.some(c => c.path === path));
          if (mod) this.currentModule = mod.key;
          this.updateUrl();
        },
        toggleSidebar() {
          this.sidebarCollapsed = !this.sidebarCollapsed;
        },
        toggleTheme() {
          this.isDark = !this.isDark;
          this.applyTheme();
          localStorage.setItem('lg-theme', this.isDark ? 'dark' : 'light');
        },
        toggleMode(val) {
          this.isTrainingMode = val;
          localStorage.setItem('lg-mode', val ? 'training' : 'ops');
          if (val && !localStorage.getItem('lg-tour-seen')) {
            this.showTour = true;
          }
        },
        applyTheme() {
          const theme = this.isDark ? 'dark' : 'light';
          document.documentElement.setAttribute('data-theme', theme);
          if (this.isDark) {
            document.documentElement.classList.add('dark');
          } else {
            document.documentElement.classList.remove('dark');
          }
        },
        updateUrl() {
          const hash = '#' + this.currentPath;
          if (window.location.hash !== hash) {
            window.location.hash = hash;
          }
        },
        parseHash() {
          const hash = window.location.hash.slice(1);
          if (hash && ROUTE_MAP[hash]) {
            this.currentPath = hash;
            const mod = this.modules.find(m => m.children.some(c => c.path === hash));
            if (mod) this.currentModule = mod.key;
          }
        },
        initFromStorage() {
          const theme = localStorage.getItem('lg-theme');
          if (theme) {
            this.isDark = theme === 'dark';
            this.applyTheme();
          }
          const mode = localStorage.getItem('lg-mode');
          if (mode === 'training') {
            this.isTrainingMode = true;
          }
          const tourSeen = localStorage.getItem('lg-tour-seen');
          if (!tourSeen) {
            this.showTour = true;
          }
        },
        closeTour() {
          this.showTour = false;
          localStorage.setItem('lg-tour-seen', 'true');
        },
      },
      mounted() {
        this.parseHash();
        this.initFromStorage();
        this.ready = true;

        window.addEventListener('hashchange', () => {
          this.parseHash();
        });
      },
    });

    // 注册全局混入
    app.mixin(GlobalMixin);

    // 注册 Element Plus
    app.use(ElementPlus, {
      locale: ElementPlusLocaleZhCn,
    });

    // 注册 Element Plus 图标
    for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
      app.component(key, component);
    }

    // 注册全局组件
    app.component('global-tour', GlobalTour);
    app.component('input-guide', InputGuide);
    app.component('tip-wrapper', TipWrapper);
    app.component('alert-guide', AlertGuide);
    app.component('knowledge-panel', KnowledgePanel);
    app.component('empty-guide', EmptyGuide);
    app.component('result-guide', ResultGuide);
    app.component('confirm-batch', ConfirmBatch);
    app.component('risk-badge', RiskBadge);
    app.component('risk-card', RiskCard);
    app.component('code-block', CodeBlock);

    // 注册页面组件
    app.component('log-parse-identify', LogParseIdentify);
    app.component('log-parse-parse', LogParseParse);
    app.component('log-parse-assess', LogParseAssess);
    app.component('log-parse-batch', LogParseBatch);
    app.component('log-collect-match', LogCollectMatch);
    app.component('log-collect-plan', LogCollectPlan);
    app.component('log-collect-fault', LogCollectFault);
    app.component('log-collect-arch', LogCollectArch);
    app.component('script-gen-regex', ScriptGenRegex);
    app.component('script-gen-esquery', ScriptGenEsquery);
    app.component('script-gen-platform', ScriptGenPlatform);
    app.component('script-gen-trace', ScriptGenTrace);
    app.component('script-gen-optimize', ScriptGenOptimize);
    app.component('compliance-qa', ComplianceQa);
    app.component('compliance-baseline', ComplianceBaseline);
    app.component('compliance-check', ComplianceCheck);
    app.component('training-scenarios', TrainingScenarios);
    app.component('training-submit', TrainingSubmit);
    app.component('training-report', TrainingReport);

    // 挂载
    app.mount('#app');
    console.log('[App] Mounted successfully');
    window.__appMounted = true;
  } catch (e) {
    console.error('[App] Mount failed:', e);
    window.__appError = e.message;
  }
})();
