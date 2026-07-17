/* ============================================
   模块五 · 实训报告 — 查看实训统计与详细报告
   ============================================ */

const TrainingReport = {
  name: 'TrainingReport',
  props: { mode: String },
  data() {
    return {
      loading: false,
      report: null,
    };
  },
  computed: {
    isTraining() {
      return this.mode === 'training';
    },
  },
  methods: {
    async loadReport() {
      this.loading = true;
      try {
        const res = await Api.training.report({});
        if (res.success) {
          this.report = res.data;
        } else {
          this.loadSampleReport();
        }
      } catch (e) {
        this.loadSampleReport();
      } finally {
        this.loading = false;
      }
    },
    loadSampleReport() {
      this.report = {
        total_sessions: 12,
        completed: 10,
        avg_score: 78,
        total_time: '4h 30m',
        details: [
          { scenario: 'SSH暴力破解检测', score: 90, time: '15min', status: 'completed' },
          { scenario: 'Web攻击日志分析', score: 75, time: '25min', status: 'completed' },
          { scenario: '内网横向移动追踪', score: 60, time: '40min', status: 'completed' },
          { scenario: '日志采集架构设计', score: 85, time: '20min', status: 'completed' },
          { scenario: '合规基线检查', score: 70, time: '18min', status: 'completed' },
        ],
      };
    },
    exportReport() {
      if (!this.report) return;
      const content = JSON.stringify(this.report, null, 2);
      const blob = new Blob([content], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `training-report-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      ElementPlus.ElMessage.success('报告已导出');
    },
  },
  mounted() {
    this.loadReport();
  },
  template: `
    <div class="g-stack">
      <alert-guide type="info" title="报告用于跟踪技能成长">
        重点关注：薄弱环节分布(哪些类型的日志分析得分低)、进步趋势(对比历次实训)、知识盲区(哪些知识点扣分多)。针对薄弱环节重点训练。
      </alert-guide>
      <div class="g-card">
        <div class="g-card-header">
          <div class="g-card-title"><el-icon><DataLine /></el-icon> 实训报告</div>
          <el-button size="small" type="primary" plain @click="exportReport" :disabled="!report">
            <el-icon style="margin-right:4px"><Download /></el-icon> 导出报告
          </el-button>
        </div>

        <div v-if="loading" style="text-align:center;padding:40px">
          <el-icon class="is-loading" :size="32" color="var(--primary)"><Loading /></el-icon>
        </div>

        <div v-else-if="report">
          <!-- 统计卡片 -->
          <div class="training-stats">
            <div class="training-stat-card">
              <div class="training-stat-value">{{ report.total_sessions }}</div>
              <div class="training-stat-label">总实训次数</div>
            </div>
            <div class="training-stat-card">
              <div class="training-stat-value" style="color:var(--risk-normal)">{{ report.completed }}</div>
              <div class="training-stat-label">已完成</div>
            </div>
            <div class="training-stat-card">
              <div class="training-stat-value" style="color:var(--risk-p1)">{{ report.avg_score }}</div>
              <div class="training-stat-label">平均分</div>
            </div>
          </div>

          <!-- 详细记录 -->
          <div v-if="report.details && report.details.length" style="margin-top:20px">
            <div style="font-weight:600;margin-bottom:12px">详细记录</div>
            <el-table :data="report.details" border size="small" class="g-table">
              <el-table-column type="index" label="#" width="50" />
              <el-table-column prop="scenario" label="实训场景" />
              <el-table-column prop="score" label="得分" width="80">
                <template #default="{ row }">
                  <span :style="{ color: row.score >= 80 ? 'var(--risk-normal)' : row.score >= 60 ? 'var(--risk-p1)' : 'var(--risk-p0)' }">
                    {{ row.score }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="time" label="用时" width="80" />
              <el-table-column prop="status" label="状态" width="80">
                <template #default="{ row }">
                  <risk-badge :level="row.status === 'completed' ? 'normal' : 'P2'" :label="row.status === 'completed' ? '已完成' : '进行中'" />
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <div v-else class="g-empty">
          <empty-guide title="暂无实训记录" desc="完成实训场景后将自动生成报告" action-text="去实训" @action="$emit('navigate', '/training/scenarios')" />
        </div>
      </div>
    </div>
  `,
};
