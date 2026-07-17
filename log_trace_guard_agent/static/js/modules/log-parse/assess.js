/* ============================================
   模块一 · 风险研判 — 对日志内容进行安全风险评估
   ============================================ */

const LogParseAssess = {
  name: 'LogParseAssess',
  props: { mode: String },
  data() {
    return {
      input: '',
      deviceType: '',
      loading: false,
      result: null,
      deviceOptions: APP_CONFIG.sampleData.deviceTypes,
    };
  },
  methods: {
    fillSample() {
      this.input = APP_CONFIG.sampleData.logs[0];
      this.deviceType = 'ssh';
    },
    async submit() {
      if (!this.input.trim()) {
        ElementPlus.ElMessageBox.alert('请输入日志内容', '提示', { type: 'warning' });
        return;
      }
      this.loading = true;
      this.result = null;
      try {
        const res = await Api.logParse.assess({
          log_text: this.input,
          device_type: this.deviceType || undefined,
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
      <alert-guide type="warning" title="风险研判需要结合上下文">
        单独一条日志的风险判断有局限性。建议：先在「日志识别」中确认设备类型，再在「结构化解析」中提取关键字段，最后在这里做综合研判。多维度输入能显著提高准确率。
      </alert-guide>
      <div class="g-card">
        <div class="g-card-header">
          <div>
            <div class="g-card-title"><el-icon><Warning /></el-icon> 风险研判</div>
            <div class="g-card-desc">对日志内容进行安全风险评估，标注风险等级与处置建议</div>
          </div>
          <el-button size="small" type="primary" plain @click="fillSample">填充测试日志</el-button>
        </div>
        <el-input v-model="input" type="textarea" :rows="4" placeholder="粘贴待研判的日志..."
                  :disabled="loading" @keyup.ctrl.enter="submit" />
        <div class="g-input-guide">
          <el-icon><InfoFilled /></el-icon>
          <span>可选指定设备类型以提高研判精度</span>
        </div>
        <div style="margin-top:12px">
          <el-select v-model="deviceType" placeholder="设备类型（可选）" clearable size="small" style="width:200px">
            <el-option v-for="d in deviceOptions" :key="d" :label="d" :value="d" />
          </el-select>
        </div>
        <div class="g-actions" style="margin-top:12px">
          <el-button type="primary" @click="submit" :loading="loading">风险研判</el-button>
        </div>
      </div>

      <div v-if="result" class="slide">
        <risk-card
          :title="result.risk_title || '风险研判结果'"
          :level="result.risk_level || 'normal'"
          :confidence="result.confidence"
          :source="result.match_source"
          :details="result.details"
          :disposition="result.disposition"
        />
        <result-guide :content="result.disposition || APP_CONFIG.guidance.resultGuides.logParse" />
      </div>
    </div>
  `,
};
