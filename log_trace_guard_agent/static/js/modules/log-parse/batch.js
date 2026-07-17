/* ============================================
   模块一 · 批量解析 — 批量上传日志文件进行解析分析
   ============================================ */

const LogParseBatch = {
  name: 'LogParseBatch',
  props: { mode: String },
  data() {
    return {
      fileList: [],
      loading: false,
      result: null,
      showConfirm: false,
    };
  },
  computed: {
    fileCount() {
      return this.fileList.length;
    },
  },
  methods: {
    beforeUpload(file) {
      const maxSize = 10 * 1024 * 1024;
      if (file.size > maxSize) {
        ElementPlus.ElMessage.warning(`${file.name} 超过10MB限制`);
        return false;
      }
      const allowed = ['.txt', '.log', '.csv'];
      const ext = '.' + file.name.split('.').pop().toLowerCase();
      if (!allowed.includes(ext)) {
        ElementPlus.ElMessage.warning(`不支持 ${ext} 格式，请上传 ${allowed.join(', ')}`);
        return false;
      }
      return true;
    },
    handleUploadChange(file, list) {
      this.fileList = list;
    },
    submit() {
      if (!this.fileList.length) {
        ElementPlus.ElMessageBox.alert('请先上传日志文件', '提示', { type: 'warning' });
        return;
      }
      this.showConfirm = true;
    },
    async confirmBatch() {
      this.showConfirm = false;
      this.loading = true;
      this.result = null;
      try {
        const formData = new FormData();
        this.fileList.forEach(f => {
          if (f.raw) formData.append('files', f.raw);
        });
        const res = await Api.logParse.batch(formData);
        if (res.success) {
          this.result = res.data;
          ElementPlus.ElMessage.success(`成功解析 ${res.data?.parsed_count || 0} 条日志`);
        } else {
          ElementPlus.ElMessage.error(res.msg);
        }
      } catch (e) {
        ElementPlus.ElMessage.error('上传失败');
      } finally {
        this.loading = false;
      }
    },
  },
  template: `
    <div class="g-stack">
      <alert-guide type="info" title="批量分析前建议按设备分文件">
        混合不同设备的日志会降低识别准确率。建议按设备类型分文件上传，每批处理同类型日志。系统会自动统计：风险分布、异常IP TOP10、攻击类型分布。
      </alert-guide>
      <div class="g-card">
        <div class="g-card-header">
          <div>
            <div class="g-card-title"><el-icon><Grid /></el-icon> 批量解析</div>
            <div class="g-card-desc">上传多个日志文件，批量进行解析分析</div>
          </div>
        </div>

        <el-upload
          drag multiple :auto-upload="false"
          :before-upload="beforeUpload"
          :on-change="handleUploadChange"
          :file-list="fileList"
          accept=".txt,.log,.csv"
          :disabled="loading"
        >
          <el-icon style="font-size:40px;color:var(--text-tertiary);margin-bottom:8px"><UploadFilled /></el-icon>
          <div style="color:var(--text-secondary);font-size:13px">拖拽文件到此处，或 <em style="color:var(--primary)">点击上传</em></div>
          <div style="color:var(--text-tertiary);font-size:12px;margin-top:4px">支持 .txt .log .csv，单文件最大 10MB</div>
        </el-upload>

        <div class="g-actions" style="margin-top:16px">
          <el-button type="primary" @click="submit" :loading="loading" :disabled="!fileList.length">
            <el-icon style="margin-right:4px"><Upload /></el-icon> 批量解析 ({{ fileCount }} 个文件)
          </el-button>
        </div>
      </div>

      <div v-if="result" class="g-card slide">
        <div class="g-card-header">
          <div class="g-card-title"><el-icon><DataBoard /></el-icon> 批量解析结果</div>
        </div>
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="总条数">{{ result.total_count || 0 }}</el-descriptions-item>
          <el-descriptions-item label="成功解析">{{ result.parsed_count || 0 }}</el-descriptions-item>
          <el-descriptions-item label="失败条数">{{ result.error_count || 0 }}</el-descriptions-item>
        </el-descriptions>

        <div v-if="result.items && result.items.length" style="margin-top:16px">
          <el-table :data="result.items" border size="small" class="g-table" max-height="400">
            <el-table-column type="index" label="#" width="50" />
            <el-table-column prop="device_type" label="设备类型" width="120" />
            <el-table-column prop="risk_level" label="风险等级" width="100">
              <template #default="{ row }">
                <risk-badge :level="row.risk_level" />
              </template>
            </el-table-column>
            <el-table-column prop="summary" label="摘要" show-overflow-tooltip />
          </el-table>
        </div>

        <result-guide content="批量解析已完成。可在上方表格中查看每条日志的解析摘要，点击行可展开详情。高风险项建议优先人工复核。" />
      </div>
    </div>

    <confirm-batch v-model:visible="showConfirm" :count="fileCount" desc="将批量解析上传的日志文件" @confirm="confirmBatch" />
  `,
};
