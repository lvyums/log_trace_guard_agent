<template>
  <div class="g-stack">
    <AlertGuide type="info" title="生成专属指导手册">
      填写基础参数，系统自动调用采集方案、架构推荐、平台选型三个模块获取结构化数据，再由 AI 生成完整指导手册。
    </AlertGuide>
    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><Notebook /></el-icon> 指导手册生成</div>
          <div class="g-card-desc">填写参数，系统自动整合三个模块的数据生成手册</div>
        </div>
        <el-button size="small" type="primary" plain @click="fillExample">填充示例</el-button>
      </div>
      <el-form label-position="top" size="default">
        <el-form-item label="企业规模">
          <el-radio-group v-model="scale">
            <el-radio-button v-for="s in scaleOptions" :key="s.value" :value="s.value">{{ s.label }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="安全设备类型（多选）">
          <el-select v-model="deviceTypes" multiple placeholder="选择设备类型" style="width:100%">
            <el-option v-for="d in deviceOptions" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="安全设备数量">
          <el-input-number v-model="deviceCount" :min="1" :max="10000" style="width:100%" />
        </el-form-item>
        <el-form-item label="日均日志量">
          <el-radio-group v-model="dailyLogVolume">
            <el-radio-button v-for="v in volumeOptions" :key="v.value" :value="v.value">{{ v.label }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="预算水平">
          <el-radio-group v-model="budget">
            <el-radio-button v-for="b in budgetOptions" :key="b.value" :value="b.value">{{ b.label }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="运维能力">
          <el-radio-group v-model="teamSkill">
            <el-radio-button v-for="s in skillOptions" :key="s.value" :value="s.value">{{ s.label }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <!-- 数据来源状态 -->
      <div v-if="fetching" style="margin:12px 0;padding:12px;background:var(--bg-secondary);border-radius:6px;font-size:13px">
        <div style="margin-bottom:8px;color:var(--text-secondary)">正在获取模块数据...</div>
        <div v-for="step in fetchSteps" :key="step.name" style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
          <el-icon v-if="step.status==='done'" color="var(--el-color-success)"><CircleCheckFilled /></el-icon>
          <el-icon v-else-if="step.status==='error'" color="var(--el-color-danger)"><CircleCloseFilled /></el-icon>
          <el-icon v-else class="is-loading"><Loading /></el-icon>
          <span :style="{color: step.status==='error'?'var(--el-color-danger)':'var(--text-secondary)'}">{{ step.label }}</span>
        </div>
      </div>

      <div class="g-actions">
        <el-button type="primary" @click="submit" :loading="loading" :disabled="fetching">生成手册</el-button>
      </div>
    </div>
    <div v-if="result" class="g-card slide">
      <div class="g-card-header">
        <div class="g-card-title"><el-icon><Document /></el-icon> 指导手册</div>
        <el-button type="success" @click="downloadMarkdown" :icon="Download">下载 Markdown</el-button>
      </div>
      <div class="guide-content" v-html="renderedContent"></div>
    </div>
    <div v-if="!result && !loading && !fetching" class="g-card">
      <EmptyGuide title="填写参数生成指导手册" desc="参数越完整，生成的手册越精准" action-text="填充示例" @action="fillExample" />
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import { APP_CONFIG } from '../../config'
import { Api } from '../../api'
import AlertGuide from '../../components/AlertGuide.vue'
import EmptyGuide from '../../components/EmptyGuide.vue'
defineProps<{ mode?: string }>()

const scale = ref('medium')
const deviceTypes = ref<string[]>([])
const deviceCount = ref(50)
const dailyLogVolume = ref('medium')
const budget = ref('medium')
const teamSkill = ref('basic')
const loading = ref(false)
const fetching = ref(false)
const result = ref<any>(null)

const deviceOptions = APP_CONFIG.sampleData.deviceTypes
const scaleOptions = [{ label: '小型（<100人）', value: 'small' }, { label: '中型（100-1000人）', value: 'medium' }, { label: '大型（>1000人）', value: 'large' }]
const volumeOptions = [{ label: '小（<10GB/天）', value: 'small' }, { label: '中（10-100GB/天）', value: 'medium' }, { label: '大（>100GB/天）', value: 'large' }]
const budgetOptions = [{ label: '低预算', value: 'low' }, { label: '中等预算', value: 'medium' }, { label: '高预算', value: 'high' }]
const skillOptions = [{ label: '基础运维', value: 'basic' }, { label: '中级运维', value: 'intermediate' }, { label: '高级运维', value: 'advanced' }]

interface FetchStep { name: string; label: string; status: 'pending' | 'loading' | 'done' | 'error' }
const fetchSteps = ref<FetchStep[]>([])

function fillExample() {
  scale.value = 'medium'
  deviceTypes.value = ['firewall', 'waf', 'ids']
  deviceCount.value = 65
  dailyLogVolume.value = 'medium'
  budget.value = 'medium'
  teamSkill.value = 'intermediate'
}

const renderedContent = computed(() => {
  if (!result.value?.content) return ''
  return simpleMarkdown(result.value.content)
})

function simpleMarkdown(text: string): string {
  let r = text.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
  r = r.replace(/^### (.+)$/gm, '<h3>$1</h3>')
  r = r.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  r = r.replace(/^# (.+)$/gm, '<h1>$1</h1>')
  r = r.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  r = r.replace(/`([^`\n]+)`/g, '<code>$1</code>')
  r = r.replace(/^- (.+)$/gm, '<li>$1</li>')
  r = r.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
  r = r.replace(/\n/g, '<br>')
  return r
}

async function submit() {
  if (!deviceTypes.value.length) { ElMessage.warning('请至少选择一种设备类型'); return }

  loading.value = true
  fetching.value = true
  result.value = null

  // 初始化步骤状态
  fetchSteps.value = [
    { name: 'plan', label: '获取采集方案...', status: 'pending' },
    { name: 'arch', label: '获取架构推荐...', status: 'pending' },
    { name: 'platform', label: '获取平台选型...', status: 'pending' },
    { name: 'guide', label: '生成指导手册...', status: 'pending' },
  ]

  try {
    // Step 1: 并行调用三个模块
    fetchSteps.value[0].status = 'loading'
    fetchSteps.value[1].status = 'loading'
    fetchSteps.value[2].status = 'loading'

    const planPromises = deviceTypes.value.map(dt =>
      Api.logCollect.plan({ device_type: dt, device_model: '', scale: scale.value })
    )

    const [planResults, archResult, platformResult] = await Promise.allSettled([
      Promise.all(planPromises),
      Api.advisory.arch({
        device_count: deviceCount.value,
        daily_log_volume: dailyLogVolume.value,
        budget: budget.value,
        team_skill: teamSkill.value,
      }),
      Api.advisory.platform({
        device_count: deviceCount.value,
        daily_log_volume: dailyLogVolume.value,
        budget: budget.value,
        team_skill: teamSkill.value,
      }),
    ])

    // 收集结果
    const collectPlans = planResults.status === 'fulfilled'
      ? planResults.value.filter((r: any) => r.success).map((r: any) => r.data)
      : []
    const architecture = archResult.status === 'fulfilled' && archResult.value.success ? archResult.value.data : null
    const platform = platformResult.status === 'fulfilled' && platformResult.value.success ? platformResult.value.data : null

    fetchSteps.value[0].status = collectPlans.length > 0 ? 'done' : 'error'
    fetchSteps.value[1].status = architecture ? 'done' : 'error'
    fetchSteps.value[2].status = platform ? 'done' : 'error'

    if (collectPlans.length === 0) {
      ElMessage.warning('采集方案获取失败，将继续生成但配置内容可能不完整')
    } else {
      ElMessage.success(`已获取 ${collectPlans.length} 个设备的采集方案`)
    }

    // Step 2: 调用 guide API
    fetchSteps.value[3].status = 'loading'
    fetching.value = false

    const r = await Api.advisory.guide({
      scale: scale.value,
      device_types: deviceTypes.value,
      device_count: deviceCount.value,
      daily_log_volume: dailyLogVolume.value,
      budget: budget.value,
      team_skill: teamSkill.value,
      collect_plans: collectPlans,
      architecture,
      platform,
    })

    if (r.success) {
      result.value = r.data
      fetchSteps.value[3].status = 'done'
    } else {
      const errMsg = r.data?.detail || r.msg || '生成失败'
      ElMessage.error(errMsg)
      fetchSteps.value[3].status = 'error'
    }
  } catch (e: any) {
    const errMsg = e?.message || '请求失败，请检查网络连接'
    ElMessage.error(errMsg)
    fetchSteps.value.forEach(s => { if (s.status === 'loading') s.status = 'error' })
  } finally {
    loading.value = false
    fetching.value = false
  }
}

function downloadMarkdown() {
  if (!result.value?.content) return
  const blob = new Blob([result.value.content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `日志采集指导手册_${new Date().toISOString().slice(0, 10)}.md`
  a.click()
  URL.revokeObjectURL(url)
}
</script>
<style scoped>
.guide-content {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-primary);
  max-height: 600px;
  overflow-y: auto;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
}
.guide-content :deep(h1) { font-size: 20px; margin: 16px 0 8px; }
.guide-content :deep(h2) { font-size: 17px; margin: 14px 0 6px; color: var(--color-primary); }
.guide-content :deep(h3) { font-size: 15px; margin: 12px 0 4px; }
.guide-content :deep(code) {
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}
.guide-content :deep(pre) {
  background: var(--bg-tertiary);
  padding: 12px 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}
.guide-content :deep(pre code) {
  background: none;
  padding: 0;
}
.guide-content :deep(ul) {
  padding-left: 20px;
  margin: 4px 0;
}
.guide-content :deep(li) {
  margin: 2px 0;
}
</style>
