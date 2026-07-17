/* ============================================
   模块三 · 脚本优化 — 优化现有正则或查询脚本性能
   ============================================ */

const ScriptGenOptimize = {
  name: 'ScriptGenOptimize',
  props: { mode: String },
  data() {
    return {
      script: '',
      scriptType: 'regex',
      loading: false,
      result: null,
      typeOptions: [
        { label: '正则表达式', value: 'regex' },
        { label: 'ES查询', value: 'es_query' },
        { label: 'Shell脚本', value: 'shell' },
      ],
    };
  },
  methods: {
    fillSample() {
      this.script = '.*Failed\\s+password\\s+for\\s+(invalid\\s+user\\s+)?(\\w+)\\s+from\\s+(\\d+\\.\\d+\\.\\d+\\.\\d+)\\s+port\\s+(\\d+).*';
      this.scriptType = 'regex';
    },
    async submit() {
      if (!this.script.trim()) {
        ElementPlus.ElMessageBox.alert('请输入待优化的脚本', '提示', { type: 'warning' });
        return;
      }
      this.loading = true;
      this.result = null;
      try {
        const res = await Api.scriptGen.optimize({
          script: this.script,
          script_type: this.scriptType,
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
      <div class="g-card">
        <div class="g-card-header">
          <div>
            <div class="g-card-title"><el-icon><SetUp /></el-icon> 脚本优化</div>
            <div class="g-card-desc">输入现有脚本，AI分析性能瓶颈并给出优化建议</div>
          </div>
          <el-button size="small" type="primary" plain @click="fillSample">填充示例</el-button>
        </div>
        <el-select v-model="scriptType" style="width:160px;margin-bottom:12px">
          <el-option v-for="t in typeOptions" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
        <el-input v-model="script" type="textarea" :rows="4" placeholder="粘贴待优化的脚本..." :disabled="loading" />
        <div class="g-actions" style="margin-top:12px">
          <el-button type="primary" @click="submit" :loading="loading">分析优化</el-button>
        </div>
      </div>

      <div v-if="result" class="g-card slide">
        <div class="g-card-title" style="margin-bottom:12px"><el-icon><TrendCharts /></el-icon> 优化结果</div>
        <div v-if="result.issues" style="margin-bottom:16px">
          <div style="font-weight:600;margin-bottom:8px;font-size:13px">发现的问题</div>
          <div v-for="(issue, i) in result.issues" :key="i" class="g-alert g-alert--warning" style="margin-bottom:8px">
            {{ issue }}
          </div>
        </div>
        <code-block :code="result.optimized || result.optimized_script" :lang="scriptType === 'regex' ? 'python' : 'bash'" title="优化后脚本" />
        <div v-if="result.explanation" style="margin-top:12px">
          <div style="font-weight:600;margin-bottom:8px;font-size:13px">优化说明</div>
          <div class="g-alert g-alert--success" style="margin-bottom:8px">
            {{ result.explanation }}
          </div>
        </div>
      </div>
    </div>
  `,
};
