/* ============================================
   全局新手引导组件 — 分步遮罩指引
   ============================================ */

const GlobalTour = {
  name: 'GlobalTour',
  props: {
    mode: { type: String, default: 'ops' },
  },
  emits: ['close'],
  data() {
    return {
      currentStep: 0,
      steps: APP_CONFIG.guidance.global.steps,
    };
  },
  computed: {
    step() {
      return this.steps[this.currentStep];
    },
    isLast() {
      return this.currentStep === this.steps.length - 1;
    },
  },
  methods: {
    next() {
      if (this.isLast) {
        this.$emit('close');
      } else {
        this.currentStep++;
      }
    },
    prev() {
      if (this.currentStep > 0) this.currentStep--;
    },
    skip() {
      this.$emit('close');
    },
  },
  template: `
    <div class="g-tour-overlay" @click.self="skip">
      <div class="g-tour-dialog" style="max-width:560px">
        <div class="g-tour-header">
          <div class="g-tour-title">安全日志分析工作流</div>
          <el-button :icon="'Close'" text @click="skip" />
        </div>
        <div class="g-tour-body">
          <div class="g-tour-step">
            <div class="g-tour-step-num">{{ currentStep + 1 }}</div>
            <div class="g-tour-step-content">
              <div class="g-tour-step-title">{{ step.title }}</div>
              <div class="g-tour-step-desc" style="line-height:1.7">{{ step.desc }}</div>
            </div>
          </div>
        </div>
        <div class="g-tour-footer">
          <div class="g-tour-progress">
            <div v-for="(s, i) in steps" :key="i"
                 class="g-tour-dot" :class="{ active: i === currentStep }" />
          </div>
          <div class="g-tour-actions">
            <el-button size="small" @click="skip">跳过</el-button>
            <el-button size="small" @click="prev" :disabled="currentStep === 0">上一步</el-button>
            <el-button size="small" type="primary" @click="next">
              {{ isLast ? '完成' : '下一步' }}
            </el-button>
          </div>
        </div>
      </div>
    </div>
  `,
};

/* ============================================
   输入框引导提示组件
   ============================================ */
const InputGuide = {
  name: 'InputGuide',
  props: {
    text: String,
    example: String,
  },
  template: `
    <div class="g-input-guide">
      <el-icon><InfoFilled /></el-icon>
      <span>{{ text }}<span v-if="example" style="color:var(--text-placeholder);margin-left:4px">{{ example }}</span></span>
    </div>
  `,
};

/* ============================================
   悬浮提示包装组件
   ============================================ */
const TipWrapper = {
  name: 'TipWrapper',
  props: {
    tip: Object,
  },
  template: `
    <el-tooltip placement="top" :show-after="300" :hide-after="100">
      <template #content>
        <div>
          <div style="font-weight:600;margin-bottom:4px">{{ tip.label }}</div>
          <div>{{ tip.desc }}</div>
          <code v-if="tip.example" style="display:block;margin-top:6px;padding:4px 6px;background:rgba(255,255,255,0.1);border-radius:4px;font-size:11px">{{ tip.example }}</code>
        </div>
      </template>
      <slot />
    </el-tooltip>
  `,
};

/* ============================================
   操作指引条组件
   ============================================ */
const AlertGuide = {
  name: 'AlertGuide',
  props: {
    type: { type: String, default: 'info' },
    title: String,
    closable: { type: Boolean, default: true },
  },
  emits: ['close'],
  data() {
    return { visible: true };
  },
  computed: {
    icon() {
      const map = { info: 'InfoFilled', warning: 'WarningFilled', danger: 'CircleCloseFilled', success: 'CircleCheckFilled' };
      return map[this.type] || 'InfoFilled';
    },
  },
  template: `
    <div v-if="visible" class="g-alert" :class="'g-alert--' + type">
      <el-icon><component :is="icon" /></el-icon>
      <div style="flex:1">
        <div v-if="title" style="font-weight:600;margin-bottom:2px">{{ title }}</div>
        <slot />
      </div>
      <el-icon v-if="closable" style="cursor:pointer;flex-shrink:0" @click="visible = false; $emit('close')"><Close /></el-icon>
    </div>
  `,
};

/* ============================================
   知识点折叠面板组件
   ============================================ */
const KnowledgePanel = {
  name: 'KnowledgePanel',
  props: {
    title: { type: String, default: '知识点详解' },
  },
  data() {
    return { open: false };
  },
  template: `
    <div class="g-knowledge-panel">
      <div class="g-knowledge-header" :class="{ 'is-open': open }" @click="open = !open">
        <el-icon><DArrowRight /></el-icon>
        <span>{{ title }}</span>
      </div>
      <div v-show="open" class="g-knowledge-body">
        <slot />
      </div>
    </div>
  `,
};

/* ============================================
   空状态引导组件
   ============================================ */
const EmptyGuide = {
  name: 'EmptyGuide',
  props: {
    title: { type: String, default: '暂无数据' },
    desc: { type: String, default: '请进行相关操作' },
    actionText: String,
    icon: { type: String, default: 'Inbox' },
  },
  emits: ['action'],
  template: `
    <div class="g-empty">
      <el-icon class="g-empty-icon"><component :is="icon" /></el-icon>
      <div class="g-empty-title">{{ title }}</div>
      <div class="g-empty-desc">{{ desc }}</div>
      <el-button v-if="actionText" type="primary" @click="$emit('action')">
        {{ actionText }}
      </el-button>
    </div>
  `,
};

/* ============================================
   结果解读面板组件
   ============================================ */
const ResultGuide = {
  name: 'ResultGuide',
  props: {
    content: String,
  },
  data() {
    return { open: true };
  },
  template: `
    <div class="g-result-guide" v-if="content">
      <div class="g-result-guide-header" @click="open = !open">
        <el-icon><InfoFilled /></el-icon>
        <span style="font-weight:500;font-size:13px">结果解读</span>
        <el-icon style="margin-left:auto;transition:transform 0.2s" :style="{ transform: open ? 'rotate(90deg)' : '' }"><ArrowRight /></el-icon>
      </div>
      <div v-show="open" class="g-result-guide-body">
        <div style="font-size:13px;color:var(--text-secondary);line-height:1.8">{{ content }}</div>
      </div>
    </div>
  `,
};

/* ============================================
   批量确认弹窗组件
   ============================================ */
const ConfirmBatch = {
  name: 'ConfirmBatch',
  props: {
    visible: Boolean,
    count: { type: Number, default: 0 },
    desc: { type: String, default: '批量操作将处理以下数据' },
  },
  emits: ['update:visible', 'confirm'],
  template: `
    <el-dialog :model-value="visible" @update:model-value="$emit('update:visible', $event)" width="420px" :show-close="true" center>
      <div class="g-confirm-batch">
        <div class="confirm-icon">⚠️</div>
        <div class="confirm-count">{{ count }} 条数据</div>
        <div class="confirm-desc">{{ desc }}<br>此操作不可撤销，请确认后执行。</div>
      </div>
      <template #footer>
        <el-button @click="$emit('update:visible', false)">取消</el-button>
        <el-button type="primary" @click="$emit('confirm'); $emit('update:visible', false)">确认执行</el-button>
      </template>
    </el-dialog>
  `,
};
