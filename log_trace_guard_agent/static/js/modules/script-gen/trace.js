/* ============================================
   模块三 · 攻击溯源 — 生成攻击链溯源检索脚本
   ============================================ */

const ScriptGenTrace = {
  name: 'ScriptGenTrace',
  props: { mode: String },
  data() {
    return {
      attackType: '',
      targetIp: '',
      timeRange: '',
      loading: false,
      result: null,
    };
  },
  methods: {
    fillSample() {
      this.attackType = 'SSH暴力破解';
      this.targetIp = '192.168.1.50';
      this.timeRange = '2024-01-05 10:00 ~ 2024-01-05 14:00';
    },
    async submit() {
      if (!this.attackType.trim()) {
        ElementPlus.ElMessageBox.alert('请描述攻击类型', '提示', { type: 'warning' });
        return;
      }
      this.loading = true;
      this.result = null;
      try {
        const res = await Api.scriptGen.trace({
          attack_type: this.attackType,
          target_ip: this.targetIp,
          time_range: this.timeRange,
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
      <alert-guide type="danger" title="攻击溯源是应急响应的关键环节">
        溯源需要跨多个日志源关联分析。生成的脚本会自动关联：登录日志→进程创建→文件变更→网络连接，还原完整攻击链。溯源结果可直接用于事件报告。
      </alert-guide>
      <div class="g-card">
        <div class="g-card-header">
          <div>
            <div class="g-card-title"><el-icon><Connection /></el-icon> 攻击溯源</div>
            <div class="g-card-desc">输入攻击线索，生成攻击链溯源检索脚本</div>
          </div>
          <el-button size="small" type="primary" plain @click="fillSample">填充示例</el-button>
        </div>
        <el-form label-position="top" size="default">
          <el-form-item label="攻击类型">
            <el-input v-model="attackType" placeholder="如：SSH暴力破解、SQL注入、Webshell上传" :disabled="loading" />
          </el-form-item>
          <el-form-item label="目标IP（可选）">
            <el-input v-model="targetIp" placeholder="被攻击的目标IP" :disabled="loading" />
          </el-form-item>
          <el-form-item label="时间范围（可选）">
            <el-input v-model="timeRange" placeholder="如：2024-01-05 10:00 ~ 2024-01-05 14:00" :disabled="loading" />
          </el-form-item>
        </el-form>
        <div class="g-actions">
          <el-button type="primary" @click="submit" :loading="loading">生成溯源脚本</el-button>
        </div>
      </div>

      <div v-if="result" class="g-card slide">
        <div class="g-card-title" style="margin-bottom:12px"><el-icon><Tickets /></el-icon> 溯源脚本</div>
        <code-block :code="result.script || result.query" :lang="result.lang || 'bash'" />
        <div v-if="result.trace_chain" style="margin-top:16px">
          <div style="font-weight:600;margin-bottom:8px;font-size:13px">攻击链路</div>
          <div v-for="(step, i) in result.trace_chain" :key="i" class="g-alert g-alert--info" style="margin-bottom:8px">
            <span>Step {{ i + 1 }}: {{ step }}</span>
          </div>
        </div>
        <knowledge-panel title="溯源方法论">
          <p>攻击溯源遵循「时间线重建 → 行为关联 → 攻击链还原」的方法论。从告警时间点出发，向前回溯登录行为、文件变更、进程创建等事件，串联形成完整攻击链。</p>
        </knowledge-panel>
      </div>
    </div>
  `,
};
