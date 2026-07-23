<template>
  <div class="g-stack">
    <AlertGuide type="info" title="ES查询用于安全事件检索">
      生成的DSL可直接在Kibana Dev Tools中执行。大规模检索时使用scroll API避免超时。
    </AlertGuide>
    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><Search /></el-icon> ES 查询生成</div>
          <div class="g-card-desc">用自然语言描述查询需求，自动生成 Elasticsearch 查询语句</div>
        </div>
        <el-button size="small" type="primary" plain @click="fillSample">填充示例</el-button>
      </div>
      <el-input v-model="description" type="textarea" :rows="3" placeholder="用自然语言描述你要查询的内容..." :disabled="loading" />
      <div class="g-input-guide"><el-icon><InfoFilled /></el-icon><span>描述越详细生成越精准，可包含：时间范围、字段条件、排序方式</span></div>
      <el-input v-model="indexPattern" placeholder="索引模式（可选）：如 logstash-*" style="margin-top:12px" :disabled="loading" />
      <div class="g-actions" style="margin-top:12px"><el-button type="primary" @click="submit" :loading="loading">生成查询</el-button></div>
    </div>
    <div v-if="result" class="g-card slide">
      <div class="g-card-title" style="margin-bottom:12px"><el-icon><Monitor /></el-icon> ES 查询语句</div>
      <CodeBlock :code="result.query" lang="json" />
    </div>
    <div v-if="!result && !loading" class="g-card">
      <EmptyGuide title="描述查询需求" desc="用自然语言描述查询条件，AI生成ES查询DSL" action-text="填充示例" @action="fillSample" />
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Api } from '../../api'
import AlertGuide from '../../components/AlertGuide.vue'
import CodeBlock from '../../components/CodeBlock.vue'
import EmptyGuide from '../../components/EmptyGuide.vue'
defineProps<{ mode?: string }>()
const description=ref(''); const indexPattern=ref(''); const loading=ref(false); const result=ref<any>(null)
function fillSample(){description.value='查询最近1小时内来源IP为192.168.1.x网段的SSH登录失败事件，按时间倒序，返回前50条';indexPattern.value='logstash-ssh-*'}
async function submit(){
  if(!description.value.trim()){ElMessage.warning('请描述查询需求');return}
  loading.value=true;result.value=null
  try{const r=await Api.scriptGen.esQuery({search_scenario:description.value,index_pattern:indexPattern.value,time_range:'',filters:{}});if(r.success)result.value=r.data;else ElMessage.error(r.msg)}catch{ElMessage.error('请求失败')}
  finally{loading.value=false}
}
</script>