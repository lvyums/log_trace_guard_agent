/* ============================================
   模块三 · ES查询生成 — 生成Elasticsearch查询语句
   ============================================ */

const ScriptGenEsquery = {
  name: 'ScriptGenEsquery',
  props: { mode: String },
  data() {
    return {
      description: '',
      indexPattern: '',
      loading: false,
      result: null,
    };
  },
  methods: {
    fillSample() {
      this.description = '查询最近1小时内来源IP为192.168.1.x网段的SSH登录失败事件，按时间倒序，返回前50条';
      this.indexPattern = 'logstash-ssh-*';
    },
    async submit() {
      if (!this.description.trim()) {
        ElementPlus.ElMessageBox.alert('请描述查询需求', '提示', { type: 'warning' });
        return;
      }
      this.loading = true;
      this.result = null;
      try {
        const res = await Api.scriptGen.esQuery({
          description: this.description,
          index_pattern: this.indexPattern,
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
      <alert-guide type="info" title="ES查询用于安全事件检索">
        生成的DSL可直接在Kibana Dev Tools中执行。如果返回结果太多，建议添加时间范围过滤和size限制。大规模检索时使用scroll API避免超时。
      </alert-guide>
      <div class="g-card">
        <div class="g-card-header">
          <div>
            <div class="g-card-title"><el-icon><Search /></el-icon> ES 查询生成</div>
            <div class="g-card-desc">用自然语言描述查询需求，自动生成 Elasticsearch 查询语句</div>
          </div>
          <el-button size="small" type="primary" plain @click="fillSample">填充示例</el-button>
        </div>
        <el-input v-model="description" type="textarea" :rows="3" placeholder="用自然语言描述你要查询的内容..." :disabled="loading" />
        <div class="g-input-guide">
          <el-icon><InfoFilled /></el-icon>
          <span>描述越详细生成越精准，可包含：时间范围、字段条件、排序方式</span>
        </div>
        <el-input v-model="indexPattern" placeholder="索引模式（可选）：如 logstash-*" style="margin-top:12px" :disabled="loading" />
        <div class="g-actions" style="margin-top:12px">
          <el-button type="primary" @click="submit" :loading="loading">生成查询</el-button>
        </div>
      </div>

      <div v-if="result" class="g-card slide">
        <div class="g-card-title" style="margin-bottom:12px"><el-icon><Monitor /></el-icon> ES 查询语句</div>
        <code-block :code="result.query || result.dsl" lang="json" title="Elasticsearch DSL" />
        <result-guide content="以上为生成的ES查询语句，可直接复制到Kibana Dev Tools或API中执行。如需调整请修改描述后重新生成。" />
      </div>
    </div>
  `,
};
