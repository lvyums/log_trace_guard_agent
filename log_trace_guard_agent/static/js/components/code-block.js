/* ============================================
   代码块组件 — 语法高亮 + 一键复制
   Prism 未加载时自动降级为纯文本
   ============================================ */

const CodeBlock = {
  name: 'CodeBlock',
  props: {
    code: { type: String, default: '' },
    lang: { type: String, default: 'python' },
    title: String,
    maxHeight: { type: String, default: '400px' },
  },
  data() {
    return { copied: false };
  },
  computed: {
    highlighted() {
      if (!this.code) return '';
      const langMap = { python: 'python', json: 'json', bash: 'bash', shell: 'bash', yaml: 'yaml', regex: 'python' };
      const lang = langMap[this.lang] || 'plaintext';
      // Prism 降级处理：未加载时直接返回转义文本
      try {
        if (typeof Prism !== 'undefined' && Prism.languages && Prism.languages[lang]) {
          return Prism.highlight(this.code, Prism.languages[lang], lang);
        }
      } catch (e) {
        // 忽略 Prism 错误
      }
      return this.escapeHtml(this.code);
    },
    displayTitle() {
      return this.title || this.lang.toUpperCase();
    },
  },
  methods: {
    escapeHtml(str) {
      return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    },
    async copy() {
      await Utils.copyText(this.code);
      this.copied = true;
      setTimeout(() => (this.copied = false), 2000);
    },
  },
  template: `
    <div class="g-code-block" v-if="code">
      <div class="g-code-header">
        <span class="g-code-lang">{{ displayTitle }}</span>
        <el-button size="small" :type="copied ? 'success' : 'primary'" text @click="copy">
          <el-icon style="margin-right:4px"><component :is="copied ? 'Check' : 'CopyDocument'" /></el-icon>
          {{ copied ? '已复制' : '复制' }}
        </el-button>
      </div>
      <div class="g-code-body" :style="{ maxHeight }">
        <code v-html="highlighted" :class="'language-' + lang"></code>
      </div>
    </div>
  `,
};
