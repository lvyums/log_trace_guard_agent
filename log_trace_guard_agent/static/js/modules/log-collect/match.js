/* ============================================
   模块二 · 设备匹配 — 识别安全设备型号与采集协议
   ============================================ */

const LogCollectMatch = {
  name: 'LogCollectMatch',
  props: { mode: String },
  data() {
    return {
      deviceType: '',
      deviceModel: '',
      loading: false,
      result: null,
      deviceOptions: APP_CONFIG.sampleData.deviceTypes,
    };
  },
  methods: {
    fillExample() {
      this.deviceType = 'firewall';
      this.deviceModel = 'Huawei USG6000';
    },
    async submit() {
      if (!this.deviceType) {
        ElementPlus.ElMessageBox.alert('请选择设备类型', '提示', { type: 'warning' });
        return;
      }
      this.loading = true;
      this.result = null;
      try {
        const res = await Api.logCollect.match({
          device_type: this.deviceType,
          device_model: this.deviceModel,
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
      <alert-guide type="info" title="设备匹配决定采集配置">
        选错设备类型会导致生成的配置无法使用。如果你不确定设备类型，先用「日志识别」分析一条该设备的日志，系统会自动判断。
      </alert-guide>
      <div class="g-card">
        <div class="g-card-header">
          <div>
            <div class="g-card-title"><el-icon><Monitor /></el-icon> 设备匹配</div>
            <div class="g-card-desc">输入设备信息，自动匹配采集协议与配置方案</div>
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
            <el-input v-model="deviceModel" placeholder="如: Huawei USG6000, Cisco ASA 5500" />
          </el-form-item>
        </el-form>

        <div class="g-actions">
          <el-button type="primary" @click="submit" :loading="loading">匹配</el-button>
        </div>
      </div>

      <div v-if="result" class="g-card slide">
        <div class="g-card-header">
          <div class="g-card-title"><el-icon><Connection /></el-icon> 匹配结果</div>
        </div>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="设备类型">{{ result.device_info?.device_type || result.plan?.device_type || '-' }}</el-descriptions-item>
          <el-descriptions-item label="采集协议">{{ result.plan?.protocol || '-' }}</el-descriptions-item>
          <el-descriptions-item label="匹配置信度">{{ result.match_confidence ? Math.round(result.match_confidence) + '%' : '-' }}</el-descriptions-item>
          <el-descriptions-item label="匹配来源">{{ result.match_source || '工厂匹配' }}</el-descriptions-item>
        </el-descriptions>

        <div v-if="result.plan?.config_template" style="margin-top:16px">
          <div style="font-weight:600;margin-bottom:8px;font-size:13px">配置模板</div>
          <code-block :code="typeof result.plan.config_template === 'string' ? result.plan.config_template : JSON.stringify(result.plan.config_template, null, 2)" lang="bash" />
        </div>

        <result-guide content="设备匹配完成。请根据采集协议配置对应的日志采集方案。点击左侧菜单「采集方案」可生成完整配置。" />
      </div>
    </div>
  `,
};
