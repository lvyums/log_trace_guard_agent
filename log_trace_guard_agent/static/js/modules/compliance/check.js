/* ============================================
   模块四 · 合规自查 — 检查现有配置是否满足合规要求
   ============================================ */

const ComplianceCheck = {
  name: 'ComplianceCheck',
  props: { mode: String },
  data() {
    return {
      config: '',
      checkType: 'log_retention',
      loading: false,
      result: null,
      checkOptions: [
        { label: '日志留存', value: 'log_retention' },
        { label: '访问控制', value: 'access_control' },
        { label: '安全审计', value: 'security_audit' },
        { label: '数据安全', value: 'data_security' },
        { label: '综合检查', value: 'comprehensive' },
      ],
    };
  },
  methods: {
    fillSample() {
      this.config = 'syslog日志保留30天，无加密传输，管理员账户使用默认密码，未开启双因素认证';
      this.checkType = 'comprehensive';
    },
    async submit() {
      if (!this.config.trim()) {
        ElementPlus.ElMessageBox.alert('请输入配置信息', '提示', { type: 'warning' });
        return;
      }
      this.loading = true;
      this.result = null;
      try {
        const res = await Api.compliance.check({
          config: this.config,
          check_type: this.checkType,
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
      <alert-guide type="warning" title="自查结果不代表最终测评结论">
        本工具提供技术层面的合规检查，但等保测评还包含管理层面(制度、人员、流程)。技术自查通过≠测评通过，建议结合管理制度一起整改。
      </alert-guide>
      <div class="g-card">
        <div class="g-card-header">
          <div>
            <div class="g-card-title"><el-icon><CircleCheck /></el-icon> 合规自查</div>
            <div class="g-card-desc">输入当前配置信息，检查是否满足合规要求</div>
          </div>
          <el-button size="small" type="primary" plain @click="fillSample">填充示例</el-button>
        </div>
        <el-select v-model="checkType" style="width:160px;margin-bottom:12px">
          <el-option v-for="c in checkOptions" :key="c.value" :label="c.label" :value="c.value" />
        </el-select>
        <el-input v-model="config" type="textarea" :rows="4" placeholder="描述当前安全配置..." :disabled="loading" />
        <div class="g-input-guide">
          <el-icon><InfoFilled /></el-icon>
          <span>描述越详细检查越全面，可包含：日志留存、加密、认证、访问控制等</span>
        </div>
        <div class="g-actions" style="margin-top:12px">
          <el-button type="primary" @click="submit" :loading="loading">开始检查</el-button>
        </div>
      </div>

      <div v-if="result" class="g-card slide">
        <div class="g-card-title" style="margin-bottom:12px"><el-icon><DataLine /></el-icon> 检查结果</div>

        <el-descriptions :column="3" border size="small" style="margin-bottom:16px">
          <el-descriptions-item label="总检查项">{{ result.total || 0 }}</el-descriptions-item>
          <el-descriptions-item label="合规项">
            <span style="color:var(--risk-normal)">{{ result.pass || 0 }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="不合规项">
            <span style="color:var(--risk-p0)">{{ result.fail || 0 }}</span>
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="result.items" style="margin-bottom:16px">
          <div v-for="(item, i) in result.items" :key="i" class="g-card" style="margin-bottom:8px;padding:12px">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
              <risk-badge :level="item.compliant ? 'normal' : 'P0'" :label="item.compliant ? '合规' : '不合规'" />
              <span style="font-weight:500;font-size:13px">{{ item.item_name }}</span>
            </div>
            <div v-if="!item.compliant && item.remediation" class="g-alert g-alert--warning" style="margin:0">
              <span>整改建议：{{ item.remediation }}</span>
            </div>
          </div>
        </div>

        <result-guide :content="APP_CONFIG.guidance.resultGuides.compliance" />
      </div>
    </div>
  `,
};
