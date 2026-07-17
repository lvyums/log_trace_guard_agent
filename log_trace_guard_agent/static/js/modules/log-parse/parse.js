/* ============================================
   模块一 · 结构化解析 — 将原始日志解析为结构化字段
   ============================================ */

const LogParseParse = {
  name: 'LogParseParse',
  props: { mode: String },
  data() {
    return {
      input: '',
      loading: false,
      result: null,
      activeTab: 'fields',
    };
  },
  methods: {
    fillSample() {
      this.input = APP_CONFIG.sampleData.logs[0];
    },
    async submit() {
      if (!this.input.trim()) {
        ElementPlus.ElMessageBox.alert('请输入日志内容', '提示', { type: 'warning' });
        return;
      }
      this.loading = true;
      this.result = null;
      try {
        const res = await Api.logParse.parse({ log_line: this.input });
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
    copyJson() {
      Utils.copyText(JSON.stringify(this.result, null, 2));
      ElementPlus.ElMessage.success('已复制');
    },
  },
  template: `
    <div class="g-stack">
      <alert-guide type="info" title="结构化解析让日志可被检索">
        原始日志是给人看的文本，结构化日志是给机器检索的数据。解析后的字段可以直接写入Elasticsearch索引，用于后续的批量检索和告警规则。
      </alert-guide>
      <div class="g-card">
        <div class="g-card-header">
          <div>
            <div class="g-card-title"><el-icon><Document /></el-icon> 结构化解析</div>
            <div class="g-card-desc">将原始日志文本解析为标准化的结构化字段</div>
          </div>
          <el-button size="small" type="primary" plain @click="fillSample">填充测试日志</el-button>
        </div>
        <el-input v-model="input" type="textarea" :rows="4" placeholder="粘贴原始日志..."
                  :disabled="loading" @keyup.ctrl.enter="submit" />
        <div class="g-input-guide">
          <el-icon><InfoFilled /></el-icon>
          <span>支持 syslog / JSON / CSV 格式，解析结果将以结构化JSON展示</span>
        </div>
        <div class="g-actions" style="margin-top:12px">
          <el-button type="primary" @click="submit" :loading="loading">解析</el-button>
        </div>
      </div>

      <div v-if="result" class="g-card slide">
        <div class="g-card-header">
          <div class="g-card-title"><el-icon><DataBoard /></el-icon> 解析结果</div>
          <el-button size="small" @click="copyJson">复制JSON</el-button>
        </div>
        <el-tabs v-model="activeTab">
          <el-tab-pane label="字段列表" name="fields">
            <el-table :data="fieldRows" border size="small" class="g-table" max-height="400">
              <el-table-column prop="name" label="字段名" width="180">
                <template #default="{ row }">
                  <span class="field-name">{{ row.name }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="value" label="值">
                <template #default="{ row }">
                  <span class="field-value">{{ row.value }}</span>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="原始JSON" name="json">
            <code-block :code="JSON.stringify(result, null, 2)" lang="json" />
          </el-tab-pane>
        </el-tabs>
        <result-guide content="以上为日志结构化解析结果。每个字段代表日志中提取的一个关键信息，可用于后续风险研判、合规审计等分析。" />
      </div>
    </div>
  `,
  computed: {
    fieldRows() {
      if (!this.result) return [];
      const obj = this.result.parsed_fields || this.result.fields || this.result;
      if (typeof obj !== 'object') return [];
      const excludeFields = ['missing_fields', 'raw_log', 'fallback_note', 'device_type'];
      return Object.entries(obj)
        .filter(([name]) => !excludeFields.includes(name) && !name.endsWith('_missing'))
        .map(([name, value]) => ({
          name,
          value: typeof value === 'object' ? JSON.stringify(value) : String(value),
        }));
    },
  },
};
