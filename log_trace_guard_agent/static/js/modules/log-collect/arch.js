/* ============================================
   模块二 · 架构推荐 — 根据企业规模推荐日志采集架构
   ============================================ */

const LogCollectArch = {
  name: 'LogCollectArch',
  props: { mode: String },
  data() {
    return {
      scale: 'small',
      deviceCount: 10,
      deviceTypes: [],
      loading: false,
      result: null,
      scaleOptions: [
        { label: '小型（<100人）', value: 'small' },
        { label: '中型（100-1000人）', value: 'medium' },
        { label: '大型（>1000人）', value: 'large' },
      ],
      deviceOptions: ['firewall', 'waf', 'ids', 'ips', 'router', 'switch', 'server', 'web', 'db'],
    };
  },
  methods: {
    fillExample() {
      this.scale = 'medium';
      this.deviceCount = 50;
      this.deviceTypes = ['firewall', 'waf', 'ids', 'server'];
    },
    async submit() {
      this.loading = true;
      this.result = null;
      try {
        const res = await Api.logCollect.arch({
          scale: this.scale,
          device_count: this.deviceCount,
          device_types: this.deviceTypes,
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
      <alert-guide type="info" title="架构设计要考虑扩展性">
        当前方案基于当前规模，但安全设备会持续增加。建议：预留30%的采集容量，选择支持水平扩展的架构(如Kafka分层)，避免未来重构。
      </alert-guide>
      <div class="g-card">
        <div class="g-card-header">
          <div>
            <div class="g-card-title"><el-icon><Share /></el-icon> 架构推荐</div>
            <div class="g-card-desc">根据企业规模和设备情况，推荐最优日志采集架构方案</div>
          </div>
          <el-button size="small" type="primary" plain @click="fillExample">填充示例</el-button>
        </div>

        <el-form label-position="top" size="default">
          <el-form-item label="企业规模">
            <el-radio-group v-model="scale">
              <el-radio-button v-for="s in scaleOptions" :key="s.value" :value="s.value">{{ s.label }}</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="安全设备数量">
            <el-input-number v-model="deviceCount" :min="1" :max="10000" />
          </el-form-item>
          <el-form-item label="设备类型">
            <el-select v-model="deviceTypes" multiple placeholder="选择涉及的设备类型" style="width:100%">
              <el-option v-for="d in deviceOptions" :key="d" :label="d" :value="d" />
            </el-select>
          </el-form-item>
        </el-form>

        <div class="g-actions">
          <el-button type="primary" @click="submit" :loading="loading">推荐架构</el-button>
        </div>
      </div>

      <div v-if="result" class="g-card slide">
        <div class="g-card-header">
          <div class="g-card-title"><el-icon><Share /></el-icon> 架构方案</div>
        </div>

        <div v-if="result.arch_name" style="font-weight:600;font-size:15px;margin-bottom:12px">{{ result.arch_name }}</div>
        <div v-if="result.description" style="color:var(--text-secondary);font-size:13px;margin-bottom:16px">{{ result.description }}</div>

        <div v-if="result.topology" class="topology-container" style="margin-bottom:16px">
          <pre style="font-family:var(--font-mono);font-size:12px;text-align:left;color:var(--text-secondary)">{{ result.topology }}</pre>
        </div>

        <div v-if="result.components && result.components.length" style="margin-bottom:16px">
          <div style="font-weight:600;margin-bottom:8px;font-size:13px">组件清单</div>
          <el-table :data="result.components" border size="small">
            <el-table-column prop="name" label="组件" width="150" />
            <el-table-column prop="role" label="职责" />
            <el-table-column prop="recommendation" label="推荐选型" width="180" />
          </el-table>
        </div>

        <result-guide content="以上为推荐的日志采集架构方案。拓扑图展示了数据流向，组件清单列出了各层所需设备。可根据实际环境调整。" />
      </div>
    </div>
  `,
};
