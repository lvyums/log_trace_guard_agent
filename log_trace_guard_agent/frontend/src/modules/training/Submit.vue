<template>
  <div class="g-stack">
    <AlertGuide type="warning" title="答题时遵循标准分析流程">
      评分标准：识别设备类型(10%)→提取关键字段(30%)→判断风险等级(20%)→给出处置建议(40%)。
    </AlertGuide>

    <div class="g-card" style="margin-bottom:16px;padding:12px">
      <div style="display:flex;align-items:center;gap:12px">
        <el-icon :size="20" color="var(--el-color-primary)"><Notebook /></el-icon>
        <span style="font-weight:600">{{ scenarioName }}</span>
      </div>
    </div>

    <div v-if="steps.length > 0" class="g-training-layout">
      <div class="g-training-task">
      <div class="g-card-title" style="margin-bottom:16px">
        <el-icon><Notebook /></el-icon> 实训任务
      </div>
      <div class="g-steps" style="margin-bottom:16px">
        <div v-for="(step, i) in steps" :key="i" class="g-step"
             @click="currentStep = i" style="cursor:pointer">
          <div class="g-step-num" :class="{ done: i < currentStep }">
            {{ stepResults[i]?.status === 'passed' ? '✓' : i + 1 }}
          </div>
          <div class="g-step-label">{{ step.title }}</div>
        </div>
      </div>
      <div class="g-divider" />
      <div style="margin-top:16px">
        <div style="font-weight:600;margin-bottom:8px">{{ steps[currentStep].title }}</div>
        <div style="font-size:13px;color:var(--text-secondary);margin-bottom:12px">
          {{ steps[currentStep].question }}
        </div>
        <div v-if="steps[currentStep].sample" class="g-code-block" style="margin-bottom:12px">
          <div class="g-code-body" style="max-height:100px;font-size:12px">
            {{ steps[currentStep].sample }}
          </div>
        </div>
        <div class="g-alert g-alert--info" style="margin-bottom:12px">
          <el-icon><InfoFilled /></el-icon>
          <span style="font-size:12px">{{ steps[currentStep].hint }}</span>
        </div>
        <div style="display:flex;gap:8px">
          <el-button size="small" :disabled="currentStep === 0" @click="prevStep">上一步</el-button>
          <el-button size="small" :disabled="currentStep >= totalSteps - 1" @click="nextStep">下一步</el-button>
        </div>
      </div>
    </div>

    <div class="g-training-workspace">
      <div class="g-card-title" style="margin-bottom:16px">
        <el-icon><EditPen /></el-icon> 答题区
      </div>
      <div v-for="(step, i) in steps" :key="i" style="margin-bottom:16px">
        <div style="font-size:13px;font-weight:500;margin-bottom:6px;color:var(--text-secondary)">
          步骤 {{ i + 1 }}: {{ step.title }}
          <span v-if="step.submitType" style="margin-left:8px;font-size:11px;color:var(--el-color-info)">
            ({{ step.submitTypeLabel }})
          </span>
          <span v-if="!answers[i]?.trim()" style="margin-left:8px;font-size:11px;color:var(--el-color-warning)">[待填写]</span>
          <span v-else style="margin-left:8px;font-size:11px;color:var(--el-color-success)">[已填写]</span>
        </div>
        <el-input v-model="answers[i]" type="textarea" :rows="2"
                  :placeholder="'请输入步骤' + (i+1) + '的答案...'"
                  :class="{ 'is-empty': !answers[i]?.trim() && showEmptyWarn }" />
      </div>

      <div v-if="!allFilled" style="font-size:12px;color:var(--el-color-warning);margin:4px 0 8px;display:flex;align-items:center;gap:4px">
        <el-icon :size="12"><WarningFilled /></el-icon>
        请填写所有步骤的答案后再提交（{{ filledCount }}/{{ totalSteps }}）
      </div>

      <el-button type="primary" :loading="loading" :disabled="!allFilled" style="width:100%;margin-top:8px" @click="submit">
        <el-icon style="margin-right:4px"><Promotion /></el-icon>
        {{ loading ? '提交中 (' + submittedCount + '/' + totalSteps + ')...' : '提交全部答案' }}
      </el-button>

      <!-- 逐步累积结果 -->
      <div v-for="(sr, si) in stepResults" :key="si" class="slide" style="margin-top:20px"
           v-if="sr">
        <div class="g-divider" />
        <div class="g-card-title" style="margin:16px 0 12px">
          <el-icon><TrophyBase /></el-icon> 步骤 {{ si + 1 }}: {{ steps[si]?.title }} — {{ sr.grade }}级
        </div>
        <el-descriptions :column="2" border size="small" style="margin-bottom:16px">
          <el-descriptions-item label="得分">{{ sr.score }} / 100</el-descriptions-item>
          <el-descriptions-item label="等级">
            <RiskBadge :level="gradeLevel(sr.grade)" :label="sr.grade" />
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="sr.checks?.length">
          <div v-for="(item, ci) in sr.checks" :key="ci"
               class="g-correction" :class="correctionClass(item)">
            <el-icon v-if="item.status === 'correct'"><CircleCheckFilled /></el-icon>
            <el-icon v-else-if="item.status === 'partial'"><WarningFilled /></el-icon>
            <el-icon v-else><CircleCloseFilled /></el-icon>
            <div>
              <div style="font-weight:500">{{ item.field }}</div>
              <div style="font-size:12px;opacity:0.8;margin-top:2px">{{ item.detail }}</div>
            </div>
          </div>
        </div>

        <!-- LLM 分析结果 -->
        <div v-if="sr.analysis && sr.analysis.trim()" style="margin-top:12px">
          <KnowledgePanel title="知识点详解">
            <div style="white-space:pre-wrap;line-height:1.8;font-size:13px">
              {{ sr.analysis }}
            </div>
          </KnowledgePanel>
        </div>
      </div>

      <!-- 全部完成后的汇总 -->
      <div v-if="allDone" class="slide" style="margin-top:24px">
        <div class="g-divider" />
        <el-alert title="所有任务提交完成" type="success" :closable="false" show-icon
                  style="margin:16px 0">
          <template #default>
            <div>总得分：{{ totalScore }} / {{ totalSteps * 100 }} | 平均分：{{ (totalScore / totalSteps).toFixed(1) }}</div>
          </template>
        </el-alert>
        <el-button type="primary" size="large" style="width:100%" @click="goToReport">
          <el-icon style="margin-right:4px"><DataLine /></el-icon>
          查看本次实训报告
        </el-button>
      </div>
    </div>
  </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { DataLine } from '@element-plus/icons-vue'
import { Api } from '../../api'
import AlertGuide from '../../components/AlertGuide.vue'
import RiskBadge from '../../components/RiskBadge.vue'
import KnowledgePanel from '../../components/KnowledgePanel.vue'

defineProps<{ mode?: string }>()

const answers = ref<Record<number, string>>({})
const currentStep = ref(0)
const loading = ref(false)
const submittedCount = ref(0)
const allDone = ref(false)
const totalScore = ref(0)
const stepResults = ref<any[]>([])
const scenarioName = ref('')
const scenarioId = ref('')
const steps = ref<{ title: string; question: string; sample: string; hint: string; taskId: string; submitType: string; submitTypeLabel: string }[]>([])
const totalSteps = computed(() => steps.value.length)

// 校验：所有大题框都必须填写
const allFilled = computed(() => {
  if (steps.value.length === 0) return false
  for (let i = 0; i < steps.value.length; i++) {
    const val = answers.value[i]
    if (!val || !val.trim()) return false
  }
  return true
})
const filledCount = computed(() => {
  let count = 0
  for (let i = 0; i < steps.value.length; i++) {
    if (answers.value[i]?.trim()) count++
  }
  return count
})
const showEmptyWarn = ref(false)

function gradeLevel(g: string) {
  if (g === 'A') return 'normal'
  if (g === 'B') return 'P2'
  return 'P0'
}

function nextStep() { if (currentStep.value < totalSteps.value - 1) currentStep.value++ }
function prevStep() { if (currentStep.value > 0) currentStep.value-- }

function correctionClass(item: any) {
  if (item.status === 'correct') return 'g-correction--correct'
  if (item.status === 'partial') return 'g-correction--miss'
  return 'g-correction--wrong'
}

onMounted(() => {
  try {
    const saved = sessionStorage.getItem('current-training-scenario')
    if (saved) {
      const scenario = JSON.parse(saved)
      const sid = scenario.scenario?.scenario_id || scenario.id || ''
      scenarioId.value = String(sid)
      scenarioName.value = scenario.scenario?.name || scenario.name || '实训场景'

      const tasks = scenario.tasks || []
      if (tasks.length > 0) {
        steps.value = tasks.map((t: any) => ({
          title: t.title || '',
          question: t.description || '',
          sample: Array.isArray(t.input_data) ? t.input_data.join('\n') : (t.input_data || ''),
          hint: t.hint || '',
          taskId: t.task_id || '',
          submitType: t.submit_type || 'conclusion',
          submitTypeLabel: ({
            conclusion: '结论分析',
            rule: '规则编写',
            script: '脚本编写',
            plan: '方案设计',
          })[t.submit_type || 'conclusion'] || '综合',
        }))
      } else {
        steps.value = [{ title: '加载中', question: '暂无任务数据', sample: '', hint: '', taskId: '', submitType: 'conclusion', submitTypeLabel: '' }]
      }
    } else {
      scenarioName.value = '实训场景'
      steps.value = [{ title: '未选择场景', question: '请先选择一个实训场景', sample: '', hint: '', taskId: '', submitType: 'conclusion', submitTypeLabel: '' }]
    }
  } catch {
    scenarioName.value = '实训场景'
    steps.value = [{ title: '加载失败', question: '场景数据加载异常', sample: '', hint: '', taskId: '', submitType: 'conclusion', submitTypeLabel: '' }]
  }
})

async function submit() {
  // 安全校验：确保所有题目已填写
  if (!allFilled.value) {
    showEmptyWarn.value = true
    ElMessage.warning('请先填写所有步骤的答案再提交')
    return
  }

  loading.value = true
  submittedCount.value = 0
  totalScore.value = 0
  allDone.value = false
  stepResults.value = []

  for (let i = 0; i < steps.value.length; i++) {
    const step = steps.value[i]
    const userAnswer = answers.value[i]?.trim() || ''

    try {
      // 逐任务提交到 /submit 端点（支持校验 + LLM分析 + 记录成绩）
      const resp = await Api.training.submit({
        scenario_id: scenarioId.value,
        task_id: step.taskId,
        submit_type: step.submitType,
        content: { user_answer: userAnswer },
        student_id: 'student_default',
      })

      if (resp.success && resp.data) {
        stepResults.value[i] = resp.data
        totalScore.value += resp.data.score || 0
      } else {
        stepResults.value[i] = {
          score: 0,
          grade: 'C',
          status: 'retry',
          checks: [],
          analysis: '⚠️ 提交失败: ' + (resp.msg || '未知错误'),
        }
      }
    } catch (err: any) {
      stepResults.value[i] = {
        score: 0,
        grade: 'C',
        status: 'retry',
        checks: [],
        analysis: '⚠️ 提交异常: ' + (err.message || '网络错误'),
      }
    }

    submittedCount.value = i + 1
  }

  allDone.value = true
  loading.value = false

  if (totalSteps.value > 0) {
    ElMessage.success(`全部 ${totalSteps.value} 个任务提交完成，平均分 ${(totalScore.value / totalSteps.value).toFixed(1)}`)
  }
}

function goToReport() {
  // 保存当前场景到 sessionStorage，报告页读取
  const scenario = { scenario_id: scenarioId.value, name: scenarioName.value }
  sessionStorage.setItem('report-scenario', JSON.stringify(scenario))
  window.location.hash = '#/training/report'
}
</script>

<style scoped>
.streaming-cursor {
  animation: blink 0.8s step-end infinite;
  color: var(--el-color-primary);
}
@keyframes blink {
  50% { opacity: 0; }
}
.is-empty :deep(.el-textarea__inner) {
  border-color: var(--el-color-warning);
  box-shadow: 0 0 0 1px var(--el-color-warning);
}
</style>
