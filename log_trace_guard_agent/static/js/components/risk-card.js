/* ============================================
   风险卡片组件 — 统一风险等级视觉标识
   ============================================ */

const RiskBadge = {
  name: 'RiskBadge',
  props: {
    level: { type: String, default: 'normal' },
    label: String,
  },
  computed: {
    risk() {
      return Utils.getRiskLevel(this.level);
    },
    displayLabel() {
      return this.label || this.risk.label;
    },
  },
  template: `
    <span class="risk-badge" :class="'risk-badge--' + (level === 'critical' ? 'p0' : level === 'high' ? 'p1' : level === 'medium' ? 'p2' : level === 'low' ? 'p3' : level === 'normal' ? 'normal' : level)"
          :style="{ background: risk.bg, color: risk.color }">
      {{ displayLabel }}
    </span>
  `,
};

/* ============================================
   风险研判结果卡片
   ============================================ */
const RiskCard = {
  name: 'RiskCard',
  props: {
    title: String,
    level: String,
    confidence: Number,
    source: String,
    details: Object,
    disposition: String,
  },
  computed: {
    risk() {
      return Utils.getRiskLevel(this.level);
    },
    confidencePercent() {
      return this.confidence ? Math.round(this.confidence * 100) : null;
    },
  },
  template: `
    <div class="g-card" style="margin-bottom:12px">
      <div v-if="confidencePercent && confidencePercent < 70" class="g-alert g-alert--warning" style="margin-bottom:12px">
        <el-icon><WarningFilled /></el-icon>
        <span>低置信度识别结果（{{ confidencePercent }}%），建议人工复核确认</span>
      </div>
      <div v-if="level === 'critical' || level === 'high'" class="g-alert g-alert--danger" style="margin-bottom:12px">
        <el-icon><CircleCloseFilled /></el-icon>
        <div>
          <div style="font-weight:600">高危风险 — 请立即处置</div>
          <div style="margin-top:4px;font-size:12px">{{ disposition || '建议立即隔离受影响资产，排查攻击来源，启动应急响应流程。' }}</div>
        </div>
      </div>
      <div class="g-card-header">
        <div>
          <div class="g-card-title">
            <risk-badge :level="level" />
            <span>{{ title }}</span>
          </div>
          <div v-if="source" class="g-card-desc">匹配来源: {{ source }}</div>
        </div>
        <div v-if="confidencePercent" style="text-align:right">
          <div style="font-size:12px;color:var(--text-tertiary)">置信度</div>
          <div style="font-size:18px;font-weight:600;color:var(--primary)">{{ confidencePercent }}%</div>
        </div>
      </div>
      <div v-if="details && Object.keys(details).length" style="font-size:13px;line-height:1.8">
        <div v-for="(val, key) in details" :key="key" style="display:flex;gap:8px;padding:4px 0;border-bottom:1px solid var(--border-light)">
          <span style="color:var(--text-tertiary);min-width:80px;flex-shrink:0">{{ key }}</span>
          <span style="color:var(--text-primary);word-break:break-all">{{ val }}</span>
        </div>
      </div>
      <slot />
    </div>
  `,
};
