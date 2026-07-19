<template>
  <div class="g-stack">
    <AlertGuide type="info" title="攻击链模式库">
      系统内置 23 条攻击链检测规则，涵盖数据库、网络、认证、容器、API 等常见安全场景。
      每条模式定义了攻击阶段序列和事件匹配条件。
    </AlertGuide>

    <div class="g-card">
      <div class="g-card-header">
        <div class="g-card-title"><el-icon><List /></el-icon> 攻击链模式列表</div>
      </div>

      <div v-if="loading" style="text-align:center;padding:40px">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
        <div style="margin-top:8px;color:var(--text-secondary)">加载中...</div>
      </div>

      <div v-else-if="error" style="text-align:center;padding:40px">
        <el-result icon="error" title="加载失败" :sub-title="error" />
      </div>

      <div v-else-if="patterns.length === 0" class="g-empty-state">
        <el-empty description="暂无攻击链模式数据" />
      </div>

      <el-table v-else :data="patterns" stripe style="width:100%" size="small">
        <el-table-column prop="name" label="模式名称" min-width="180">
          <template #default="{ row }">
            <code>{{ row.name }}</code>
          </template>
        </el-table-column>
        <el-table-column label="风险等级" width="100">
          <template #default="{ row }">
            <RiskBadge :level="getRiskKey(row.risk_level)" :label="row.risk_level" />
          </template>
        </el-table-column>
        <el-table-column label="匹配阶段" min-width="200">
          <template #default="{ row }">
            <div style="display:flex;gap:4px;flex-wrap:wrap">
              <el-tag v-for="(stage, idx) in row.stages" :key="idx" size="small">
                {{ stage }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="阶段数" width="70" align="center">
          <template #default="{ row }">
            {{ row.stages?.length || 0 }}
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Api } from '../../api'
import AlertGuide from '../../components/AlertGuide.vue'
import RiskBadge from '../../components/RiskBadge.vue'

defineProps<{ mode?: string }>()

const patterns = ref<any[]>([])
const loading = ref(true)
const error = ref('')

function getRiskKey(level: string): string {
  const map: Record<string, string> = {
    'P0_高危': 'P0', 'P1_中危': 'P1', 'P2_低危': 'P2', 'P3_低风险': 'P3',
    'critical': 'P0', 'major': 'P1', 'warning': 'P2',
  }
  return map[level] || 'normal'
}

async function loadPatterns() {
  loading.value = true
  error.value = ''
  try {
    const res = await Api.logCorrelate.patterns()
    if (res.success) {
      patterns.value = res.data?.patterns || []
    } else {
      error.value = res.msg || '获取模式列表失败'
    }
  } catch (err: any) {
    error.value = err.message || '网络错误'
  } finally {
    loading.value = false
  }
}

onMounted(loadPatterns)
</script>