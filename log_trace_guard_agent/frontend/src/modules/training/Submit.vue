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
            {{ i < currentStep ? '✓' : i + 1 }}
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
        </div>
        <el-input v-model="answers[i]" type="textarea" :rows="2"
                  :placeholder="'请输入步骤' + (i+1) + '的答案...'" />
      </div>

      <el-button type="primary" :loading="loading" style="width:100%;margin-top:8px" @click="submit">
        <el-icon style="margin-right:4px"><Promotion /></el-icon>
        {{ loading ? '分析中...' : '提交答案' }}
      </el-button>

      <div v-if="resultShown" class="slide" style="margin-top:20px">
        <div class="g-divider" />
        <div class="g-card-title" style="margin:16px 0 12px">
          <el-icon><TrophyBase /></el-icon> 评分结果
        </div>
        <el-descriptions :column="2" border size="small" style="margin-bottom:16px">
          <el-descriptions-item label="总分">{{ score }} / 100</el-descriptions-item>
          <el-descriptions-item label="等级">
            <RiskBadge :level="gradeLevel" :label="grade" />
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="checks.length">
          <div v-for="(item, i) in checks" :key="i"
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

        <KnowledgePanel title="知识点详解" v-if="streamingAnalysis">
          <div class="streaming-text" style="white-space:pre-wrap;line-height:1.8">
            {{ streamingAnalysis }}
            <span v-if="isStreaming" class="streaming-cursor">▍</span>
          </div>
        </KnowledgePanel>
      </div>
    </div>
  </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Api } from '../../api'
import AlertGuide from '../../components/AlertGuide.vue'
import RiskBadge from '../../components/RiskBadge.vue'
import KnowledgePanel from '../../components/KnowledgePanel.vue'

defineProps<{ mode?: string }>()

const answers = ref<Record<number, string>>({})
const currentStep = ref(0)
const loading = ref(false)
const isStreaming = ref(false)
const resultShown = ref(false)
const score = ref(0)
const grade = ref('C')
const checks = ref<any[]>([])
const streamingAnalysis = ref('')
const scenarioName = ref('')
const scenarioId = ref('')
const steps = ref<{ title: string; question: string; sample: string; hint: string }[]>([
  { title: '加载中...', question: '', sample: '', hint: '' },
])
const totalSteps = computed(() => steps.value.length)
const gradeLevel = computed(() => {
  if (grade.value === 'A') return 'normal'
  if (grade.value === 'B') return 'P2'
  return 'P0'
})

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

      // 从后端返回的任务数据中构建步骤
      const tasks = scenario.tasks || []
      if (tasks.length > 0) {
        steps.value = tasks.map((t: any) => ({
          title: t.title || '',
          question: t.description || '',
          sample: Array.isArray(t.input_data) ? t.input_data.join('\n') : (t.input_data || ''),
          hint: t.hint || '',
        }))
      } else {
        steps.value = [{ title: '加载中', question: '暂无任务数据', sample: '', hint: '' }]
      }
    } else {
      scenarioName.value = '实训场景'
      steps.value = [{ title: '未选择场景', question: '请先选择一个实训场景', sample: '', hint: '' }]
    }
  } catch {
    scenarioName.value = '实训场景'
    steps.value = [{ title: '加载失败', question: '场景数据加载异常', sample: '', hint: '' }]
  }
})

async function submit() {
  loading.value = true
  resultShown.value = false
  streamingAnalysis.value = ''
  isStreaming.value = true

  await Api.training.analyzeStream(
    {
      scenario_id: scenarioId.value,
      task_id: 'task_' + scenarioId.value,
      submit_type: 'conclusion',
      content: answers.value,
      student_id: 'student_default',
    },
    {
      onResult: (r) => {
        score.value = r.score
        grade.value = r.grade
        checks.value = r.checks
        resultShown.value = true
      },
      onToken: (text) => { streamingAnalysis.value += text },
      onDone: () => {
        isStreaming.value = false
        loading.value = false
      },
      onError: (err) => {
        ElMessage.error('分析失败: ' + err)
        loading.value = false
        isStreaming.value = false
      },
    },
  )

  // 兜底超时
  setTimeout(() => {
    if (loading.value) {
      loading.value = false
      isStreaming.value = false
    }
  }, 30000)
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
</style>