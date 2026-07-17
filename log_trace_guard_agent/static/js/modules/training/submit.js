/* ============================================
   模块五 · 提训答案 — 提交实训答案并获取评分
   ============================================ */

const TrainingSubmit = {
  name: 'TrainingSubmit',
  props: { mode: String },
  data() {
    return {
      scenarioId: 1,
      answers: {},
      currentStep: 0,
      loading: false,
      result: null,
      steps: [
        { title: '日志识别', question: '请识别以下日志的设备类型和格式', sample: '<22>Jan  5 12:34:56 sshd[12345]: Failed password for root from 192.168.1.100 port 22', hint: '提示：观察日志前缀和关键字' },
        { title: '字段提取', question: '提取日志中的关键字段（用户名、源IP、端口）', sample: '', hint: '提示：使用键值对格式，如 username: xxx' },
        { title: '风险研判', question: '判断该日志的安全风险等级并说明理由', sample: '', hint: '提示：P0极高危/P1高危/P2中危/P3低危/正常' },
      ],
    };
  },
  computed: {
    isTraining() {
      return this.mode === 'training';
    },
    totalSteps() {
      return this.steps.length;
    },
  },
  methods: {
    nextStep() {
      if (this.currentStep < this.totalSteps - 1) this.currentStep++;
    },
    prevStep() {
      if (this.currentStep > 0) this.currentStep--;
    },
    async submit() {
      this.loading = true;
      this.result = null;
      try {
        const res = await Api.training.submit({
          scenario_id: String(this.scenarioId),
          task_id: 'task_' + this.scenarioId,
          submit_type: 'conclusion',
          content: this.answers,
          student_id: 'student_default',
        });
        if (res.success) {
          this.result = res.data;
        } else {
          ElementPlus.ElMessage.error(res.msg);
        }
      } catch (e) {
        ElementPlus.ElMessage.error('提交失败');
      } finally {
        this.loading = false;
      }
    },
    getCorrectionClass(item) {
      if (item.status === 'correct') return 'g-correction--correct';
      if (item.status === 'partial') return 'g-correction--miss';
      return 'g-correction--wrong';
    },
  },
  template: `
    <div class="g-training-layout">
      <alert-guide type="warning" title="答题时遵循标准分析流程">
        评分标准：识别设备类型(10%)→提取关键字段(30%)→判断风险等级(20%)→给出处置建议(40%)。每步都有对应分值，漏掉任何一步都会扣分。
      </alert-guide>

      <!-- 左栏：任务题干 -->
      <div class="g-training-task">
        <div class="g-card-title" style="margin-bottom:16px"><el-icon><Notebook /></el-icon> 实训任务</div>

        <!-- 步骤进度 -->
        <div class="g-steps" style="margin-bottom:16px">
          <div v-for="(step, i) in steps" :key="i" class="g-step" @click="currentStep = i" style="cursor:pointer">
            <div class="g-step-num" :class="{ done: i < currentStep }">{{ i < currentStep ? '✓' : i + 1 }}</div>
            <div class="g-step-label">{{ step.title }}</div>
          </div>
        </div>

        <div class="g-divider"></div>

        <!-- 当前步骤 -->
        <div style="margin-top:16px">
          <div style="font-weight:600;margin-bottom:8px">{{ steps[currentStep].title }}</div>
          <div style="font-size:13px;color:var(--text-secondary);margin-bottom:12px">{{ steps[currentStep].question }}</div>

          <div v-if="steps[currentStep].sample" class="g-code-block" style="margin-bottom:12px">
            <div class="g-code-body" style="max-height:100px;font-size:12px">{{ steps[currentStep].sample }}</div>
          </div>

          <div class="g-alert g-alert--info" style="margin-bottom:12px">
            <el-icon><InfoFilled /></el-icon>
            <span style="font-size:12px">{{ steps[currentStep].hint }}</span>
          </div>

          <div style="display:flex;gap:8px">
            <el-button size="small" @click="prevStep" :disabled="currentStep === 0">上一步</el-button>
            <el-button size="small" @click="nextStep" :disabled="currentStep >= totalSteps - 1">下一步</el-button>
          </div>
        </div>
      </div>

      <!-- 右栏：答题操作区 -->
      <div class="g-training-workspace">
        <div class="g-card-title" style="margin-bottom:16px"><el-icon><EditPen /></el-icon> 答题区</div>

        <div v-for="(step, i) in steps" :key="i" style="margin-bottom:16px">
          <div style="font-size:13px;font-weight:500;margin-bottom:6px;color:var(--text-secondary)">
            步骤 {{ i + 1 }}: {{ step.title }}
          </div>
          <el-input v-model="answers[i]" type="textarea" :rows="2"
                    :placeholder="'请输入步骤' + (i+1) + '的答案...'" />
          <div class="g-input-guide">
            <el-icon><InfoFilled /></el-icon>
            <span>请根据左侧题干要求填写答案</span>
          </div>
        </div>

        <el-button type="primary" @click="submit" :loading="loading" style="width:100%;margin-top:8px">
          <el-icon style="margin-right:4px"><Promotion /></el-icon> 提交答案
        </el-button>

        <!-- 评分结果 -->
        <div v-if="result" class="slide" style="margin-top:20px">
          <div class="g-divider"></div>
          <div class="g-card-title" style="margin:16px 0 12px"><el-icon><TrophyBase /></el-icon> 评分结果</div>

          <el-descriptions :column="2" border size="small" style="margin-bottom:16px">
            <el-descriptions-item label="总分">{{ result.score || 0 }} / 100</el-descriptions-item>
            <el-descriptions-item label="等级">
              <risk-badge :level="result.score >= 90 ? 'normal' : result.score >= 70 ? 'P2' : 'P0'"
                         :label="result.grade || (result.score >= 90 ? 'A' : result.score >= 70 ? 'B' : 'C')" />
            </el-descriptions-item>
          </el-descriptions>

          <!-- 分层纠错 -->
          <div v-if="result.checks">
            <div v-for="(item, i) in result.checks" :key="i" class="g-correction" :class="getCorrectionClass(item)">
              <el-icon v-if="item.status === 'correct'"><CircleCheckFilled /></el-icon>
              <el-icon v-else-if="item.status === 'partial'"><WarningFilled /></el-icon>
              <el-icon v-else><CircleCloseFilled /></el-icon>
              <div>
                <div style="font-weight:500">{{ item.field }}</div>
                <div style="font-size:12px;opacity:0.8;margin-top:2px">{{ item.detail }}</div>
              </div>
            </div>
          </div>

          <knowledge-panel title="知识点详解">
            <p>{{ result.analysis || '请根据评分反馈复习相关知识点，重点关注标记为错误和遗漏的部分。' }}</p>
          </knowledge-panel>
        </div>
      </div>
    </div>
  `,
};
