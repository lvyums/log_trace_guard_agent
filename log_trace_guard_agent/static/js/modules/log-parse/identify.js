/* ============================================
   模块一 · 日志识别 — 输入日志自动识别设备类型与格式
   ============================================ */

const LogParseIdentify = {
  name: 'LogParseIdentify',
  props: { mode: String },
  data() {
    return {
      input: '',
      loading: false,
      result: null,
      showSample: false,
    };
  },
  methods: {
    fillSample() {
      this.input = APP_CONFIG.sampleData.logs.join('\n');
      this.showSample = false;
    },
    async submit() {
      if (!this.input.trim()) {
        ElementPlus.ElMessageBox.alert('请输入日志内容后再提交', '提示', { type: 'warning' });
        return;
      }
      if (this.input.length > 50000) {
        ElementPlus.ElMessageBox.alert('输入内容过长（最大50000字符），请分批提交', '输入超限', {
          type: 'error',
          distinguishCancelAndClose: true,
          confirmButtonText: '了解',
        });
        return;
      }
      this.loading = true;
      this.result = null;
      try {
        const res = await Api.logParse.identify({ log_line: this.input });
        if (res.success) {
          this.result = res.data;
        } else {
          ElementPlus.ElMessage.error(res.msg);
        }
      } catch (e) {
        ElementPlus.ElMessage.error('请求失败，请检查服务是否运行');
      } finally {
        this.loading = false;
      }
    },
    clear() {
      this.input = '';
      this.result = null;
    },
  },
  template: `
    <div class="g-stack">
      <alert-guide type="info" title="日志识别是分析的起点">
        粘贴一行完整原始日志，系统会自动识别：①设备类型(防火墙/WAF/IDS等) ②日志格式(syslog/JSON/CSV) ③关键字段。识别准确率取决于日志是否包含完整的PRI头和时间戳。
      </alert-guide>
      <!-- 上卡片：日志输入区 -->
      <div class="g-card">
        <div class="g-card-header">
          <div>
            <div class="g-card-title">
              <el-icon><Aim /></el-icon> 日志识别
            </div>
            <div class="g-card-desc">输入原始日志，AI自动识别设备类型、日志格式与关键字段</div>
          </div>
          <div class="g-actions">
            <el-tooltip content="粘贴单条或多条日志" placement="top">
              <el-button size="small" @click="showSample = !showSample">
                {{ showSample ? '收起' : '查看示例' }}
              </el-button>
            </el-tooltip>
            <el-button size="small" type="primary" plain @click="fillSample">
              填充测试日志
            </el-button>
          </div>
        </div>

        <!-- 示例展开 -->
        <div v-if="showSample" style="margin-bottom:12px">
          <div class="g-alert g-alert--info">
            <el-icon><InfoFilled /></el-icon>
            <span>支持格式：syslog、JSON、CSV、纯文本。单条或多条均可。</span>
          </div>
          <div class="g-code-block" style="font-size:12px">
            <div class="g-code-body" style="max-height:120px">
              <code v-text="APP_CONFIG.sampleData.logs.join('\\n')"></code>
            </div>
          </div>
        </div>

        <!-- 输入区 -->
        <el-input v-model="input" type="textarea" :rows="6" placeholder="在此粘贴日志内容..."
                  class="log-input-area" :disabled="loading"
                  @keyup.ctrl.enter="submit" @keyup.meta.enter="submit" />
        <div class="g-input-guide">
          <el-icon><InfoFilled /></el-icon>
          <span>支持粘贴单条或多条日志，Ctrl+Enter 快速提交。最大50000字符。</span>
        </div>

        <div class="g-actions" style="margin-top:12px">
          <el-button type="primary" @click="submit" :loading="loading" :disabled="!input.trim()">
            <el-icon style="margin-right:4px"><Search /></el-icon> 识别分析
          </el-button>
          <el-button @click="clear" :disabled="loading">清空</el-button>
        </div>
      </div>

      <!-- 下卡片：识别结果 -->
      <div v-if="result" class="g-card slide">
        <div class="g-card-header">
          <div class="g-card-title">
            <el-icon><Document /></el-icon> 识别结果
          </div>
        </div>

        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="设备类型">
            <risk-badge :level="'normal'" :label="result.device_type || '未知'" />
          </el-descriptions-item>
          <el-descriptions-item label="置信度">{{ result.confidence ? Math.round(result.confidence) + '%' : '-' }}</el-descriptions-item>
          <el-descriptions-item label="识别依据">{{ result.identify_reason || '规则匹配' }}</el-descriptions-item>
        </el-descriptions>

        <div v-if="result.fields && Object.keys(result.fields).length" style="margin-top:16px">
          <div style="font-weight:600;margin-bottom:8px;font-size:13px">关键字段</div>
          <div class="g-code-block">
            <div class="g-code-body" style="max-height:200px">
              <code v-text="JSON.stringify(result.fields, null, 2)"></code>
            </div>
          </div>
        </div>

        <result-guide :content="APP_CONFIG.guidance.resultGuides.logParse" />
      </div>

      <!-- 空状态 -->
      <div v-if="!result && !loading" class="g-card">
        <empty-guide title="等待日志输入" desc="在上方输入框粘贴日志内容，点击识别分析" action-text="填充测试日志" @action="fillSample" />
      </div>
    </div>
  `,
};
