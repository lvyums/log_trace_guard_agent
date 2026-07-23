<template>
  <div class="g-stack">
    <AlertGuide type="danger" title="攻击溯源是应急响应的关键环节">
      溯源需要跨多个日志源关联分析。生成的脚本会自动关联：登录日志→进程创建→文件变更→网络连接，还原完整攻击链。
    </AlertGuide>
    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><Connection /></el-icon> 攻击溯源</div>
          <div class="g-card-desc">输入攻击线索和日志，生成攻击链溯源检索脚本</div>
        </div>
        <el-button size="small" type="primary" plain @click="fillSample">填充示例</el-button>
      </div>
      <el-form label-position="top" size="default">
        <el-form-item label="攻击类型"><el-input v-model="attackType" placeholder="如：SSH暴力破解、SQL注入、Webshell上传" :disabled="loading" /></el-form-item>
        <el-form-item label="目标IP（可选）"><el-input v-model="targetIp" placeholder="被攻击的目标IP" :disabled="loading" /></el-form-item>
        <el-form-item label="时间范围（可选）"><el-input v-model="timeRange" placeholder="如：2024-01-05 10:00 ~ 2024-01-05 14:00" :disabled="loading" /></el-form-item>
        <el-form-item label="日志内容"><el-input v-model="logs" type="textarea" :rows="4" placeholder="粘贴相关日志，每行一条..." :disabled="loading" /></el-form-item>
      </el-form>
      <div class="g-actions"><el-button type="primary" @click="submit" :loading="loading">生成溯源脚本</el-button></div>
    </div>
    <div v-if="result" class="g-card slide">
      <div class="g-card-title" style="margin-bottom:12px"><el-icon><Tickets /></el-icon> 溯源结果</div>
      <div v-if="result.attack_chain?.length" style="margin-bottom:16px">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">攻击链路</div>
        <div v-for="(event,i) in result.attack_chain" :key="i" class="g-alert g-alert--info" style="margin-bottom:8px">
          <span>Step {{i+1}}: {{ event.action }} — {{ event.source }} → {{ event.target||'未知' }}</span>
        </div>
      </div>
      <div v-if="result.summary" style="font-size:13px;color:var(--text-secondary);margin-bottom:8px"><strong>总结：</strong>{{ result.summary }}</div>
      <div v-if="result.entry_point" style="font-size:13px;color:var(--text-tertiary);margin-bottom:16px"><strong>攻击入口：</strong>{{ result.entry_point }}</div>
      <div v-if="result.scripts?.length">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">溯源检索脚本</div>
        <div v-for="(script,i) in result.scripts" :key="i" style="margin-bottom:16px">
          <div style="font-size:13px;font-weight:500;margin-bottom:4px">{{ script.name }}</div>
          <div style="font-size:12px;color:var(--text-secondary);margin-bottom:6px">{{ script.description }}</div>
          <CodeBlock :code="script.code" :lang="script.lang" />
        </div>
      </div>
    </div>
    <div v-if="!result && !loading" class="g-card">
      <EmptyGuide title="输入攻击线索" desc="输入攻击类型和相关日志，AI生成溯源检索脚本" action-text="填充示例" @action="fillSample" />
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Api } from '../../api'
import AlertGuide from '../../components/AlertGuide.vue'
import EmptyGuide from '../../components/EmptyGuide.vue'
import CodeBlock from '../../components/CodeBlock.vue'
defineProps<{ mode?: string }>()
const attackType=ref(''); const targetIp=ref(''); const timeRange=ref(''); const logs=ref(''); const loading=ref(false); const result=ref<any>(null)
function fillSample(){attackType.value='SSH暴力破解';targetIp.value='192.168.1.50';timeRange.value='2024-01-05 10:00 ~ 2024-01-05 14:00';logs.value='<22>Jan  5 12:34:56 sshd[12345]: Failed password for root from 192.168.1.100 port 22'}
async function submit(){
  if(!attackType.value.trim()){ElMessage.warning('请描述攻击类型');return}
  if(!logs.value.trim()){ElMessage.warning('请输入日志内容');return}
  loading.value=true;result.value=null
  try{const tp=timeRange.value?timeRange.value.split('~').map(s=>s.trim()):[];const r=await Api.scriptGen.trace({attack_type:attackType.value,logs:logs.value.split('\n').map(l=>l.trim()).filter(l=>l),start_time:tp[0]||'',end_time:tp[1]||''});if(r.success)result.value=r.data;else ElMessage.error(r.msg)}catch{ElMessage.error('请求失败')}
  finally{loading.value=false}
}
</script>