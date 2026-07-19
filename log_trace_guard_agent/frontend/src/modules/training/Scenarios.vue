<template>
  <div class="g-stack">
    <AlertGuide type="info" title="选择场景前先评估自己的水平">
      初级：适合刚接触日志分析的学员，主要考察基础字段提取能力。中级：需要理解攻击原理。高级：需要完整还原攻击链。
    </AlertGuide>

    <AlertGuide v-if="mode === 'training'" type="info" title="实训模式已开启">
      选择一个实训场景开始练习。每个场景包含分步指引和标准答案，完成后可查看详细报告。
    </AlertGuide>

    <div class="g-card">
      <div class="g-card-header">
        <div class="g-card-title"><el-icon><Reading /></el-icon> 实训场景</div>
      </div>

      <div v-if="loading" style="text-align:center;padding:40px">
        <el-icon class="is-loading" :size="32" color="var(--el-color-primary)"><Loading /></el-icon>
        <div style="margin-top:8px;font-size:13px;color:var(--text-tertiary)">加载中...</div>
      </div>

      <div v-else-if="!scenarios.length">
        <EmptyGuide title="暂无实训场景" desc="请稍后再试或联系管理员" />
      </div>

      <div v-else style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px">
        <div
          v-for="s in scenarios" :key="s.scenario?.scenario_id || s.id"
          class="training-task-item"
          :class="{ active: selected?.scenario?.scenario_id === s.scenario?.scenario_id }"
          @click="selectScenario(s)"
        >
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
            <div style="display:flex;align-items:center;gap:8px">
              <span class="training-task-num">{{ s.scenario?.scenario_id || s.id }}</span>
              <span class="training-task-title">{{ s.scenario?.name || s.title }}</span>
            </div>
            <RiskBadge
              :level="diffLevel(s.scenario?.difficulty || s.difficulty)"
              :label="s.scenario?.difficulty || s.difficulty"
            />
          </div>
          <div style="font-size:12px;color:var(--text-tertiary);margin-bottom:6px">
            {{ s.scenario?.category || s.category }} · {{ s.total_tasks || s.steps || 0 }}个步骤
          </div>
          <div style="font-size:13px;color:var(--text-secondary)">{{ s.scenario?.description || s.description }}</div>
        </div>
      </div>
    </div>

    <div v-if="selected && mode === 'training'" class="g-actions" style="justify-content:center">
      <el-button type="primary" size="large" @click="startTraining">
        <el-icon style="margin-right:4px"><Promotion /></el-icon> 开始实训
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Api } from '../../api'
import AlertGuide from '../../components/AlertGuide.vue'
import RiskBadge from '../../components/RiskBadge.vue'
import EmptyGuide from '../../components/EmptyGuide.vue'

defineProps<{ mode?: string }>()

const scenarios = ref<any[]>([])
const loading = ref(false)
const selected = ref<any>(null)

async function loadScenarios() {
  loading.value = true
  try {
    const res = await Api.training.scenarios()
    if (res.success && res.data) {
      scenarios.value = Array.isArray(res.data) ? res.data : (res.data.scenarios || [])
      loading.value = false
      return
    }
    if (res.success && !res.data) {
      loading.value = false
      return
    }
  } catch {
    // fall through to sample
  }
  // Sample fallback when API fails
  scenarios.value = [
    { scenario: { scenario_id: '1', name: 'SSH暴力破解检测', difficulty: '初级', category: '入侵检测', description: '分析SSH登录日志，识别暴力破解行为并溯源攻击IP' }, total_tasks: 3 },
    { scenario: { scenario_id: '2', name: 'Web攻击日志分析', difficulty: '中级', category: 'Web安全', description: '分析WAF日志，识别SQL注入、XSS等Web攻击' }, total_tasks: 5 },
    { scenario: { scenario_id: '3', name: '内网横向移动追踪', difficulty: '高级', category: '应急响应', description: '通过多源日志关联分析，追踪内网横向移动路径' }, total_tasks: 7 },
    { scenario: { scenario_id: '4', name: '日志采集架构设计', difficulty: '中级', category: '架构设计', description: '根据企业需求设计完整的日志采集与存储架构' }, total_tasks: 4 },
    { scenario: { scenario_id: '5', name: '合规基线检查', difficulty: '初级', category: '合规审计', description: '对服务器配置进行等保2.0三级合规自查' }, total_tasks: 3 },
  ]
  loading.value = false
}

function diffLevel(d: string): string {
  return d === '高级' ? 'P0' : d === '中级' ? 'P1' : 'P3'
}

function selectScenario(s: any) {
  selected.value = s
}

function startTraining() {
  if (selected.value) {
    // 保存选中场景到 sessionStorage，Submit.vue 读取
    sessionStorage.setItem('current-training-scenario', JSON.stringify(selected.value))
    window.location.hash = '#/training/submit'
  }
}

loadScenarios()
</script>