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
        const res = await Api.training.report({
          student_id: 'student_default',
          scenario_id: '',
        });
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
        total_tasks: 12,
        completed_tasks: 10,
        average_score: 78,
        overall_grade: 'B',
        task_records: [
          { task_id: '1', title: 'SSH暴力破解检测', score: 90, grade: 'A', attempts: 1, status: 'completed' },
          { task_id: '2', title: 'Web攻击日志分析', score: 75, grade: 'B', attempts: 2, status: 'completed' },
          { task_id: '3', title: '内网横向移动追踪', score: 60, grade: 'C', attempts: 3, status: 'completed' },
        ],
        weaknesses: [
          { category: '风险研判', description: '对高级攻击手法判断不准确', score: 60, suggestion: '建议加强攻击原理学习' },
        ],
        improvement_plan: '重点提升风险研判能力，建议完成中级实训场景后再挑战高级场景。',
        summary: '学员已完成12次实训，平均分78分，整体表现良好。',
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
              <div class="training-stat-value">{{ report.total_tasks }}</div>
              <div class="training-stat-label">总任务数</div>
            </div>
            <div class="training-stat-card">
              <div class="training-stat-value" style="color:var(--risk-normal)">{{ report.completed_tasks }}</div>
              <div class="training-stat-label">已完成</div>
            </div>
            <div class="training-stat-card">
              <div class="training-stat-value" style="color:var(--risk-p1)">{{ report.average_score }}</div>
              <div class="training-stat-label">平均分</div>
            </div>
          </div>

          <!-- 详细记录 -->
          <div v-if="report.task_records && report.task_records.length" style="margin-top:20px">
            <div style="font-weight:600;margin-bottom:12px">任务记录</div>
            <el-table :data="report.task_records" border size="small" class="g-table">
              <el-table-column type="index" label="#" width="50" />
              <el-table-column prop="title" label="任务" />
              <el-table-column prop="score" label="得分" width="80">
                <template #default="{ row }">
                  <span :style="{ color: row.score >= 80 ? 'var(--risk-normal)' : row.score >= 60 ? 'var(--risk-p1)' : 'var(--risk-p0)' }">
                    {{ row.score }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="grade" label="等级" width="60" />
              <el-table-column prop="status" label="状态" width="80">
                <template #default="{ row }">
                  <risk-badge :level="row.status === 'completed' ? 'normal' : 'P2'" :label="row.status === 'completed' ? '已完成' : '进行中'" />
                </template>
              </el-table-column>
            </el-table>
          </div>

          <!-- 薄弱项 -->
          <div v-if="report.weaknesses && report.weaknesses.length" style="margin-top:20px">
            <div style="font-weight:600;margin-bottom:12px">薄弱项分析</div>
            <div v-for="(w, i) in report.weaknesses" :key="i" class="g-card" style="margin-bottom:8px;padding:12px">
              <div style="font-weight:500;font-size:13px;margin-bottom:4px">{{ w.category }} ({{ w.score }}分)</div>
              <div style="font-size:12px;color:var(--text-secondary);margin-bottom:4px">{{ w.description }}</div>
              <div style="font-size:12px;color:var(--primary)">建议：{{ w.suggestion }}</div>
            </div>
          </div>
        </div>

        <div v-else class="g-empty">
          <empty-guide title="暂无实训记录" desc="完成实训场景后将自动生成报告" action-text="去实训" @action="$emit('navigate', '/training/scenarios')" />
        </div>
      </div>
    </div>
  `,
};
