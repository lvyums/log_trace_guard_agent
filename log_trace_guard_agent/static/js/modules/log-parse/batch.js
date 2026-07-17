/* ============================================
   模块一 · 批量解析 — 批量上传日志文件进行解析分析
   ============================================ */

const LogParseBatch = {
  name: 'LogParseBatch',
  props: { mode: String },
  data() {
    return {
      input: '',
      doAssess: true,
      loading: false,
      result: null,
    };
  },
  computed: {
    logLines() {
      if (!this.input.trim()) return [];
      return this.input.split('\n').map(l => l.trim()).filter(l => l.length > 0);
    },
    totalCount() {
      return this.logLines.length;
    },
  },
  methods: {
    fillSample() {
      this.input = APP_CONFIG.sampleData.logs.join('\n');
    },
    async submit() {
      if (!this.totalCount) {
        ElementPlus.ElMessageBox.alert('请输入日志内容', '提示', { type: 'warning' });
        return;
      }
      if (this.totalCount > 100) {
        ElementPlus.ElMessageBox.alert('单次最多批量解析100条日志，请分批处理', '提示', { type: 'warning' });
        return;
      }
      this.loading = true;
      this.result = null;
      try {
        const res = await Api.logParse.batch({
          logs: this.logLines,
          assess: this.doAssess,
        });
        if (res.success) {
          this.result = res.data;
          ElementPlus.ElMessage.success(`成功解析 ${res.data?.success_count || 0} 条日志`);
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
      <alert-guide type="info" title="批量分析前建议按设备分文件">
        混合不同设备的日志会降低识别准确率。建议按设备类型分批输入，每批处理同类型日志。系统会自动统计：风险分布、异常IP TOP10、攻击类型分布。
      </alert-guide>
      <div class="g-card">
        <div class="g-card-header">
          <div>
            <div class="g-card-title"><el-icon><Grid /></el-icon> 批量解析</div>
            <div class="g-card-desc">输入多条日志（每行一条），批量进行解析分析</div>
          </div>
          <div class="g-actions">
            <el-button size="small" type="primary" plain @click="fillSample">
              填充测试日志
            </el-button>
          </div>
        </div>

        <el-input v-model="input" type="textarea" :rows="6" placeholder="在此粘贴日志内容，每行一条日志..."
                  class="log-input-area" :disabled="loading" />
        <div class="g-input-guide">
          <el-icon><InfoFilled /></el-icon>
          <span>每行一条日志，最多100条。支持 syslog / JSON / CSV 格式。</span>
        </div>

        <div style="margin-top:12px">
          <el-checkbox v-model="doAssess">同时进行风险研判</el-checkbox>
        </div>

        <div class="g-actions" style="margin-top:12px">
          <el-button type="primary" @click="submit" :loading="loading" :disabled="!totalCount">
            <el-icon style="margin-right:4px"><Upload /></el-icon> 批量解析 ({{ totalCount }} 条日志)
          </el-button>
        </div>
      </div>

      <div v-if="result" class="g-card slide">
        <div class="g-card-header">
          <div class="g-card-title"><el-icon><DataBoard /></el-icon> 批量解析结果</div>
        </div>
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="总条数">{{ result.total || 0 }}</el-descriptions-item>
          <el-descriptions-item label="成功解析">{{ result.success_count || 0 }}</el-descriptions-item>
          <el-descriptions-item label="失败条数">{{ result.fail_count || 0 }}</el-descriptions-item>
        </el-descriptions>

        <div v-if="result.items && result.items.length" style="margin-top:16px">
          <el-table :data="result.items" border size="small" class="g-table" max-height="400">
            <el-table-column type="index" label="#" width="50" />
            <el-table-column label="日志摘要" width="200" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.log_line || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="解析状态" width="100">
              <template #default="{ row }">
                <risk-badge :level="row.error ? 'P0' : 'normal'" :label="row.error ? '失败' : '成功'" />
              </template>
            </el-table-column>
            <el-table-column prop="parse_result" label="设备类型" width="120">
              <template #default="{ row }">
                {{ row.parse_result?.device_type || '-' }}
              </template>
            </el-table-column>
          </el-table>
        </div>

        <result-guide content="批量解析已完成。可在上方表格中查看每条日志的解析结果。高风险项建议优先人工复核。" />
      </div>
    </div>
  `,
};
