<template>
  <div class="g-stack">
    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><DataAnalysis /></el-icon> 平台选型</div>
          <div class="g-card-desc">描述需求，AI对比主流日志平台并推荐最佳选型</div>
        </div>
        <el-button size="small" type="primary" plain @click="fillSample">填充示例</el-button>
      </div>
      <el-input v-model="requirements" type="textarea" :rows="3" placeholder="描述日志平台需求..." :disabled="loading" />
      <div style="margin-top:12px;display:flex;gap:12px;flex-wrap:wrap">
        <el-input-number v-model="deviceCount" :min="1" :max="100000" placeholder="设备数量" style="width:160px" />
        <el-select v-model="dailyLogVolume" placeholder="日志量级" style="width:160px"><el-option v-for="v in volumeOptions" :key="v.value" :label="v.label" :value="v.value" /></el-select>
        <el-select v-model="budget" placeholder="预算" style="width:140px"><el-option v-for="b in budgetOptions" :key="b.value" :label="b.label" :value="b.value" /></el-select>
        <el-select v-model="teamSkill" placeholder="运维能力" style="width:140px"><el-option v-for="s in skillOptions" :key="s.value" :label="s.label" :value="s.value" /></el-select>
      </div>
      <div class="g-actions" style="margin-top:12px"><el-button type="primary" @click="submit" :loading="loading">对比选型</el-button></div>
    </div>
    <div v-if="result" class="g-card slide">
      <div class="g-card-title" style="margin-bottom:12px"><el-icon><TrendCharts /></el-icon> 选型对比</div>
      <div v-if="result.recommendation" class="g-alert g-alert--success" style="margin-bottom:12px">
        <el-icon><CircleCheckFilled /></el-icon><div><strong>推荐：</strong>{{ result.recommendation.name }} - {{ result.recommendation.type }}</div>
      </div>
      <div v-if="result.alternatives?.length">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">备选方案</div>
        <el-table :data="result.alternatives" border size="small">
          <el-table-column prop="name" label="平台" width="120" />
          <el-table-column prop="type" label="类型" width="100" />
          <el-table-column label="优势" width="180"><template #default="{row}"><span v-for="(p,i) in (row.pros||[]).slice(0,2)" :key="i">{{ p }}{{ i<1 ? '; ' : '' }}</span></template></el-table-column>
          <el-table-column label="劣势" width="180"><template #default="{row}"><span v-for="(c,i) in (row.cons||[]).slice(0,2)" :key="i">{{ c }}{{ i<1 ? '; ' : '' }}</span></template></el-table-column>
        </el-table>
      </div>
      <div v-if="result.summary" style="margin-top:12px;font-size:13px;color:var(--text-secondary)">{{ result.summary }}</div>
    </div>
    <div v-if="!result && !loading" class="g-card">
      <EmptyGuide title="描述平台需求" desc="AI将对比主流日志平台并推荐最佳选型" action-text="填充示例" @action="fillSample" />
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Api } from '../../api'
import AlertGuide from '../../components/AlertGuide.vue'
import EmptyGuide from '../../components/EmptyGuide.vue'
defineProps<{ mode?: string }>()
const requirements=ref(''); const deviceCount=ref(50); const dailyLogVolume=ref('medium'); const budget=ref('medium'); const teamSkill=ref('basic')
const loading=ref(false); const result=ref<any>(null)
const volumeOptions=[{label:'小（<10GB/天）',value:'small'},{label:'中（10-100GB/天）',value:'medium'},{label:'大（>100GB/天）',value:'large'}]
const budgetOptions=[{label:'低预算',value:'low'},{label:'中等预算',value:'medium'},{label:'高预算',value:'high'}]
const skillOptions=[{label:'基础运维',value:'basic'},{label:'中级运维',value:'intermediate'},{label:'高级运维',value:'advanced'}]
function fillSample(){requirements.value='需要支持syslog采集、全文检索、告警规则、可视化报表，日均日志量约5GB';deviceCount.value=50;dailyLogVolume.value='medium';budget.value='medium';teamSkill.value='intermediate'}
async function submit(){
  if(!requirements.value.trim()){ElMessage.warning('请描述需求');return}
  loading.value=true;result.value=null
  try{const r=await Api.scriptGen.platform({device_count:deviceCount.value,daily_log_volume:dailyLogVolume.value,budget:budget.value,team_skill:teamSkill.value,requirements:[requirements.value]});if(r.success)result.value=r.data;else ElMessage.error(r.msg)}catch{ElMessage.error('请求失败')}
  finally{loading.value=false}
}
</script>