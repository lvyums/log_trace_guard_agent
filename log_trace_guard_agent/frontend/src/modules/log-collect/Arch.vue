<template>
  <div class="g-stack">
    <AlertGuide type="info" title="架构设计要考虑扩展性">
      当前方案基于当前规模，但安全设备会持续增加。建议：预留30%的采集容量，选择支持水平扩展的架构(如Kafka分层)，避免未来重构。
    </AlertGuide>
    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><Share /></el-icon> 架构推荐</div>
          <div class="g-card-desc">根据企业规模和设备情况，推荐最优日志采集架构方案</div>
        </div>
        <el-button size="small" type="primary" plain @click="fillExample">填充示例</el-button>
      </div>
      <el-form label-position="top" size="default">
        <el-form-item label="企业规模">
          <el-radio-group v-model="scale">
            <el-radio-button v-for="s in scaleOptions" :key="s.value" :value="s.value">{{ s.label }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="安全设备数量"><el-input-number v-model="deviceCount" :min="1" :max="10000" /></el-form-item>
        <el-form-item label="日均日志量">
          <el-select v-model="dailyLogVolume" style="width:100%"><el-option v-for="v in volumeOptions" :key="v.value" :label="v.label" :value="v.value" /></el-select>
        </el-form-item>
        <el-form-item label="预算水平">
          <el-select v-model="budget" style="width:100%"><el-option v-for="b in budgetOptions" :key="b.value" :label="b.label" :value="b.value" /></el-select>
        </el-form-item>
        <el-form-item label="运维能力">
          <el-select v-model="teamSkill" style="width:100%"><el-option v-for="s in skillOptions" :key="s.value" :label="s.label" :value="s.value" /></el-select>
        </el-form-item>
      </el-form>
      <div class="g-actions"><el-button type="primary" @click="submit" :loading="loading">推荐架构</el-button></div>
    </div>
    <div v-if="result" class="g-card slide">
      <div class="g-card-header"><div class="g-card-title"><el-icon><Share /></el-icon> 架构方案</div></div>
      <div v-if="result.recommended_arch" style="font-weight:600;font-size:15px;margin-bottom:12px">{{ result.recommended_arch }}</div>
      <div v-if="result.architecture_desc" style="color:var(--text-secondary);font-size:13px;margin-bottom:16px">{{ result.architecture_desc }}</div>
      <div v-if="result.components?.length" style="margin-bottom:16px">
        <SectionTitle>组件清单</SectionTitle>
        <ul style="font-size:13px;color:var(--text-secondary);padding-left:20px"><li v-for="(c,i) in result.components" :key="i">{{ c }}</li></ul>
      </div>
      <div v-if="result.data_flow?.length" style="margin-bottom:16px">
        <SectionTitle>数据流向</SectionTitle>
        <NumberedList :items="result.data_flow" />
      </div>
      <div v-if="result.estimated_cost"><span style="font-weight:600;font-size:13px">估算成本：</span><span style="font-size:13px;color:var(--text-secondary)">{{ result.estimated_cost }}</span></div>
    </div>
    <div v-if="!result && !loading" class="g-card">
      <EmptyGuide title="填写参数获取架构推荐" desc="根据企业规模和需求推荐最优日志采集架构" action-text="填充示例" @action="fillExample" />
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Api } from '../../api'
import AlertGuide from '../../components/AlertGuide.vue'
import EmptyGuide from '../../components/EmptyGuide.vue'
import SectionTitle from '../../components/SectionTitle.vue'
import NumberedList from '../../components/NumberedList.vue'
defineProps<{ mode?: string }>()
const scale=ref('small'); const deviceCount=ref(10); const dailyLogVolume=ref('small'); const budget=ref('low'); const teamSkill=ref('basic')
const loading=ref(false); const result=ref<any>(null)
const scaleOptions=[{label:'小型（<100人）',value:'small'},{label:'中型（100-1000人）',value:'medium'},{label:'大型（>1000人）',value:'large'}]
const volumeOptions=[{label:'小（<10GB/天）',value:'small'},{label:'中（10-100GB/天）',value:'medium'},{label:'大（>100GB/天）',value:'large'}]
const budgetOptions=[{label:'低预算',value:'low'},{label:'中等预算',value:'medium'},{label:'高预算',value:'high'}]
const skillOptions=[{label:'基础运维',value:'basic'},{label:'中级运维',value:'intermediate'},{label:'高级运维',value:'advanced'}]
function fillExample(){scale.value='medium';deviceCount.value=50;dailyLogVolume.value='medium';budget.value='medium';teamSkill.value='intermediate'}
async function submit(){
  loading.value=true;result.value=null
  try{const r=await Api.advisory.arch({device_count:deviceCount.value,daily_log_volume:dailyLogVolume.value,budget:budget.value,team_skill:teamSkill.value});if(r.success)result.value=r.data;else ElMessage.error(r.msg)}catch{ElMessage.error('请求失败')}
  finally{loading.value=false}
}
</script>