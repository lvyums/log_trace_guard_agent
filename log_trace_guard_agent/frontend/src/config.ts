import type {
  RiskLevelDef, RiskLevelKey, ModuleDef, GuideStep,
  ResultGuides, ModuleTip, EmptyState, TooltipDef,
} from './types'

export interface AppConfig {
  apiBase: string
  riskLevels: Record<RiskLevelKey, RiskLevelDef>
  modules: ModuleDef[]
  guidance: {
    global: { title: string; steps: GuideStep[] }
    tooltips: Record<string, TooltipDef>
    emptyStates: Record<string, EmptyState>
    resultGuides: ResultGuides
    moduleTips: Record<string, ModuleTip>
  }
  sampleData: {
    logs: string[]
    deviceTypes: string[]
    collectPlan: string
  }
}

export const APP_CONFIG: AppConfig = {
  apiBase: '',

  riskLevels: {
    P0: { label: '极高危', color: '#F53F3F', bg: 'rgba(245,63,63,0.1)', icon: 'CircleCloseFilled' },
    P1: { label: '高危', color: '#FF7D00', bg: 'rgba(255,125,0,0.1)', icon: 'WarningFilled' },
    P2: { label: '中危', color: '#FFC53D', bg: 'rgba(255,197,61,0.1)', icon: 'InfoFilled' },
    P3: { label: '低危', color: '#86909C', bg: 'rgba(134,144,156,0.1)', icon: 'InfoFilled' },
    normal: { label: '正常', color: '#00B42A', bg: 'rgba(0,180,42,0.1)', icon: 'CircleCheckFilled' },
  },

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
      key: 'log-correlate', label: '日志联合审查', icon: 'Connection',
      desc: '安全威胁狩猎、攻击链检测、多源日志关联分析',
      children: [
        { path: '/log-correlate/analyze', label: '关联分析', icon: 'Search', tip: '输入多源日志，检测安全攻击链（关键词+LLM双引擎）' },
        { path: '/log-correlate/patterns', label: '攻击链模式', icon: 'List', tip: '查看所有可检测的攻击链模式列表' },
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
      desc: '实训场景、实训报告',
      children: [
        { path: '/training/scenarios', label: '实训场景', icon: 'Reading', tip: '查看并选择攻防实训场景' },
        { path: '/training/report', label: '实训报告', icon: 'DataLine', tip: '查看实训统计与详细报告' },
      ],
    },
  ],

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
        example: '正确: <22>Jan 5 12:34:56 sshd[12345]: Failed password for root from 192.168.1.100 port 22\n错误: sshd: Failed password (缺少pri头和时间戳会导致识别失败)',
      },
      fileUpload: {
        label: '批量上传建议',
        desc: '单文件最大10MB。如果日志量很大，建议按设备类型分文件上传。',
        example: '推荐: fw_syslog.txt / waf_events.json / nginx_access.log',
      },
    },
    emptyStates: {
      logParse: {
        title: '安全分析从一行日志开始',
        desc: '粘贴任何安全设备的原始日志，系统会自动识别设备类型、解析字段、评估风险等级。',
        action: '加载真实攻击样例',
        hint: '典型场景：收到IDS告警后，粘贴原始日志确认是否为误报。',
      },
      correlate: {
        title: '安全威胁狩猎 — 发现隐蔽攻击链',
        desc: '输入多源日志（每行一条），系统自动检测安全攻击链。内置 16 种攻击链模型，覆盖 SSH 爆破提权、SQL 注入、横向移动、数据窃取、C2 通信、勒索软件等场景。支持中英文日志，关键词匹配不足时自动降级 LLM 智能分析。',
        action: '加载攻击链样例',
        hint: '例如：SSH 暴力破解失败 → 登录成功 → sudo提权 → 敏感文件访问，就是一个完整的攻击链。',
      },
      collectPlan: {
        title: '日志采集是安全运营的基石',
        desc: '没有日志就没有检测能力。选择设备类型和企业规模，系统会生成符合等保要求的标准化采集方案。',
        action: '查看防火墙采集方案',
        hint: '等保2.0要求：日志留存≥180天，传输需加密。',
      },
      training: {
        title: '实战化攻防技能训练',
        desc: '每个场景基于真实安全事件设计，包含：攻击日志样本、分析任务、评分标准和知识点讲解。',
        action: '开始SSH暴力破解检测',
        hint: '实训模式会记录每步操作并评分。',
      },
      script: {
        title: '自动化安全分析脚本',
        desc: '手动分析效率低。输入你的分析需求，自动生成正则表达式、ES查询语句、溯源脚本等。',
        action: '生成SSH暴力破解正则',
        hint: '所有脚本都经过性能优化，可直接用于生产环境。',
      },
    },
    resultGuides: {
      logParse: '识别结果决定了后续分析的准确性。如果设备类型识别错误，请手动指定设备类型后重新分析。',
      collectPlan: '配置代码可直接粘贴到设备命令行执行。如果采集不通，先检查防火墙是否放行了Syslog端口(UDP 514)。',
      compliance: '基线报告中的不合规项按风险排序：红色=必须立即整改、黄色=建议整改、灰色=最佳实践。',
      training: '分析日志时的标准流程：1.先识别设备和日志格式 2.提取攻击者IP、时间、手法 3.判断风险等级 4.给出处置建议。',
    },
    moduleTips: {
      '/log-parse/identify': { type: 'info', title: '日志识别是分析的起点', content: '粘贴一行完整原始日志，系统会自动识别设备类型、日志格式、关键字段。' },
      '/log-parse/parse': { type: 'info', title: '结构化解析让日志可被检索', content: '原始日志是给人看的文本，结构化日志是给机器检索的数据。' },
      '/log-parse/assess': { type: 'warning', title: '风险研判需要结合上下文', content: '单独一条日志的风险判断有局限性。建议结合多维度输入。' },
      '/log-parse/batch': { type: 'info', title: '批量分析前建议按设备分文件', content: '混合不同设备的日志会降低识别准确率。' },
      '/log-collect/match': { type: 'info', title: '设备匹配决定采集配置', content: '选错设备类型会导致生成的配置无法使用。' },
      '/log-collect/plan': { type: 'warning', title: '采集方案必须满足等保要求', content: '等保2.0要求：日志留存≥180天、传输加密。' },
      '/log-collect/fault': { type: 'warning', title: '故障诊断前先确认基础条件', content: '80%的采集故障是基础问题：网络不通、端口未开放、防火墙拦截。' },
      '/log-collect/arch': { type: 'info', title: '架构设计要考虑扩展性', content: '预留30%的采集容量，选择支持水平扩展的架构。' },
      '/script-gen/regex': { type: 'info', title: '正则表达式用于日志批量检索', content: '生成的正则可用于SIEM告警规则、ELK的grok解析。' },
      '/script-gen/es-query': { type: 'info', title: 'ES查询用于安全事件检索', content: '生成的DSL可直接在Kibana Dev Tools中执行。' },
      '/script-gen/trace': { type: 'danger', title: '攻击溯源是应急响应的关键环节', content: '溯源需要跨多个日志源关联分析。' },
      '/compliance/qa': { type: 'info', title: '合规问答基于最新法规标准', content: '知识库涵盖等保2.0、网安法、数据安全法。' },
      '/compliance/baseline': { type: 'warning', title: '基线报告需要逐项整改', content: '报告按风险分级：红色=必须整改、黄色=建议整改、灰色=最佳实践。' },
      '/training/scenarios': { type: 'info', title: '选择场景前先评估水平', content: '初级：基础字段提取。中级：攻击原理理解。高级：完整溯源。' },
      '/training/submit': { type: 'warning', title: '答题时遵循标准流程', content: '评分标准：识别设备类型(10%)→提取关键字段(30%)→判断风险等级(20%)→处置建议(40%)。' },
      '/training/report': { type: 'info', title: '报告用于跟踪技能成长', content: '重点关注薄弱环节、进步趋势、知识盲区。' },
      '/log-correlate/analyze': { type: 'info', title: '关联分析需要多源日志输入', content: '粘贴至少2-3条不同来源的日志，系统会自动构建时间线和检测攻击链。支持SSH、Web、防火墙等多类型混输。' },
      '/log-correlate/patterns': { type: 'info', title: '攻击链模式库', content: '内置23条常见攻击链检测规则，涵盖数据库、网络、认证、容器、API等场景。' },
    },
  },

  sampleData: {
    logs: [
      '<22>Jan  5 12:34:56 web-server sshd[12345]: Failed password for invalid user admin from 192.168.1.100 port 22 ssh2',
      '2024-01-05T12:34:56Z "POST /api/login" 401 1234 "Mozilla/5.0" - -',
      '{"timestamp":"2024-01-05T12:34:56Z","action":"BLOCK","src_ip":"10.0.0.1","dst_ip":"192.168.1.50","rule_id":"WAF-001","severity":"HIGH"}',
    ],
    deviceTypes: ['firewall', 'waf', 'ids', 'ips', 'router', 'switch', 'server', 'web', 'db'],
    collectPlan: '# 防火墙日志采集方案\n## 设备信息\n- 类型: 防火墙\n- 协议: Syslog (UDP 514)\n\n## 采集配置\n```\nsyslog-server 10.0.0.100 port 514\n```',
  },
}

/** 风险等级映射工具 */
export function getRiskLevel(level: string): RiskLevelDef {
  const map: Record<string, RiskLevelKey> = {
    critical: 'P0', high: 'P1', medium: 'P2', low: 'P3',
    'P0_高危': 'P0', 'P1_中危': 'P1', 'P2_低危': 'P2', 'P3_噪音': 'P3',
  }
  const key = map[level] || level as RiskLevelKey
  return APP_CONFIG.riskLevels[key] || APP_CONFIG.riskLevels.normal
}
