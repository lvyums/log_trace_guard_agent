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

    <div class="g-training-layout">
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
const scenarioId = ref('1')

// 根据场景动态生成步骤
const scenarioSteps: Record<string, { title: string; question: string; sample: string; hint: string }[]> = {
  '1': [
    { title: '日志识别', question: '请识别以下日志的设备类型和格式', sample: '<22>Jan  5 12:34:56 sshd[12345]: Failed password for root from 192.168.1.100 port 22', hint: '提示：观察日志前缀和关键字，判断是哪种安全设备' },
    { title: '字段提取', question: '提取日志中的关键字段（用户名、源IP、端口）', sample: '', hint: '提示：使用键值对格式，如 username: xxx' },
    { title: '风险研判', question: '判断该日志的安全风险等级并说明理由', sample: '', hint: '提示：P0极高危/P1高危/P2中危/P3低危/正常' },
  ],
  '2': [
    { title: '攻击类型识别', question: '请识别以下Web日志中的攻击类型', sample: '192.168.1.100 - - [15/Jan/2024:10:30:00 +0800] "GET /api/login?username=admin%27%20OR%20%271%27%3D%271 HTTP/1.1" 500 1234', hint: '提示：观察URL参数中的特殊字符' },
    { title: '攻击参数提取', question: '提取攻击Payload中的关键参数', sample: '', hint: '提示：关注SQL注入、XSS等攻击的特征字符串' },
    { title: '影响分析', question: '分析该攻击可能造成的影响范围', sample: '', hint: '提示：考虑数据泄露、权限提升等风险' },
    { title: '处置建议', question: '给出针对该攻击的处置建议', sample: '', hint: '提示：从WAF规则、输入过滤、最小权限等角度' },
    { title: '溯源分析', question: '尝试还原攻击者的攻击路径', sample: '', hint: '提示：关联攻击IP的历史行为' },
  ],
  '3': [
    { title: '入口点识别', question: '识别攻击者的初始入侵入口', sample: 'Dec 15 08:12:34 web-server sshd[23456]: Accepted password for admin from 10.0.0.5 port 22', hint: '提示：关注远程登录成功的日志' },
    { title: '横向移动追踪', question: '追踪攻击者在内网的横向移动路径', sample: 'Dec 15 08:15:34 db-server mysqld[34567]: SELECT * FROM users', hint: '提示：关注不同服务器间的连接' },
    { title: '权限提升分析', question: '分析攻击者是否进行了权限提升', sample: '', hint: '提示：关注sudo、su等命令的使用' },
    { title: '数据泄露评估', question: '评估可能的数据泄露范围', sample: '', hint: '提示：关注数据库查询、文件下载等操作' },
    { title: '攻击链还原', question: '完整还原攻击链并给出处置方案', sample: '', hint: '提示：组合所有发现，形成完整攻击链' },
    { title: '应急响应建议', question: '给出分级应急响应建议', sample: '', hint: '提示：从遏制、根除、恢复三个阶段' },
    { title: '整改措施', question: '提出防止类似攻击的长效整改措施', sample: '', hint: '提示：从网络隔离、访问控制、监控告警等角度' },
  ],
  '4': [
    { title: '需求分析', question: '分析企业的日志采集需求', sample: '某企业有200台服务器，需要满足等保2.0合规要求，日志留存≥180天', hint: '提示：考虑设备数量、日志类型、合规要求' },
    { title: '架构设计', question: '设计日志采集架构', sample: '', hint: '提示：选择采集协议、传输方式、存储方案' },
    { title: '容量规划', question: '计算存储容量和带宽需求', sample: '', hint: '提示：考虑日志量、压缩比、留存时间' },
    { title: '成本估算', question: '估算硬件和运维成本', sample: '', hint: '提示：考虑服务器、存储、带宽、人力成本' },
  ],
  '5': [
    { title: '身份鉴别检查', question: '检查服务器的身份鉴别配置是否合规', sample: '检查项：密码策略、登录失败锁定、远程管理', hint: '提示：等保2.0三级要求密码复杂度、登录失败锁定等' },
    { title: '访问控制检查', question: '检查访问控制配置是否合规', sample: '', hint: '提示：检查默认账户、权限分离、最小权限原则' },
    { title: '安全审计检查', question: '检查安全审计配置是否合规', sample: '', hint: '提示：检查日志记录范围、审计策略、日志保护' },
  ],
}

const steps = computed(() => {
  return scenarioSteps[scenarioId.value] || scenarioSteps['1']
})
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
      const sid = scenario.scenario?.scenario_id || scenario.id || '1'
      scenarioId.value = String(sid)
      scenarioName.value = scenario.scenario?.name || scenario.name || '实训场景'
    } else {
      scenarioName.value = 'SSH暴力破解检测'
    }
  } catch {
    scenarioName.value = 'SSH暴力破解检测'
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