/* ============================================
   模块二 · 采集方案 — 生成标准化日志采集配置方案
   ============================================ */

const LogCollectPlan = {
  name: 'LogCollectPlan',
  props: { mode: String },
  data() {
    return {
      deviceType: '',
      deviceModel: '',
      scale: 'small',
      loading: false,
      result: null,
      deviceOptions: APP_CONFIG.sampleData.deviceTypes,
      scaleOptions: [
        { label: '小型（<100人）', value: 'small' },
        { label: '中型（100-1000人）', value: 'medium' },
        { label: '大型（>1000人）', value: 'large' },
      ],
    };
  },
  methods: {
    fillExample() {
      this.deviceType = 'firewall';
      this.deviceModel = 'Huawei USG6000';
      this.scale = 'medium';
    },
    async submit() {
      if (!this.deviceType) {
        ElementPlus.ElMessageBox.alert('请选择设备类型', '提示', { type: 'warning' });
        return;
      }
      this.loading = true;
      this.result = null;
      try {
        const res = await Api.logCollect.plan({
          device_type: this.deviceType,
          device_model: this.deviceModel,
          scale: this.scale,
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
      <alert-guide type="warning" title="采集方案必须满足等保要求">
        等保2.0明确要求：日志留存≥180天、传输加密、覆盖所有安全设备。生成方案后请逐项核对是否满足合规要求，不满足的需要手动补充。
      </alert-guide>
      <div class="g-card">
        <div class="g-card-header">
          <div>
            <div class="g-card-title"><el-icon><Document /></el-icon> 采集方案生成</div>
            <div class="g-card-desc">根据设备类型和企业规模，生成标准化的日志采集配置方案</div>
          </div>
          <el-button size="small" type="primary" plain @click="fillExample">填充示例</el-button>
        </div>

        <el-form label-position="top" size="default">
          <el-form-item label="设备类型">
            <tip-wrapper :tip="APP_CONFIG.guidance.tooltips.deviceType">
              <el-select v-model="deviceType" placeholder="选择设备类型" style="width:100%">
                <el-option v-for="d in deviceOptions" :key="d" :label="d" :value="d" />
              </el-select>
            </tip-wrapper>
          </el-form-item>
          <el-form-item label="设备型号（可选）">
            <el-input v-model="deviceModel" placeholder="具体型号可提高方案精准度" />
          </el-form-item>
          <el-form-item label="企业规模">
            <tip-wrapper :tip="APP_CONFIG.guidance.tooltips.企业规模">
              <el-radio-group v-model="scale">
                <el-radio-button v-for="s in scaleOptions" :key="s.value" :value="s.value">{{ s.label }}</el-radio-button>
              </el-radio-group>
            </tip-wrapper>
          </el-form-item>
        </el-form>

        <div class="g-actions">
          <el-button type="primary" @click="submit" :loading="loading">生成方案</el-button>
        </div>
      </div>

      <div v-if="result" class="g-card slide">
        <div class="g-card-header">
          <div class="g-card-title"><el-icon><Document /></el-icon> 采集方案</div>
        </div>

        <div v-if="result.plan_title" style="font-weight:600;font-size:15px;margin-bottom:12px">{{ result.plan_title }}</div>

        <div v-if="result.steps && result.steps.length" style="margin-bottom:16px">
          <div style="font-weight:600;margin-bottom:8px;font-size:13px">实施步骤</div>
          <div v-for="(step, i) in result.steps" :key="i" class="g-steps" style="padding:0;gap:12px">
            <div class="g-step-num" style="width:24px;height:24px;font-size:12px">{{ i + 1 }}</div>
            <div style="flex:1;font-size:13px;color:var(--text-secondary)">{{ step }}</div>
          </div>
        </div>

        <div v-if="result.config">
          <div style="font-weight:600;margin-bottom:8px;font-size:13px">配置代码</div>
          <code-block :code="typeof result.config === 'string' ? result.config : JSON.stringify(result.config, null, 2)"
                      :lang="result.config_format || 'bash'" />
        </div>

        <result-guide :content="APP_CONFIG.guidance.resultGuides.collectPlan" />
      </div>
    </div>
  `,
};
