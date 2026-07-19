<template>
  <div class="g-stack">
    <AlertGuide type="info" title="合规问答基于最新法规标准">
      知识库涵盖：等保2.0(GB/T 22239-2019)、网安法、数据安全法、行业规范。问题越具体，回答越精准。
    </AlertGuide>
    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><ChatDotRound /></el-icon> 合规问答</div>
          <div class="g-card-desc">关于等保2.0、网安法、数据安全法等合规问题的智能解答</div>
        </div>
        <el-button size="small" type="primary" plain @click="fillSample">填充示例</el-button>
      </div>
      <div style="display:flex;gap:8px">
        <el-input v-model="question" placeholder="输入合规相关问题..." :disabled="loading" @keyup.enter="submit" style="flex:1" />
        <el-button type="primary" @click="submit" :loading="loading">提问</el-button>
      </div>
      <div class="g-input-guide"><el-icon><InfoFilled /></el-icon><span>支持等保2.0、网安法、数据安全法、行业合规标准等问题</span></div>
    </div>
    <div v-if="history.length" style="display:flex;flex-direction:column;gap:12px">
      <div v-for="(item,i) in history" :key="i" class="g-card slide">
        <div style="margin-bottom:12px"><div style="font-size:12px;color:var(--text-tertiary);margin-bottom:4px">问题</div><div style="font-size:13px;color:var(--text-primary)">{{ item.q }}</div></div>
        <div class="g-divider" style="margin:8px 0"></div>
        <div><div style="font-size:12px;color:var(--text-tertiary);margin-bottom:4px">回答</div><div style="font-size:13px;color:var(--text-secondary);line-height:1.8;white-space:pre-wrap">{{ typeof item.a === 'string' ? item.a : JSON.stringify(item.a,null,2) }}</div></div>
      </div>
    </div>
    <div v-if="!history.length && !loading" class="g-card">
      <EmptyGuide title="暂无问答记录" desc="输入合规相关问题开始咨询" action-text="查看示例问题" @action="fillSample" />
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
const question=ref(''); const loading=ref(false); const result=ref<any>(null); const history=ref<any[]>([])
function fillSample(){question.value='等保2.0三级对日志留存有什么要求？'}
async function submit(){
  if(!question.value.trim()){ElMessage.warning('请输入问题');return}
  loading.value=true
  try{const r=await Api.compliance.qa({question:question.value});if(r.success){history.value.push({q:question.value,a:r.data.answer||r.data});result.value=r.data}else ElMessage.error(r.msg)}catch{ElMessage.error('请求失败')}
  finally{loading.value=false;question.value=''}
}
</script>