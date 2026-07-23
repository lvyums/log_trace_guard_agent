<template>
  <div class="g-stack">
    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><Grid /></el-icon> 批量解析</div>
          <div class="g-card-desc">批量上传日志文件或粘贴多条日志进行解析分析</div>
        </div>
        <el-button size="small" type="primary" plain @click="fillSample">填充测试日志</el-button>
      </div>
      <el-input v-model="input" type="textarea" :rows="8" placeholder="粘贴日志内容，每行一条..." :disabled="loading" />
      <div class="g-input-guide"><el-icon><InfoFilled /></el-icon><span>共 {{ totalCount }} 条日志，支持 Ctrl+Enter 快速提交</span></div>
      <div style="margin-top:12px">
        <el-checkbox v-model="doAssess">同时进行风险研判</el-checkbox>
      </div>
      <div class="g-actions" style="margin-top:12px">
        <el-button type="primary" :loading="loading" :disabled="!input.trim()" @click="submit">
          <el-icon><Search /></el-icon> 批量解析
        </el-button>
        <el-button :disabled="loading" @click="clear">清空</el-button>
      </div>
    </div>
    <div v-if="result" class="g-card slide">
      <div class="g-card-header"><div class="g-card-title"><el-icon><Document /></el-icon> 解析结果</div></div>
      <el-descriptions :column="3" border size="small" style="margin-bottom:16px">
        <el-descriptions-item label="总条数">{{ result.total || result.items?.length || 0 }}</el-descriptions-item>
        <el-descriptions-item label="成功">{{ result.success_count || result.items?.filter(i=>!i.error).length || 0 }}</el-descriptions-item>
        <el-descriptions-item label="失败">{{ result.fail_count || result.items?.filter(i=>i.error).length || 0 }}</el-descriptions-item>
      </el-descriptions>
      <div v-if="result.risk_summary" style="margin-bottom:12px">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">风险统计</div>
        <div v-for="(count, level) in result.risk_summary" :key="level" style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
          <RiskBadge :level="getLevelKey(level)" :label="level" size="small" />
          <span style="font-size:13px">{{ count }} 条</span>
        </div>
      </div>
      <div v-if="result.items?.length">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">逐条结果</div>
        <div v-for="(item,i) in result.items" :key="i" style="margin-bottom:8px;padding:8px;border:1px solid var(--border-color);border-radius:4px">
          <div style="font-size:12px;color:var(--text-tertiary);margin-bottom:4px">#{{ i+1 }} {{ item.log_line?.slice(0,60) || '' }}</div>
          <div v-if="item.error" class="g-alert g-alert--danger" style="margin:0">{{ item.error }}</div>
          <div v-else style="font-size:12px">
            <el-tag size="small">{{ item.parse_result?.device_type || '未知' }}</el-tag>
            <RiskBadge v-if="item.risk_result?.risk_level" :level="getLevelKey(item.risk_result.risk_level)" :label="item.risk_result.risk_level" size="small" />
            <span v-if="item.parse_result?.user" style="margin-left:8px;color:var(--text-secondary)">用户: {{ item.parse_result.user }}</span>
            <span v-if="item.parse_result?.src_ip" style="margin-left:8px;color:var(--text-secondary)">源IP: {{ item.parse_result.src_ip }}</span>
            <div v-if="item.risk_result" style="margin-top:4px;padding:6px 8px;background:var(--bg-secondary);border-radius:4px;line-height:1.6">
              <div v-if="item.risk_result.risk_desc" style="color:var(--text-secondary)">
                <el-icon style="margin-right:4px;vertical-align:middle"><Warning /></el-icon>
                <span>{{ item.risk_result.risk_desc }}</span>
              </div>
              <div v-if="item.risk_result.attack_type" style="margin-top:2px;color:var(--text-secondary)">
                <el-icon style="margin-right:4px;vertical-align:middle"><SoldOut /></el-icon>
                <span>攻击类型: {{ item.risk_result.attack_type }}</span>
              </div>
              <div v-if="item.risk_result.suggestion" style="margin-top:2px;color:var(--el-color-primary)">
                <el-icon style="margin-right:4px;vertical-align:middle"><ChatLineSquare /></el-icon>
                <span>{{ item.risk_result.suggestion }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-if="!result && !loading" class="g-card">
      <EmptyGuide title="批量解析" desc="粘贴多条日志或上传文件进行批量解析" action-text="填充测试日志" @action="fillSample" />
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { APP_CONFIG } from '../../config'
import { Api } from '../../api'
import RiskBadge from '../../components/RiskBadge.vue'
import EmptyGuide from '../../components/EmptyGuide.vue'
defineProps<{ mode?: string }>()
const input=ref(''); const doAssess=ref(true); const loading=ref(false); const result=ref<any>(null)
const totalCount=computed(()=>input.value.trim()?input.value.split('\n').filter(l=>l.trim()).length:0)
const sampleLogs=APP_CONFIG?.sampleData?.logs?.join('\n')||''
function fillSample(){input.value=sampleLogs}
function clear(){input.value='';result.value=null}
function getLevelKey(l){const m={'P0_高危':'P0','P1_中危':'P1','P2_低危':'P2','P3_噪音':'P3','P0':'P0','P1':'P1','P2':'P2','P3':'P3'};return m[l]||'normal'}
async function submit(){
  if(!input.value.trim()){ElMessage.warning('请输入日志内容');return}
  loading.value=true;result.value=null
  try{const lines=input.value.split('\n').filter(l=>l.trim());const r=await Api.logParse.batch({logs:lines,assess:doAssess.value});if(r.success)result.value=r.data;else ElMessage.error(r.msg)}catch{ElMessage.error('请求失败')}
  finally{loading.value=false}
}
</script>