/* ============================================
   模块三 · 平台选型 — 日志平台对比选型推荐
   ============================================ */

const ScriptGenPlatform = {
  name: 'ScriptGenPlatform',
  props: { mode: String },
  data() {
    return {
      requirements: '',
      scale: 'medium',
      budget: '',
      loading: false,
      result: null,
      scaleOptions: [
        { label: '小型', value: 'small' },
        { label: '中型', value: 'medium' },
        { label: '大型', value: 'large' },
      ],
    };
  },
  methods: {
    fillSample() {
      this.requirements = '需要支持syslog采集、全文检索、告警规则、可视化报表，日均日志量约5GB';
      this.scale = 'medium';
      this.budget = '50万以内';
    },
    async submit() {
      if (!this.requirements.trim()) {
        ElementPlus.ElMessageBox.alert('请描述需求', '提示', { type: 'warning' });
        return;
      }
      this.loading = true;
      this.result = null;
      try {
        const res = await Api.scriptGen.platform({
          requirements: this.requirements,
          scale: this.scale,
          budget: this.budget,
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
            <div class="g-card-title"><el-icon><DataAnalysis /></el-icon> 平台选型</div>
            <div class="g-card-desc">描述需求，AI对比主流日志平台并推荐最佳选型</div>
          </div>
          <el-button size="small" type="primary" plain @click="fillSample">填充示例</el-button>
        </div>
        <el-input v-model="requirements" type="textarea" :rows="3" placeholder="描述日志平台需求..." :disabled="loading" />
        <div style="margin-top:12px;display:flex;gap:12px">
          <el-select v-model="scale" placeholder="企业规模" style="width:160px">
            <el-option v-for="s in scaleOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
          <el-input v-model="budget" placeholder="预算范围（可选）" style="flex:1" :disabled="loading" />
        </div>
        <div class="g-actions" style="margin-top:12px">
          <el-button type="primary" @click="submit" :loading="loading">对比选型</el-button>
        </div>
      </div>

      <div v-if="result" class="g-card slide">
        <div class="g-card-title" style="margin-bottom:12px"><el-icon><TrendCharts /></el-icon> 选型对比</div>
        <el-table v-if="result.platforms" :data="result.platforms" border size="small">
          <el-table-column prop="name" label="平台" width="120" />
          <el-table-column prop="type" label="类型" width="80" />
          <el-table-column prop="pros" label="优势" />
          <el-table-column prop="cons" label="劣势" />
          <el-table-column prop="score" label="推荐度" width="80">
            <template #default="{ row }">
              <el-rate v-model="row.score" disabled :max="5" />
            </template>
          </el-table-column>
        </el-table>
        <div v-if="result.recommendation" class="g-alert g-alert--success" style="margin-top:12px">
          <el-icon><CircleCheckFilled /></el-icon>
          <div><strong>推荐：</strong>{{ result.recommendation }}</div>
        </div>
        <knowledge-panel title="选型建议">
          <p>{{ result.advice || '选型需综合考虑团队技术栈、运维能力、日志量级和预算。建议先小规模试用再全面部署。' }}</p>
        </knowledge-panel>
      </div>
    </div>
  `,
};
