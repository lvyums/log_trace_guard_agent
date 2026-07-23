<template>
  <div class="g-stack">
    <AlertGuide type="info" title="正则表达式用于日志批量检索">
      生成的正则可用于：SIEM告警规则、ELK的grok解析、Python日志分析脚本、grep命令行检索。
    </AlertGuide>
    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><MagicStick /></el-icon> 正则表达式生成</div>
          <div class="g-card-desc">粘贴日志样本，AI自动生成匹配正则表达式</div>
        </div>
        <el-button size="small" type="primary" plain @click="fillSample">填充测试日志</el-button>
      </div>
      <el-input v-model="input" type="textarea" :rows="3" placeholder="粘贴日志样本..." :disabled="loading" />
      <div class="g-input-guide"><el-icon><InfoFilled /></el-icon><span>粘贴一条典型日志，AI将分析其结构并生成正则</span></div>
      <el-input v-model="purpose" placeholder="提取目的（可选）：如提取用户名、IP地址" style="margin-top:12px" :disabled="loading" />
      <div class="g-actions" style="margin-top:12px"><el-button type="primary" @click="submit" :loading="loading">生成正则</el-button></div>
    </div>
    <div v-if="result" class="g-card slide">
      <div class="g-card-title" style="margin-bottom:12px"><el-icon><Finished /></el-icon> 生成结果</div>
      <div v-if="result.regexes?.length">
        <div v-for="(r,i) in result.regexes" :key="i" style="margin-bottom:16px">
          <div style="font-weight:600;font-size:13px;margin-bottom:6px">{{ r.name || '正则 '+(i+1) }}</div>
          <CodeBlock :code="r.pattern" lang="regex" />
          <div v-if="r.description" style="font-size:12px;color:var(--text-secondary);margin-top:4px">{{ r.description }}</div>
        </div>
      </div>
      <div v-else><CodeBlock :code="result.note || '无匹配规则'" lang="text" /></div>
    </div>
    <div v-if="!result && !loading" class="g-card">
      <EmptyGuide title="粘贴日志样本" desc="AI将分析日志结构并生成匹配正则表达式" action-text="填充测试日志" @action="fillSample" />
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
const input=ref(''); const purpose=ref(''); const loading=ref(false); const result=ref<any>(null)
function fillSample(){input.value='<22>Jan  5 12:34:56 web-server sshd[12345]: Failed password for invalid user admin from 192.168.1.100 port 22 ssh2';purpose.value='提取用户名、源IP、失败原因'}
async function submit(){
  if(!input.value.trim()){ElMessage.warning('请输入日志样本');return}
  loading.value=true;result.value=null
  try{const r=await Api.scriptGen.regex({scenario:purpose.value||input.value,log_sample:input.value,device_type:''});if(r.success)result.value=r.data;else ElMessage.error(r.msg)}catch{ElMessage.error('请求失败')}
  finally{loading.value=false}
}
</script>