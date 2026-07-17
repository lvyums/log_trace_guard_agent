/* ============================================
   模块四 · 基线生成 — 根据资产信息生成合规基线报告
   ============================================ */

const ComplianceBaseline = {
  name: 'ComplianceBaseline',
  props: { mode: String },
  data() {
    return {
      form: {
        asset_count: 10,
        business_type: '互联网',
        device_types: 'web,db,firewall',
        monitor_scenarios: '入侵检测,异常登录,数据泄露',
        industry: '互联网',
      },
      loading: false,
      result: null,
      industryOptions: ['互联网', '金融', '政府', '教育', '医疗', '能源', '制造业', '其他'],
    };
  },
  methods: {
    renderMarkdown(text) {
      if (!text) return '';
      return text
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/`(.+?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
    },
    fillExample() {
      this.form = {
        asset_count: 50,
        business_type: '互联网金融',
        device_types: 'web,db,firewall,waf,server',
        monitor_scenarios: '入侵检测,异常登录,数据泄露,恶意软件',
        industry: '金融',
      };
    },
    async submit() {
      if (!this.form.asset_count || !this.form.business_type) {
        ElementPlus.ElMessageBox.alert('请填写资产数量和组织类型', '提示', { type: 'warning' });
        return;
      }
      this.loading = true;
      this.result = null;
      try {
        const res = await Api.compliance.baseline({
          asset_count: this.form.asset_count,
          business_type: this.form.business_type,
          device_types: this.form.device_types.split(',').map(s => s.trim()).filter(s => s),
          monitor_scenarios: this.form.monitor_scenarios.split(',').map(s => s.trim()).filter(s => s),
          industry: this.form.industry,
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
    <div class="g-split g-split--left-fixed">
      <alert-guide type="warning" title="基线报告中的不合规项需要逐项整改">
        报告按风险分级：红色=必须整改(等保测评直接不通过)、黄色=建议整改(有风险但不影响测评)、灰色=最佳实践。整改建议包含具体命令和配置示例。
      </alert-guide>
      <!-- 左侧表单 -->
      <div class="g-card" style="align-self:start">
        <div class="g-card-header">
          <div>
            <div class="g-card-title"><el-icon><Document /></el-icon> 基线生成</div>
            <div class="g-card-desc">填写资产信息，生成合规基线检查报告</div>
          </div>
          <el-button size="small" type="primary" plain @click="fillExample">填充示例</el-button>
        </div>
        <el-form :model="form" label-position="top" size="default" class="compliance-form">
          <el-form-item label="资产数量">
            <el-input-number v-model="form.asset_count" :min="1" :max="100000" style="width:100%" />
          </el-form-item>
          <el-form-item label="业务类型">
            <el-input v-model="form.business_type" placeholder="如：互联网、金融、政府" />
          </el-form-item>
          <el-form-item label="设备类型（逗号分隔）">
            <el-input v-model="form.device_types" placeholder="如：web,db,firewall,waf" />
          </el-form-item>
          <el-form-item label="监控场景（逗号分隔）">
            <el-input v-model="form.monitor_scenarios" placeholder="如：入侵检测,异常登录,数据泄露" />
          </el-form-item>
          <el-form-item label="所属行业">
            <el-select v-model="form.industry" style="width:100%">
              <el-option v-for="ind in industryOptions" :key="ind" :label="ind" :value="ind" />
            </el-select>
          </el-form-item>
        </el-form>
        <el-button type="primary" @click="submit" :loading="loading" style="width:100%">生成基线报告</el-button>
      </div>

      <!-- 右侧预览 -->
      <div class="g-card" style="align-self:start">
        <div class="g-card-title" style="margin-bottom:12px"><el-icon><View /></el-icon> 基线报告预览</div>
        <div v-if="result" class="compliance-preview" v-html="renderMarkdown(result.report || result.baseline || JSON.stringify(result, null, 2))"></div>
        <div v-else class="g-empty" style="min-height:300px">
          <el-icon class="g-empty-icon"><Document /></el-icon>
          <div style="font-size:14px;color:var(--text-secondary)">填写左侧表单生成报告</div>
          <div style="font-size:12px;color:var(--text-tertiary)">报告将实时渲染在此区域</div>
        </div>
        <result-guide v-if="result" :content="APP_CONFIG.guidance.resultGuides.compliance" />
      </div>
    </div>
  `,
};
