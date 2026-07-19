<template>
  <div class="g-stack">
    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><SetUp /></el-icon> 脚本优化</div>
          <div class="g-card-desc">输入现有脚本，AI分析性能瓶颈并给出优化建议</div>
        </div>
        <el-button size="small" type="primary" plain @click="fillSample">填充示例</el-button>
      </div>
      <el-select v-model="scriptType" style="width:160px;margin-bottom:12px">
        <el-option v-for="t in typeOptions" :key="t.value" :label="t.label" :value="t.value" />
      </el-select>
      <el-input v-model="script" type="textarea" :rows="4" placeholder="粘贴待优化的脚本..." :disabled="loading" />
      <div class="g-actions" style="margin-top:12px"><el-button type="primary" @click="submit" :loading="loading">分析优化</el-button></div>
    </div>
    <div v-if="result" class="g-card slide">
      <div class="g-card-title" style="margin-bottom:12px"><el-icon><TrendCharts /></el-icon> 优化结果</div>
      <div v-if="result.issues" style="margin-bottom:16px">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">发现的问题</div>
        <div v-for="(issue,i) in result.issues" :key="i" class="g-alert g-alert--warning" style="margin-bottom:8px">{{ issue }}</div>
      </div>
      <CodeBlock :code="result.optimized||result.optimized_script" :lang="scriptType==='regex'?'python':'bash'" />
      <div v-if="result.explanation" style="margin-top:12px">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">优化说明</div>
        <div class="g-alert g-alert--success">{{ result.explanation }}</div>
      </div>
    </div>
    <div v-if="!result && !loading" class="g-card">
      <EmptyGuide title="粘贴待优化脚本" desc="AI将分析脚本性能瓶颈并给出优化建议" action-text="填充示例" @action="fillSample" />
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Api } from '../../api'
import CodeBlock from '../../components/CodeBlock.vue'
import EmptyGuide from '../../components/EmptyGuide.vue'
defineProps<{ mode?: string }>()
const script=ref(''); const scriptType=ref('regex'); const loading=ref(false); const result=ref<any>(null)
const typeOptions=[{label:'正则表达式',value:'regex'},{label:'ES查询',value:'es_query'},{label:'Shell脚本',value:'shell'}]
function fillSample(){script.value='.*Failed\\s+password\\s+for\\s+(invalid\\s+user\\s+)?(\\w+)\\s+from\\s+(\\d+\\.\\d+\\.\\d+\\.\\d+)\\s+port\\s+(\\d+).*';scriptType.value='regex'}
async function submit(){
  if(!script.value.trim()){ElMessage.warning('请输入待优化的脚本');return}
  loading.value=true;result.value=null
  try{const r=await Api.scriptGen.optimize({script:script.value,script_type:scriptType.value});if(r.success)result.value=r.data;else ElMessage.error(r.msg)}catch{ElMessage.error('请求失败')}
  finally{loading.value=false}
}
</script>