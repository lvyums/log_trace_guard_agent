<template>
  <div class="g-stack">
    <div class="g-alert g-alert--warning" style="padding:12px 16px;border-radius:6px;font-size:13px;margin-bottom:16px">
      <strong>故障诊断前先确认基础条件</strong><br>
      <span style="margin-top:4px;display:block">80%的采集故障是基础问题：①网络不通(ping目标IP) ②端口未开放(telnet IP 514) ③防火墙拦截(检查ACL)。先排除这三项再使用诊断工具。</span>
    </div>
    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><Warning /></el-icon> 故障诊断</div>
          <div class="g-card-desc">描述日志采集中的故障现象，AI诊断原因并给出修复方案</div>
        </div>
        <el-button size="small" type="primary" plain @click="fillExample">填充示例</el-button>
      </div>
      <el-input v-model="symptom" type="textarea" :rows="4" placeholder="描述故障现象，如：防火墙日志采集不通..." :disabled="loading" />
      <div class="g-input-guide"><el-icon><InfoFilled /></el-icon><span>描述越详细诊断越准确，建议包含：设备类型、协议、症状表现</span></div>
      <div style="margin-top:12px">
        <el-select v-model="deviceType" placeholder="设备类型（可选）" clearable size="small" style="width:200px">
          <el-option v-for="d in deviceOptions" :key="d" :label="d" :value="d" />
        </el-select>
      </div>
      <div class="g-actions" style="margin-top:12px"><el-button type="primary" @click="submit" :loading="loading">诊断</el-button></div>
    </div>
    <div v-if="result" class="g-card slide">
      <div class="g-card-header"><div class="g-card-title"><el-icon><FirstAidKit /></el-icon> 诊断结果</div></div>

      <!-- 故障概要 -->
      <div style="margin-bottom:16px">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="故障类型">
            <el-tag size="small" :type="result.fault_type ? '' : 'info'">{{ result.fault_type || '未识别' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="匹配度">
            <span :style="{color: result.match_score >= 70 ? 'var(--el-color-success)' : result.match_score >= 30 ? 'var(--el-color-warning)' : 'var(--el-color-danger)'}">
              {{ result.match_score || 0 }}%
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="严重程度">
            <RiskBadge :level="severityLevel(result.severity)" :label="result.severity || '未知'" size="small" />
          </el-descriptions-item>
        </el-descriptions>
        <div v-if="result.fault_desc" style="margin-top:8px;padding:8px 12px;background:var(--bg-secondary);border-radius:4px;font-size:13px;color:var(--text-secondary)">
          {{ result.fault_desc }}
        </div>
      </div>

      <!-- 可能原因 -->
      <div v-if="result.possible_causes?.length" style="margin-bottom:16px">
        <SectionTitle :icon="Warning">可能原因</SectionTitle>
        <div v-for="(cause,i) in result.possible_causes" :key="i" class="g-alert g-alert--warning" style="margin-bottom:8px">
          <span>{{ i+1 }}. {{ cause }}</span>
        </div>
      </div>

      <!-- 修复步骤 -->
      <div v-if="result.fix_steps" style="margin-bottom:16px">
        <SectionTitle :icon="Tools">修复步骤</SectionTitle>
        <CodeBlock :code="typeof result.fix_steps === 'string' ? result.fix_steps : result.fix_steps.join('\n')" lang="bash" />
      </div>

      <!-- 预防措施 -->
      <div v-if="result.prevention" style="margin-bottom:16px">
        <SectionTitle :icon="Lock">预防措施</SectionTitle>
        <div class="g-alert g-alert--info" style="margin:0">
          <span>{{ result.prevention }}</span>
        </div>
      </div>

      <!-- 候选匹配 -->
      <div v-if="result.candidates?.length" style="margin-bottom:16px">
        <SectionTitle :icon="Search">相似故障参考</SectionTitle>
        <div v-for="(c, i) in result.candidates" :key="i"
             style="padding:6px 10px;margin-bottom:4px;border:1px solid var(--border-color);border-radius:4px;font-size:12px;display:flex;justify-content:space-between;align-items:center">
          <span>{{ c.fault_type }}</span>
          <span>
            <el-tag size="small" :type="c.match_score >= 70 ? 'success' : c.match_score >= 30 ? 'warning' : 'danger'" effect="plain">
              匹配度 {{ c.match_score }}%
            </el-tag>
          </span>
        </div>
      </div>
    </div>
    <div v-if="!result && !loading" class="g-card">
      <EmptyGuide title="描述故障现象" desc="输入采集故障的症状，AI分析原因并给出修复方案" action-text="填充示例" @action="fillExample" />
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Warning, Tools, Lock, Search } from '@element-plus/icons-vue'
import { APP_CONFIG } from '../../config'
import { Api } from '../../api'
import CodeBlock from '../../components/CodeBlock.vue'
import EmptyGuide from '../../components/EmptyGuide.vue'
import RiskBadge from '../../components/RiskBadge.vue'
import SectionTitle from '../../components/SectionTitle.vue'
defineProps<{ mode?: string }>()
const symptom=ref(''); const deviceType=ref(''); const loading=ref(false); const result=ref<any>(null)
const deviceOptions=APP_CONFIG.sampleData.deviceTypes
function fillExample() { symptom.value='防火墙syslog日志采集不通，设备端已配置发送到10.0.0.100:514，但日志服务器未收到任何数据'; deviceType.value='firewall' }
function severityLevel(s: string) {
  if (!s) return 'normal'
  const m: Record<string,string> = {'严重':'P0','高':'P0','HIGH':'P0','中':'P1','MEDIUM':'P1','低':'P2','LOW':'P2','info':'normal'}
  return m[s] || 'normal'
}
async function submit() {
  if(!symptom.value.trim()){ElMessage.warning('请描述故障现象');return}
  loading.value=true; result.value=null
  try{const r=await Api.logCollect.fault({symptom:symptom.value,device_type:deviceType.value});if(r.success)result.value=r.data;else ElMessage.error(r.msg)}catch{ElMessage.error('请求失败')}
  finally{loading.value=false}
}
</script>
