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

      <!-- Attack stage & entry point -->
      <el-descriptions :column="2" border size="small" style="margin-bottom:16px">
        <el-descriptions-item label="攻击阶段">
          <el-tag :type="result.attack_stage==='入侵成功'?'danger':result.attack_stage==='横向移动'?'warning':'info'" size="small">{{ result.attack_stage || '未知' }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="攻击入口">{{ result.entry_point || '未知' }}</el-descriptions-item>
      </el-descriptions>

      <!-- Affected assets -->
      <div v-if="result.affected_assets?.length" style="margin-bottom:16px">
        <div style="font-weight:600;margin-bottom:6px;font-size:13px">受影响资产</div>
        <el-tag v-for="(asset,i) in result.affected_assets" :key="i" type="danger" size="small" style="margin-right:6px;margin-bottom:4px">{{ asset }}</el-tag>
      </div>

      <!-- Attack chain events -->
      <div v-if="result.attack_chain?.length" style="margin-bottom:16px">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">攻击链路</div>
        <div v-for="(event,i) in result.attack_chain" :key="i" class="g-alert g-alert--info" style="margin-bottom:10px;padding:10px 12px">
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px">
            <span style="font-weight:600;font-size:13px;min-width:48px">Step {{i+1}}</span>
            <el-tag size="small" type="primary" effect="plain">{{ event.event_type || '事件' }}</el-tag>
            <RiskBadge v-if="event.risk_level" :level="event.risk_level" :label="event.risk_level" size="small" />
            <span v-if="event.timestamp" style="font-size:12px;color:var(--text-tertiary);margin-left:auto">{{ event.timestamp }}</span>
          </div>
          <div style="font-size:13px">{{ event.action }} — {{ event.source }}<span v-if="event.target"> → {{ event.target }}</span></div>
          <div v-if="event.detail" style="font-size:12px;color:var(--text-tertiary);margin-top:4px">{{ event.detail }}</div>
        </div>
      </div>

      <!-- Summary -->
      <div v-if="result.summary" style="font-size:13px;color:var(--text-secondary);margin-bottom:8px"><strong>总结：</strong>{{ result.summary }}</div>
      <div v-if="result.scripts?.length">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">溯源检索脚本</div>
        <div v-for="(script,i) in result.scripts" :key="i" style="margin-bottom:16px">
          <div style="font-size:13px;font-weight:500;margin-bottom:4px">{{ script.name }}</div>
          <div style="font-size:12px;color:var(--text-secondary);margin-bottom:6px">{{ script.description }}</div>
          <CodeBlock :code="script.code" :lang="script.lang" />
          <!-- Splunk SPL 脚本的交互按钮 -->
          <div v-if="script.lang === 'spl'" style="display:flex;gap:8px;margin-top:8px">
            <el-tooltip :disabled="hasSplunkConfig" content="请先在导航栏设置中配置 Splunk" placement="top">
              <el-button size="small" type="primary" :loading="splunkLoading" :disabled="!hasSplunkConfig" @click="executeSplunk(script.code)">
                <el-icon><VideoPlay /></el-icon> 执行查询
              </el-button>
            </el-tooltip>
            <el-tooltip :disabled="hasSplunkConfig" content="请先在导航栏设置中配置 Splunk" placement="top">
              <el-button size="small" plain :disabled="!hasSplunkConfig" @click="openSplunk(script.code)">
                <el-icon><Link /></el-icon> 在 Splunk 中打开
              </el-button>
            </el-tooltip>
          </div>
        </div>
      </div>

      <!-- Splunk 查询结果 -->
      <div v-if="splunkResult" class="g-card" style="margin-top:12px;border:1px solid var(--el-border-color-light)">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
          <div style="font-weight:600;font-size:13px"><el-icon><Monitor /></el-icon> Splunk 查询结果</div>
          <el-button size="small" text @click="splunkResult=null">关闭</el-button>
        </div>
        <el-table :data="splunkResult.results" border size="small" max-height="400" style="width:100%">
          <el-table-column v-for="(_, key) in splunkResult.results[0] || {}" :key="key" :prop="key" :label="key" min-width="120" show-overflow-tooltip />
        </el-table>
        <div style="font-size:12px;color:var(--text-tertiary);margin-top:8px">
          共 {{ splunkResult.event_count }} 条结果，耗时 {{ splunkResult.execution_time }}s
        </div>
        <!-- ★ 回流按钮：Splunk 结果送到关联分析再分析 -->
        <div style="margin-top:10px;display:flex;gap:8px;border-top:1px solid var(--el-border-color-light);padding-top:10px">
          <el-button size="small" type="primary" @click="sendToCorrelate">
            <el-icon><Connection /></el-icon> 送到关联分析再分析
          </el-button>
          <span style="font-size:12px;color:var(--text-tertiary);line-height:32px">
            将 Splunk 查到的日志送日志联合审查模块重新分析，发现更深层攻击链
          </span>
        </div>
      </div>
    </div>
    <div v-if="!result && !loading" class="g-card">
      <EmptyGuide title="输入攻击线索" desc="输入攻击类型和相关日志，AI生成溯源检索脚本" action-text="填充示例" @action="fillSample" />
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Api } from '../../api'
import { getSplunkConfig } from '../../utils/splunk'
import { sendToCorrelate as storeSendToCorrelate } from '../../utils/crossModuleStore'
import AlertGuide from '../../components/AlertGuide.vue'
import EmptyGuide from '../../components/EmptyGuide.vue'
import CodeBlock from '../../components/CodeBlock.vue'
import RiskBadge from '../../components/RiskBadge.vue'
defineProps<{ mode?: string }>()
const attackType=ref(''); const targetIp=ref(''); const timeRange=ref(''); const logs=ref(''); const loading=ref(false); const result=ref<any>(null)
const splunkLoading=ref(false); const splunkResult=ref<any>(null)
const hasSplunkConfig = computed(() => !!getSplunkConfig())
function fillSample(){attackType.value='SSH暴力破解';targetIp.value='192.168.1.50';timeRange.value='2024-01-05 10:00 ~ 2024-01-05 14:00';logs.value='<22>Jan  5 12:34:56 sshd[12345]: Failed password for root from 192.168.1.100 port 22'}
async function submit(){
  if(!attackType.value.trim()){ElMessage.warning('请描述攻击类型');return}
  if(!logs.value.trim()){ElMessage.warning('请输入日志内容');return}
  loading.value=true;result.value=null;splunkResult.value=null
  try{const tp=timeRange.value?timeRange.value.split('~').map(s=>s.trim()):[];const r=await Api.scriptGen.trace({attack_type:attackType.value,logs:logs.value.split('\n').map(l=>l.trim()).filter(l=>l),start_time:tp[0]||'',end_time:tp[1]||''});if(r.success)result.value=r.data;else ElMessage.error(r.msg)}catch{ElMessage.error('请求失败')}
  finally{loading.value=false}
}
async function executeSplunk(spl: string){
  const cfg=getSplunkConfig();if(!cfg){ElMessage.warning('请先在导航栏设置中配置 Splunk');return}
  splunkLoading.value=true;splunkResult.value=null
  try{const r=await Api.scriptGen.splunkSearch({spl_query:spl,splunk_config:cfg});if(r.success)splunkResult.value=r.data;else ElMessage.error(r.msg||'Splunk 查询失败')}catch{ElMessage.error('Splunk 请求失败')}
  finally{splunkLoading.value=false}
}
async function openSplunk(spl: string){
  const cfg=getSplunkConfig();if(!cfg){ElMessage.warning('请先在导航栏设置中配置 Splunk');return}
  try{const r=await Api.scriptGen.splunkOpenUrl({spl_query:spl,splunk_config:cfg});if(r.success&&r.data?.open_url)window.open(r.data.open_url,'_blank');else ElMessage.error(r.msg||'无法生成 Splunk 链接')}catch{ElMessage.error('请求失败')}
}
// ★ 回流：Splunk 查询结果 → 关联分析
function sendToCorrelate() {
  if (!splunkResult.value?.results?.length) {
    ElMessage.warning('没有可分析的 Splunk 结果')
    return
  }
  // 把 Splunk 结果转回日志行格式
  const newLogs: string[] = []
  for (const row of splunkResult.value.results) {
    // 优先取 _raw 字段（Splunk 原始日志）
    if (row._raw && typeof row._raw === 'string') {
      newLogs.push(row._raw)
      continue
    }
    // 无 _raw 则拼接所有非空字段
    const parts = Object.values(row)
      .filter(v => v != null && v !== '')
      .map(v => String(v))
    if (parts.length) {
      newLogs.push(parts.join(' | '))
    }
  }
  // 合并用户输入的原始日志
  const allLogs = [
    ...logs.value.split('\n').map(l => l.trim()).filter(l => l),
    ...newLogs,
  ]
  if (!allLogs.length) {
    ElMessage.warning('没有可分析的日志')
    return
  }
  storeSendToCorrelate({
    logs: allLogs,
    source: 'trace-splunk',
    chainName: attackType.value || '',
  })
  window.location.hash = '#/log-correlate/analyze'
  ElMessage.success(`已发送 ${allLogs.length} 条日志到关联分析`)
}
</script>
