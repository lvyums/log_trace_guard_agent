/* ============================================
   模块三 · 正则生成 — 根据日志样本自动生成正则表达式
   ============================================ */

const ScriptGenRegex = {
  name: 'ScriptGenRegex',
  props: { mode: String },
  data() {
    return {
      input: '',
      purpose: '',
      loading: false,
      result: null,
    };
  },
  methods: {
    fillSample() {
      this.input = '<22>Jan  5 12:34:56 web-server sshd[12345]: Failed password for invalid user admin from 192.168.1.100 port 22 ssh2';
      this.purpose = '提取用户名、源IP、失败原因';
    },
    async submit() {
      if (!this.input.trim()) {
        ElementPlus.ElMessageBox.alert('请输入日志样本', '提示', { type: 'warning' });
        return;
      }
      this.loading = true;
      this.result = null;
      try {
        const res = await Api.scriptGen.regex({
          scenario: this.purpose || this.input,
          log_sample: this.input,
          device_type: '',
        });
        if (res.success) {
          this.result = res.data;
        } else {
          ElementPlus.ElMessage.error(res.msg);
        }
      } catch (e) {
        ElementPlus.ElMessage.error('请求失败');
      } finally {
        this.loading = false;
      }
    },
  },
  template: `
    <div class="g-stack">
      <alert-guide type="info" title="正则表达式用于日志批量检索">
        生成的正则可用于：SIEM告警规则、ELK的grok解析、Python日志分析脚本、grep命令行检索。如果匹配速度慢，优先使用非捕获组(?:...)优化。
      </alert-guide>
      <div class="g-card">
        <div class="g-card-header">
          <div>
            <div class="g-card-title"><el-icon><MagicStick /></el-icon> 正则表达式生成</div>
            <div class="g-card-desc">粘贴日志样本，AI自动生成匹配正则表达式</div>
          </div>
          <el-button size="small" type="primary" plain @click="fillSample">填充测试日志</el-button>
        </div>
        <el-input v-model="input" type="textarea" :rows="3" placeholder="粘贴日志样本..." :disabled="loading" />
        <div class="g-input-guide">
          <el-icon><InfoFilled /></el-icon>
          <span>粘贴一条典型日志，AI将分析其结构并生成正则</span>
        </div>
        <el-input v-model="purpose" placeholder="提取目的（可选）：如提取用户名、IP地址" style="margin-top:12px" :disabled="loading" />
        <div class="g-actions" style="margin-top:12px">
          <el-button type="primary" @click="submit" :loading="loading">生成正则</el-button>
        </div>
      </div>

      <div v-if="result" class="g-card slide">
        <div class="g-card-title" style="margin-bottom:12px"><el-icon><Finished /></el-icon> 生成结果</div>
        <div v-if="result.regexes && result.regexes.length">
          <div v-for="(r, i) in result.regexes" :key="i" style="margin-bottom:16px">
            <div style="font-weight:600;font-size:13px;margin-bottom:6px">{{ r.name || '正则 ' + (i+1) }}</div>
            <code-block :code="r.pattern" lang="regex" :title="'正则表达式'" />
            <div v-if="r.description" style="font-size:12px;color:var(--text-secondary);margin-top:4px">{{ r.description }}</div>
          </div>
        </div>
        <div v-else>
          <code-block :code="result.pattern || '无匹配规则'" lang="regex" />
        </div>
        <div v-if="result.note" style="margin-top:12px">
          <div class="g-alert g-alert--info">
            <el-icon><InfoFilled /></el-icon>
            <span>{{ result.note }}</span>
          </div>
        </div>
        <knowledge-panel title="正则优化建议">
          <p>生成的正则已针对性能优化。建议在大量日志场景下使用预编译正则以提高匹配速度。</p>
        </knowledge-panel>
      </div>
    </div>
  `,
};
