/* ============================================
   全局配置 — 主题、风险等级、指引文案、模块定义
   ============================================ */

var APP_CONFIG = {
  // API 基础路径
  apiBase: '',

  // 风险等级定义
  riskLevels: {
    P0: { label: '极高危', color: '#F53F3F', bg: 'rgba(245,63,63,0.1)', icon: 'CircleCloseFilled' },
    P1: { label: '高危', color: '#FF7D00', bg: 'rgba(255,125,0,0.1)', icon: 'WarningFilled' },
    P2: { label: '中危', color: '#FFC53D', bg: 'rgba(255,197,61,0.1)', icon: 'InfoFilled' },
    P3: { label: '低危', color: '#86909C', bg: 'rgba(134,144,156,0.1)', icon: 'InfoFilled' },
    normal: { label: '正常', color: '#00B42A', bg: 'rgba(0,180,42,0.1)', icon: 'CircleCheckFilled' },
  },

  // 模块定义
  modules: [
    {
      key: 'log-parse', label: '日志解析', icon: 'Search',
      desc: '异构日志标准化解析、字段释义、风险研判',
      children: [
        { path: '/log-parse/identify', label: '日志识别', icon: 'Aim', tip: '输入日志自动识别设备类型与格式' },
        { path: '/log-parse/parse', label: '结构化解析', icon: 'Document', tip: '将原始日志解析为结构化字段' },
        { path: '/log-parse/assess', label: '风险研判', icon: 'Warning', tip: '对日志内容进行安全风险评估' },
        { path: '/log-parse/batch', label: '批量解析', icon: 'Grid', tip: '批量上传日志文件进行解析分析' },
      ],
    },
    {
      key: 'log-collect', label: '日志采集', icon: 'Download',
      desc: '设备匹配、采集方案生成、故障诊断、架构推荐',
      children: [
        { path: '/log-collect/match', label: '设备匹配', icon: 'Monitor', tip: '识别安全设备型号与采集协议' },
        { path: '/log-collect/plan', label: '采集方案', icon: 'Document', tip: '生成标准化日志采集配置方案' },
        { path: '/log-collect/fault', label: '故障诊断', icon: 'Warning', tip: '诊断日志采集中常见故障并给出修复建议' },
        { path: '/log-collect/arch', label: '架构推荐', icon: 'Share', tip: '根据企业规模推荐日志采集架构' },
      ],
    },
    {
      key: 'script-gen', label: '脚本生成', icon: 'Monitor',
      desc: '正则生成、ES查询、平台选型、攻击溯源、脚本优化',
      children: [
        { path: '/script-gen/regex', label: '正则生成', icon: 'MagicStick', tip: '根据日志样本自动生成正则表达式' },
        { path: '/script-gen/es-query', label: 'ES查询生成', icon: 'Search', tip: '生成Elasticsearch查询语句' },
        { path: '/script-gen/platform', label: '平台选型', icon: 'DataAnalysis', tip: '日志平台对比选型推荐' },
        { path: '/script-gen/trace', label: '攻击溯源', icon: 'Connection', tip: '生成攻击链溯源检索脚本' },
        { path: '/script-gen/optimize', label: '脚本优化', icon: 'SetUp', tip: '优化现有正则或查询脚本性能' },
      ],
    },
    {
      key: 'compliance', label: '合规审计', icon: 'Checked',
      desc: '合规问答、基线生成、合规自查',
      children: [
        { path: '/compliance/qa', label: '合规问答', icon: 'ChatDotRound', tip: '回答等保2.0/网安法/数据安全法相关问题' },
        { path: '/compliance/baseline', label: '基线生成', icon: 'Document', tip: '根据资产信息生成合规基线报告' },
        { path: '/compliance/check', label: '合规自查', icon: 'CircleCheck', tip: '检查现有配置是否满足合规要求' },
      ],
    },
    {
      key: 'training', label: '攻防实训', icon: 'Flag',
      desc: '实训场景、提交答案、实训报告',
      children: [
        { path: '/training/scenarios', label: '实训场景', icon: 'Reading', tip: '查看并选择攻防实训场景' },
        { path: '/training/submit', label: '提交答案', icon: 'Promotion', tip: '提交实训答案并获取评分' },
        { path: '/training/report', label: '实训报告', icon: 'DataLine', tip: '查看实训统计与详细报告' },
      ],
    },
  ],

  // 指引文案 — 业务导向，非UI描述
  guidance: {
    global: {
      title: '安全日志分析标准工作流',
      steps: [
        {
          title: '第一步：日志识别 — 确认你在看什么',
          desc: '安全事件响应的第一步永远是识别日志来源。不同设备的日志格式差异巨大：防火墙是syslog格式，WAF可能是JSON，Web服务器走combined格式。粘贴日志后，系统自动识别设备类型和日志格式，这是后续所有分析的基础。',
        },
        {
          title: '第二步：结构化解析 — 从乱码到结构化数据',
          desc: '原始日志对人眼不友好。结构化解析把一行syslog拆解成：时间戳、源IP、目标IP、事件类型、用户名等字段。这是做关联分析的前提——比如要查"哪个IP在什么时间访问了哪个服务"，必须先有结构化字段。',
        },
        {
          title: '第三步：风险研判 — 判断是否需要响应',
          desc: '不是所有异常日志都是攻击。系统会结合RAG知识库和规则引擎，判断这条日志是正常运维操作还是真实威胁。P0/P1级别的风险会给出标准化处置步骤，比如"立即封禁源IP"或"排查横向移动路径"。',
        },
        {
          title: '关联分析：跨模块联动',
          desc: '日志解析结果会自动传递给后续模块。比如在日志解析中识别出的设备类型，可以直接用于生成采集方案；发现的攻击特征，可以直接生成溯源脚本。不要孤立使用单个模块。',
        },
        {
          title: '运维 vs 实训两种工作模式',
          desc: '运维模式：轻量操作指引，侧重批量处理和快速响应。实训模式：强制分步引导，每步有评分和知识点讲解，适合课堂和技能考核。右上角一键切换。',
        },
      ],
    },
    tooltips: {
      logInput: {
        label: '日志输入要点',
        desc: '粘贴完整原始日志行，不要裁剪或重格式化。系统需要完整的时间戳、优先级、主机名来准确识别设备类型。',
        example: '正确: <22>Jan  5 12:34:56 sshd[12345]: Failed password for root from 192.168.1.100 port 22\n错误: sshd: Failed password (缺少pri头和时间戳会导致识别失败)',
      },
      fileUpload: {
        label: '批量上传建议',
        desc: '单文件最大10MB。如果日志量很大，建议按设备类型分文件上传——混合不同设备的日志会降低识别准确率。',
        example: '推荐文件组织: fw_syslog.txt(防火墙) / waf_events.json(WAF) / nginx_access.log(Web)',
      },
      deviceType: {
        label: '为什么选对设备类型很重要',
        desc: '不同设备的日志字段含义完全不同。同样是"action"字段，防火墙里是"deny/permit"，WAF里是"block/allow"，IDS里是"alert/pass"。选错设备类型会导致字段释义全部错误。',
        example: '常见对应: 防火墙(firewall)→syslog / WAF(waf)→JSON / 服务器(server)→文件上传',
      },
      企业规模: {
        label: '规模决定架构复杂度',
        desc: '小型企业可以用单台syslog服务器；中型需要前置Syslog-ng做聚合；大型需要Kafka+Federation分层架构。选错规模会导致方案不落地。',
        example: '<100人→单机syslog / 100-1000人→Syslog-ng集中 / >1000人→Kafka+ES分层',
      },
    },
    emptyStates: {
      logParse: {
        title: '安全分析从一行日志开始',
        desc: '粘贴任何安全设备的原始日志，系统会自动识别设备类型、解析字段、评估风险等级。也可以上传整个日志文件做批量分析。',
        action: '加载真实攻击样例',
        hint: '典型场景：收到IDS告警后，粘贴原始日志确认是否为误报；分析WAF拦截日志判断是否为真实攻击；批量解析防火墙日志统计异常连接。',
      },
      collectPlan: {
        title: '日志采集是安全运营的基石',
        desc: '没有日志就没有检测能力。选择设备类型和企业规模，系统会生成符合等保要求的标准化采集方案，包含Syslog配置、传输加密、存储策略。',
        action: '查看防火墙采集方案',
        hint: '等保2.0要求：日志留存≥180天，传输需加密，采集需覆盖所有安全设备和服务器。选错设备类型会导致配置不可用。',
      },
      training: {
        title: '实战化攻防技能训练',
        desc: '每个场景基于真实安全事件设计，包含：攻击日志样本、分析任务、评分标准和知识点讲解。从初级的SSH暴力破解到高级的内网横向移动，逐步提升分析能力。',
        action: '开始SSH暴力破解检测',
        hint: '实训模式会记录每步操作并评分。分析日志时注意：先识别设备类型→提取关键字段→判断风险等级→给出处置建议。漏掉任何一步都会扣分。',
      },
      script: {
        title: '自动化安全分析脚本',
        desc: '手动分析效率低。输入你的分析需求，自动生成正则表达式、ES查询语句、溯源脚本等。所有脚本都经过性能优化，可直接用于生产环境。',
        action: '生成SSH暴力破解正则',
        hint: '典型场景：需要批量从日志中提取异常登录IP→生成正则；需要在ES中检索特定攻击→生成DSL查询；需要自动化溯源→生成批量脚本。',
      },
    },
    resultGuides: {
      logParse: {
        identify: '识别结果决定了后续分析的准确性。如果设备类型识别错误，请手动指定设备类型后重新分析——这通常发生在非标准syslog格式或自定义日志模板的情况下。',
        parse: '结构化字段可直接用于SIEM告警规则。比如从SSH日志中提取的"src_ip"字段，可以直接写入Elasticsearch的检测规则中匹配暴力破解模式。',
        assess: '风险研判结果包含三个关键信息：风险等级(决定是否需要立即响应)、置信度(判断是否需要人工复核)、处置指引(标准化响应步骤)。P0级别请立即执行处置步骤。',
        batch: '批量解析结果支持导出为CSV，可直接导入Excel做二次分析。重点关注：异常分布统计、高风险IP TOP10、攻击类型分布——这些是安全周报的核心数据。',
      },
      collectPlan: '配置代码可直接粘贴到设备命令行执行。实施步骤按"网络连通→配置采集→验证数据→监控告警"的顺序，每步都有验证命令。如果采集不通，先检查防火墙是否放行了Syslog端口(UDP 514)。',
      compliance: '基线报告中的不合规项按风险排序：红色=必须立即整改(等保测评会直接不通过)、黄色=建议整改(有安全风险但不影响测评)、灰色=最佳实践(提升安全水位)。先处理红色项。',
      training: '分析日志时的标准流程：1.先识别设备和日志格式 2.提取攻击者IP、时间、手法 3.判断风险等级 4.给出处置建议。评分依据是这四步的完整性和准确性。漏掉"判断风险等级"这一步会丢20%的分。',
    },
    // 模块级操作指引（页面顶部提示条）
    moduleTips: {
      '/log-parse/identify': {
        type: 'info',
        title: '日志识别是分析的起点',
        content: '粘贴一行完整原始日志，系统会自动识别：①设备类型(防火墙/WAF/IDS等) ②日志格式(syslog/JSON/CSV) ③关键字段。识别准确率取决于日志是否包含完整的PRI头和时间戳。',
      },
      '/log-parse/parse': {
        type: 'info',
        title: '结构化解析让日志可被检索',
        content: '原始日志是给人看的文本，结构化日志是给机器检索的数据。解析后的字段可以直接写入Elasticsearch索引，用于后续的批量检索和告警规则。',
      },
      '/log-parse/assess': {
        type: 'warning',
        title: '风险研判需要结合上下文',
        content: '单独一条日志的风险判断有局限性。建议：先在「日志识别」中确认设备类型，再在「结构化解析」中提取关键字段，最后在这里做综合研判。多维度输入能显著提高准确率。',
      },
      '/log-parse/batch': {
        type: 'info',
        title: '批量分析前建议按设备分文件',
        content: '混合不同设备的日志会降低识别准确率。建议按设备类型分文件上传，每批处理同类型日志。系统会自动统计：风险分布、异常IP TOP10、攻击类型分布。',
      },
      '/log-collect/match': {
        type: 'info',
        title: '设备匹配决定采集配置',
        content: '选错设备类型会导致生成的配置无法使用。如果你不确定设备类型，先用「日志识别」分析一条该设备的日志，系统会自动判断。',
      },
      '/log-collect/plan': {
        type: 'warning',
        title: '采集方案必须满足等保要求',
        content: '等保2.0明确要求：日志留存≥180天、传输加密、覆盖所有安全设备。生成方案后请逐项核对是否满足合规要求，不满足的需要手动补充。',
      },
      '/log-collect/fault': {
        type: 'warning',
        title: '故障诊断前先确认基础条件',
        content: '80%的采集故障是基础问题：①网络不通( ping目标IP ) ②端口未开放( telnet IP 514 ) ③防火墙拦截( 检查ACL )。先排除这三项再使用诊断工具。',
      },
      '/log-collect/arch': {
        type: 'info',
        title: '架构设计要考虑扩展性',
        content: '当前方案基于当前规模，但安全设备会持续增加。建议：预留30%的采集容量，选择支持水平扩展的架构(如Kafka分层)，避免未来重构。',
      },
      '/script-gen/regex': {
        type: 'info',
        title: '正则表达式用于日志批量检索',
        content: '生成的正则可用于：SIEM告警规则、ELK的grok解析、Python日志分析脚本、grep命令行检索。如果匹配速度慢，优先使用非捕获组(?:...)优化。',
      },
      '/script-gen/es-query': {
        type: 'info',
        title: 'ES查询用于安全事件检索',
        content: '生成的DSL可直接在Kibana Dev Tools中执行。如果返回结果太多，建议添加时间范围过滤和size限制。大规模检索时使用scroll API避免超时。',
      },
      '/script-gen/trace': {
        type: 'danger',
        title: '攻击溯源是应急响应的关键环节',
        content: '溯源需要跨多个日志源关联分析。生成的脚本会自动关联：登录日志→进程创建→文件变更→网络连接，还原完整攻击链。溯源结果可直接用于事件报告。',
      },
      '/compliance/qa': {
        type: 'info',
        title: '合规问答基于最新法规标准',
        content: '知识库涵盖：等保2.0(GB/T 22239-2019)、网安法、数据安全法、行业规范。问题越具体，回答越精准。避免问"等保要求是什么"，应该问"三级等保对日志留存的具体要求"。',
      },
      '/compliance/baseline': {
        type: 'warning',
        title: '基线报告中的不合规项需要逐项整改',
        content: '报告按风险分级：红色=必须整改(等保测评直接不通过)、黄色=建议整改(有风险但不影响测评)、灰色=最佳实践。整改建议包含具体命令和配置示例。',
      },
      '/compliance/check': {
        type: 'warning',
        title: '自查结果不代表最终测评结论',
        content: '本工具提供技术层面的合规检查，但等保测评还包含管理层面(制度、人员、流程)。技术自查通过≠测评通过，建议结合管理制度一起整改。',
      },
      '/training/scenarios': {
        type: 'info',
        title: '选择场景前先评估自己的水平',
        content: '初级：适合刚接触日志分析的学员，主要考察基础字段提取能力。中级：需要理解攻击原理，能关联多条日志判断攻击阶段。高级：需要完整还原攻击链并给出溯源建议。',
      },
      '/training/submit': {
        type: 'warning',
        title: '答题时遵循标准分析流程',
        content: '评分标准：识别设备类型(10%)→提取关键字段(30%)→判断风险等级(20%)→给出处置建议(40%)。每步都有对应分值，漏掉任何一步都会扣分。',
      },
      '/training/report': {
        type: 'info',
        title: '报告用于跟踪技能成长',
        content: '重点关注：薄弱环节分布(哪些类型的日志分析得分低)、进步趋势(对比历次实训)、知识盲区(哪些知识点扣分多)。针对薄弱环节重点训练。',
      },
    },
  },

  // 测试样例数据
  sampleData: {
    logs: [
      '<22>Jan  5 12:34:56 web-server sshd[12345]: Failed password for invalid user admin from 192.168.1.100 port 22 ssh2',
      '2024-01-05T12:34:56Z "POST /api/login" 401 1234 "Mozilla/5.0" - -',
      '{"timestamp":"2024-01-05T12:34:56Z","action":"BLOCK","src_ip":"10.0.0.1","dst_ip":"192.168.1.50","rule_id":"WAF-001","severity":"HIGH"}',
    ],
    deviceTypes: ['firewall', 'waf', 'ids', 'ips', 'router', 'switch', 'server', 'web', 'db'],
    collectPlan: '# 防火墙日志采集方案\n## 设备信息\n- 类型: 防火墙\n- 型号: Huawei USG6000\n- 协议: Syslog (UDP 514)\n\n## 采集配置\n```\nsyslog-server 10.0.0.100 port 514\nlogging enable\nlogging source-interface GigabitEthernet0/0/0\nlogging facility local7\nlogging trap informational\n```',
  },
};

// 工具函数
var Utils = {
  // 风险等级映射
  getRiskLevel(level) {
    const map = { 'critical': 'P0', 'high': 'P1', 'medium': 'P2', 'low': 'P3', 'normal': 'normal' };
    return APP_CONFIG.riskLevels[map[level] || level] || APP_CONFIG.riskLevels.normal;
  },

  // 复制文本到剪贴板
  async copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      return true;
    }
  },

  // 格式化时间
  formatTime(date) {
    return new Date(date).toLocaleString('zh-CN', { hour12: false });
  },

  // 防抖
  debounce(fn, delay = 300) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), delay);
    };
  },
};

// Vue 全局混入：让所有组件模板都能访问 APP_CONFIG 和 Utils
var GlobalMixin = {
  data() {
    return { APP_CONFIG: APP_CONFIG, Utils: Utils };
  },
};
