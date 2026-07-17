/* ============================================
   模块四 · 基线生成 — 根据资产信息生成合规基线报告
   ============================================ */

const ComplianceBaseline = {
  name: 'ComplianceBaseline',
  props: { mode: String },
  data() {
    return {
      form: {
        org_name: '',
        asset_type: '',
        os_type: '',
        service_list: '',
        standard: '等保2.0三级',
      },
      loading: false,
      result: null,
      standardOptions: ['等保2.0二级', '等保2.0三级', '等保2.0四级', '网安法', '数据安全法'],
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
        org_name: 'XX科技有限公司',
        asset_type: 'Web应用服务器',
        os_type: 'CentOS 7.9',
        service_list: 'Nginx, MySQL, Redis',
        standard: '等保2.0三级',
      };
    },
    async submit() {
      if (!this.form.org_name || !this.form.asset_type) {
        ElementPlus.ElMessageBox.alert('请填写组织名称和资产类型', '提示', { type: 'warning' });
        return;
      }
      this.loading = true;
      this.result = null;
      try {
        const res = await Api.compliance.baseline(this.form);
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
          <el-form-item label="组织名称">
            <tip-wrapper :tip="{ label: '组织名称', desc: '填写需要进行合规检查的组织或单位名称' }">
              <el-input v-model="form.org_name" placeholder="如：XX科技有限公司" />
            </tip-wrapper>
          </el-form-item>
          <el-form-item label="资产类型">
            <tip-wrapper :tip="{ label: '资产类型', desc: '选择需要检查的资产类型', example: 'Web服务器、数据库、防火墙等' }">
              <el-input v-model="form.asset_type" placeholder="如：Web应用服务器" />
            </tip-wrapper>
          </el-form-item>
          <el-form-item label="操作系统">
            <el-input v-model="form.os_type" placeholder="如：CentOS 7.9" />
          </el-form-item>
          <el-form-item label="部署服务">
            <el-input v-model="form.service_list" placeholder="如：Nginx, MySQL, Redis" />
          </el-form-item>
          <el-form-item label="合规标准">
            <el-select v-model="form.standard" style="width:100%">
              <el-option v-for="s in standardOptions" :key="s" :label="s" :value="s" />
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
