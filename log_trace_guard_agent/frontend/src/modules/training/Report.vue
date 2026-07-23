<template>
  <div class="g-stack">
    <div class="g-card">
      <div class="g-card-header">
        <div class="g-card-title"><el-icon><DataBoard /></el-icon> 实训报告</div>
        <div class="g-card-desc">查看实训统计与详细报告</div>
      </div>
      <el-form label-position="top" size="default">
        <el-form-item label="选择实训场景">
          <el-select v-model="selectedScenario" placeholder="选择场景" style="width:100%" @change="autoLoad">
            <el-option v-for="s in scenarioOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="学员ID">
          <el-input v-model="studentId" placeholder="如: student_default" />
        </el-form-item>
      </el-form>
      <div class="g-actions">
        <el-button type="primary" @click="loadReport" :loading="loading">查看报告</el-button>
      </div>
    </div>
    <div v-if="report" class="g-card slide">
      <div class="g-card-header">
        <div class="g-card-title"><el-icon><DataLine /></el-icon> 报告详情</div>
        <div style="font-size:12px;color:var(--text-tertiary)">
          场景: {{ report.scenario_name || selectedScenarioLabel }}
        </div>
      </div>
      <el-descriptions :column="2" border size="small" style="margin-bottom:16px">
        <el-descriptions-item label="场景名称">{{ report.scenario_name || selectedScenarioLabel }}</el-descriptions-item>
        <el-descriptions-item label="综合等级"><RiskBadge :level="report.overall_grade==='A'?'normal':report.overall_grade==='B'?'P2':'P0'" :label="report.overall_grade || '-'" /></el-descriptions-item>
        <el-descriptions-item label="总分">{{ report.average_score ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="任务完成">{{ report.completed_tasks || 0 }} / {{ report.total_tasks || 0 }}</el-descriptions-item>
      </el-descriptions>
      <div v-if="report.task_records?.length">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">详细得分</div>
        <div v-for="(item,i) in report.task_records" :key="i" style="margin-bottom:8px;padding:8px;border:1px solid var(--border-color);border-radius:4px">
          <div style="display:flex;justify-content:space-between;font-size:13px">
            <span>{{ item.title }}</span>
            <RiskBadge :level="item.score>=80?'normal':item.score>=60?'P2':'P0'" :label="item.score+'分'" />
          </div>
          <div style="font-size:12px;color:var(--text-tertiary);margin-top:4px">尝试次数: {{ item.attempts }} | 等级: {{ item.grade }}</div>
        </div>
      </div>
      <div v-if="report.summary" style="margin-top:12px;padding:12px;background:var(--bg-secondary);border-radius:4px;font-size:13px;color:var(--text-secondary);line-height:1.8;white-space:pre-wrap">{{ report.summary }}</div>
      <div v-if="report.improvement_plan" style="margin-top:12px;font-size:13px;color:var(--text-secondary);line-height:1.8;white-space:pre-wrap">{{ report.improvement_plan }}</div>
    </div>
    <div v-if="!report && !loading" class="g-card">
      <div style="text-align:center;padding:40px;color:var(--text-secondary)">
        <el-icon :size="48"><DataBoard /></el-icon>
        <div style="margin-top:8px">选择场景和学员ID，查看实训报告</div>
        <div style="font-size:12px;margin-top:4px">提示：完成答题后自动记录成绩，直接选择同一场景即可查看</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Api } from '../../api'
import RiskBadge from '../../components/RiskBadge.vue'

defineProps<{ mode?: string }>()

const scenariosRaw = ref<any[]>([])
const selectedScenario = ref('')
const studentId = ref('student_default')
const loading = ref(false)
const report = ref<any>(null)
const loadingScenarios = ref(false)

const scenarioOptions = computed(() => {
  // 优先显示已有记录的场景，且尽量在下拉框中看到
  return scenariosRaw.value.length > 0
    ? scenariosRaw.value.map((s: any) => {
        const sc = s.scenario || {}
        return { label: sc.name || s.name || sc.scenario_id || s.id, value: sc.scenario_id || s.id }
      })
    : [{ label: '日志基础认知', value: 'S001' }]  // fallback
})

const selectedScenarioLabel = computed(() => {
  const opt = scenarioOptions.value.find((o: any) => o.value === selectedScenario.value)
  return opt?.label || selectedScenario.value
})

async function loadScenarios() {
  loadingScenarios.value = true
  try {
    const res = await Api.training.scenarios()
    if (res.success && res.data) {
      const list = Array.isArray(res.data) ? res.data : (res.data.scenarios || [])
      if (list.length > 0) {
        scenariosRaw.value = list
        if (!selectedScenario.value) {
          selectedScenario.value = (list[0].scenario?.scenario_id || list[0].id || list[0].scenario_id) as string
        }
      }
    }
  } catch {
    // fallback — scenarioOptions 的后备数据已准备好
  }
  loadingScenarios.value = false
}

async function loadReport() {
  if (!selectedScenario.value) {
    ElMessage.warning('请先选择实训场景')
    return
  }
  loading.value = true
  report.value = null
  try {
    const r = await Api.training.report({ scenario_id: selectedScenario.value, student_id: studentId.value })
    if (r.success) {
      if (r.data && r.data.total_tasks > 0) {
        report.value = r.data
      } else {
        ElMessage.info('该场景暂无实训记录，请先完成答题')
        report.value = r.data  // 仍然显示，但会显示 0/0
      }
    } else {
      ElMessage.error(r.msg || '请求失败')
    }
  } catch {
    ElMessage.error('请求失败')
  }
  loading.value = false
}

// 选中场景后自动加载 — 但只在首次或手动选择后触发
function autoLoad() {
  // 不自动请求，让用户点击"查看报告"
}

onMounted(() => {
  // 从 Submit.vue 跳转时获取场景信息
  try {
    const stored = sessionStorage.getItem('report-scenario')
    if (stored) {
      const sc = JSON.parse(stored)
      if (sc.scenario_id) {
        selectedScenario.value = sc.scenario_id
      }
      sessionStorage.removeItem('report-scenario')
    }
  } catch { /* ignore */ }
  loadScenarios()
})
</script>
