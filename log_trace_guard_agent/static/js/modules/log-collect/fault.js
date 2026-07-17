/* ============================================
   模块二 · 故障诊断 — 诊断日志采集中常见故障
   ============================================ */

const LogCollectFault = {
  name: 'LogCollectFault',
  props: { mode: String },
  data() {
    return {
      symptom: '',
      deviceType: '',
      loading: false,
      result: null,
      deviceOptions: APP_CONFIG.sampleData.deviceTypes,
    };
  },
  methods: {
    fillExample() {
      this.symptom = '防火墙syslog日志采集不通，设备端已配置发送到10.0.0.100:514，但日志服务器未收到任何数据';
      this.deviceType = 'firewall';
    },
    async submit() {
      if (!this.symptom.trim()) {
        ElementPlus.ElMessageBox.alert('请描述故障现象', '提示', { type: 'warning' });
        return;
      }
      this.loading = true;
      this.result = null;
      try {
        const res = await Api.logCollect.fault({
          symptom: this.symptom,
          device_type: this.deviceType,
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
      <div style="padding:12px 16px;border-radius:6px;background:rgba(255,197,61,0.1);border:1px solid rgba(255,197,61,0.25);color:#B8860B;font-size:13px;margin-bottom:16px">
        <strong>故障诊断前先确认基础条件</strong><br>
        <span style="margin-top:4px;display:block">80%的采集故障是基础问题：①网络不通( ping目标IP ) ②端口未开放( telnet IP 514 ) ③防火墙拦截( 检查ACL )。先排除这三项再使用诊断工具。</span>
      </div>
      <div class="g-card">
        <div class="g-card-header">
          <div>
            <div class="g-card-title"><el-icon><Warning /></el-icon> 故障诊断</div>
            <div class="g-card-desc">描述日志采集中的故障现象，AI诊断原因并给出修复方案</div>
          </div>
          <el-button size="small" type="primary" plain @click="fillExample">填充示例</el-button>
        </div>
        <el-input v-model="symptom" type="textarea" :rows="4" placeholder="描述故障现象，如：防火墙日志采集不通..."
                  :disabled="loading" />
        <div class="g-input-guide">
          <el-icon><InfoFilled /></el-icon>
          <span>描述越详细诊断越准确，建议包含：设备类型、协议、症状表现</span>
        </div>
        <div style="margin-top:12px">
          <el-select v-model="deviceType" placeholder="设备类型（可选）" clearable size="small" style="width:200px">
            <el-option v-for="d in deviceOptions" :key="d" :label="d" :value="d" />
          </el-select>
        </div>
        <div class="g-actions" style="margin-top:12px">
          <el-button type="primary" @click="submit" :loading="loading">诊断</el-button>
        </div>
      </div>

      <div v-if="result" class="g-card slide">
        <div class="g-card-header">
          <div class="g-card-title"><el-icon><FirstAidKit /></el-icon> 诊断结果</div>
        </div>

        <div v-if="result.possible_causes" style="margin-bottom:16px">
          <div style="font-weight:600;margin-bottom:8px;font-size:13px">可能原因</div>
          <div v-for="(cause, i) in result.possible_causes" :key="i" class="g-alert g-alert--warning" style="margin-bottom:8px">
            <span>{{ i + 1 }}. {{ cause }}</span>
          </div>
        </div>

        <div v-if="result.fix_steps">
          <div style="font-weight:600;margin-bottom:8px;font-size:13px">修复步骤</div>
          <code-block :code="typeof result.fix_steps === 'string' ? result.fix_steps : JSON.stringify(result.fix_steps, null, 2)" lang="bash" />
        </div>

        <knowledge-panel title="故障排查知识">
          <p>日志采集中常见故障包括：网络不通、端口未监听、防火墙策略拦截、日志格式不匹配、磁盘空间不足等。建议按网络层→传输层→应用层的顺序逐层排查。</p>
        </knowledge-panel>
      </div>
    </div>
  `,
};
