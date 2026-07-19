<template>
  <div class="g-stack">
    <div class="g-card">
      <div class="g-card-header">
        <div class="g-card-title"><el-icon><DataBoard /></el-icon> 实训报告</div>
        <div class="g-card-desc">查看实训统计与详细报告</div>
      </div>
      <el-form label-position="top" size="default">
        <el-form-item label="选择实训场景">
          <el-select v-model="selectedScenario" placeholder="选择场景" style="width:100%">
            <el-option v-for="s in scenarioOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="学员ID">
          <el-input v-model="studentId" placeholder="如: student_001" />
        </el-form-item>
      </el-form>
      <div class="g-actions">
        <el-button type="primary" @click="loadReport" :loading="loading">查看报告</el-button>
      </div>
    </div>
    <div v-if="report" class="g-card slide">
      <div class="g-card-header">
        <div class="g-card-title"><el-icon><DataLine /></el-icon> 报告详情</div>
      </div>
      <el-descriptions :column="2" border size="small" style="margin-bottom:16px">
        <el-descriptions-item label="场景名称">{{ report.scenario_name || selectedScenario }}</el-descriptions-item>
        <el-descriptions-item label="完成状态">{{ report.status || '-' }}</el-descriptions-item>
        <el-descriptions-item label="总分">{{ report.score ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="用时">{{ report.duration || '-' }}</el-descriptions-item>
      </el-descriptions>
      <div v-if="report.details?.length">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">详细得分</div>
        <div v-for="(item,i) in report.details" :key="i" style="margin-bottom:8px;padding:8px;border:1px solid var(--border-color);border-radius:4px">
          <div style="display:flex;justify-content:space-between;font-size:13px">
            <span>{{ item.field }}</span>
            <RiskBadge :level="item.score>=80?'normal':item.score>=60?'P2':'P0'" :label="item.score+'分'" />
          </div>
        </div>
      </div>
      <div v-if="report.summary" style="margin-top:12px;font-size:13px;color:var(--text-secondary);line-height:1.8;white-space:pre-wrap">{{ report.summary }}</div>
    </div>
    <div v-if="!report && !loading" class="g-card">
      <div style="text-align:center;padding:40px;color:var(--text-secondary)">
        <el-icon :size="48"><DataBoard /></el-icon>
        <div style="margin-top:8px">选择场景和学员ID，查看实训报告</div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Api } from '../../api'
import RiskBadge from '../../components/RiskBadge.vue'
defineProps<{ mode?: string }>()
const selectedScenario=ref('1'); const studentId=ref('student_default'); const loading=ref(false); const report=ref<any>(null)
const scenarioOptions=[
  {label:'SSH暴力破解检测',value:'1'},{label:'Web攻击日志分析',value:'2'},
  {label:'内网横向移动追踪',value:'3'},{label:'日志采集架构设计',value:'4'},{label:'合规基线检查',value:'5'},
]
async function loadReport(){
  loading.value=true;report.value=null
  try{const r=await Api.training.report({scenario_id:selectedScenario.value,student_id:studentId.value});if(r.success)report.value=r.data;else ElMessage.error(r.msg)}catch{ElMessage.error('请求失败')}
  finally{loading.value=false}
}
</script>