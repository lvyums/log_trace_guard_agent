<template>
  <div class="g-stack">
    <AlertGuide type="warning" title="自查结果不代表最终测评结论">
      本工具提供技术层面的合规检查，但等保测评还包含管理层面(制度、人员、流程)。技术自查通过≠测评通过。
    </AlertGuide>
    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><CircleCheck /></el-icon> 合规自查</div>
          <div class="g-card-desc">填写当前配置信息，检查是否满足合规要求</div>
        </div>
        <el-button size="small" type="primary" plain @click="fillSample">填充示例</el-button>
      </div>
      <el-form label-position="top" size="default">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="日志留存天数"><el-input-number v-model="form.log_retention_days" :min="1" :max="3650" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="设备数量"><el-input-number v-model="form.device_count" :min="1" :max="100000" style="width:100%" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="是否开启备份"><el-switch v-model="form.has_backup" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="备份频率"><el-select v-model="form.backup_frequency" style="width:100%"><el-option label="每天" value="daily" /><el-option label="每周" value="weekly" /><el-option label="每月" value="monthly" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="防篡改机制"><el-switch v-model="form.has_tamper_proof" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="审计机制"><el-switch v-model="form.has_audit_mechanism" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="NTP同步"><el-switch v-model="form.has_ntp" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="审计频率"><el-select v-model="form.audit_frequency" style="width:100%"><el-option label="每天" value="daily" /><el-option label="每周" value="weekly" /><el-option label="每月" value="monthly" /><el-option label="每季度" value="quarterly" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="告警系统"><el-switch v-model="form.has_alert_system" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="堡垒机"><el-switch v-model="form.has_bastion" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="补充描述（可选）"><el-input v-model="form.additional_info" type="textarea" :rows="2" placeholder="其他安全配置描述..." /></el-form-item>
      </el-form>
      <div class="g-actions"><el-button type="primary" @click="submit" :loading="loading">开始检查</el-button></div>
    </div>
    <div v-if="result" class="g-card slide">
      <div class="g-card-title" style="margin-bottom:12px"><el-icon><DataLine /></el-icon> 检查结果</div>
      <div v-if="result.summary" style="margin-bottom:16px;padding:12px;background:var(--bg-secondary);border-radius:6px;font-size:13px;line-height:1.8" v-html="renderSummary(result.summary)"></div>
      <div v-if="result.overall_score!=null" style="margin-bottom:16px;display:flex;align-items:center;gap:16px">
        <div style="font-size:32px;font-weight:700" :style="{color: result.overall_score>=80?'var(--risk-normal)':result.overall_score>=60?'var(--risk-p2)':'var(--risk-p0)'}">{{ result.overall_score }}</div>
        <div style="font-size:13px;color:var(--text-secondary)">合规评分（满分100）</div>
      </div>
      <div v-if="result.note" style="margin-bottom:16px">
        <el-alert :title="result.note" type="info" show-icon :closable="false" />
      </div>
      <el-descriptions :column="3" border size="small" style="margin-bottom:16px">
        <el-descriptions-item label="总检查项">{{ (result.gaps||[]).length }}</el-descriptions-item>
        <el-descriptions-item label="高风险"><span style="color:var(--risk-p0)">{{ result.critical_count||0 }}</span></el-descriptions-item>
        <el-descriptions-item label="中风险"><span style="color:var(--risk-p2)">{{ result.medium_count||0 }}</span></el-descriptions-item>
        <el-descriptions-item label="低风险"><span style="color:var(--risk-p3)">{{ result.low_count||0 }}</span></el-descriptions-item>
      </el-descriptions>
      <div v-if="result.gaps?.length">
        <div v-for="(gap,i) in result.gaps" :key="i" style="margin-bottom:12px;padding:12px;border:1px solid var(--border-color);border-radius:6px">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
            <RiskBadge :level="gap.risk_level==='high'?'P0':'P2'" :label="gap.risk_level==='high'?'高风险':'中风险'" />
            <span style="font-weight:500;font-size:13px">{{ gap.requirement }}</span>
            <span style="font-size:11px;color:var(--text-tertiary)">[{{ gap.standard_ref }}]</span>
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:6px">
            <el-tag v-if="gap.gap_id" size="small" type="info">{{ gap.gap_id }}</el-tag>
            <el-tag v-if="gap.priority" size="small" :type="gap.priority?.startsWith('P0')||gap.priority?.startsWith('P1')?'danger':'warning'">{{ gap.priority }}</el-tag>
          </div>
          <div style="font-size:12px;color:var(--text-secondary);margin-bottom:6px"><strong>当前状态：</strong>{{ gap.current_status }}</div>
          <div style="font-size:12px;color:var(--text-secondary);margin-bottom:6px"><strong>风险描述：</strong>{{ gap.risk_description }}</div>
          <div v-if="gap.remediation_steps?.length" style="margin-top:8px;padding:8px;background:var(--bg-tertiary);border-radius:4px">
            <div style="font-size:12px;font-weight:500;margin-bottom:4px">整改措施：</div>
            <div v-for="(step,j) in gap.remediation_steps" :key="j" style="font-size:12px;color:var(--text-secondary);margin-bottom:2px">{{ j+1 }}. {{ step }}</div>
          </div>
        </div>
      </div>
      <div v-if="result.llm_remediation" style="margin-top:16px">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">LLM 智能整改建议</div>
        <div style="padding:12px;background:var(--bg-tertiary);border-radius:6px;font-size:13px;line-height:1.8;white-space:pre-wrap">{{ result.llm_remediation }}</div>
      </div>
    </div>
    <div v-if="!result && !loading" class="g-card">
      <EmptyGuide title="填写配置信息" desc="检查当前配置是否满足合规要求" action-text="填充示例" @action="fillSample" />
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Api } from '../../api'
import AlertGuide from '../../components/AlertGuide.vue'
import RiskBadge from '../../components/RiskBadge.vue'
import EmptyGuide from '../../components/EmptyGuide.vue'
defineProps<{ mode?: string }>()
const form=reactive({log_retention_days:30,has_backup:false,has_tamper_proof:false,backup_frequency:'daily',device_count:10,has_audit_mechanism:false,has_ntp:true,audit_frequency:'monthly',has_alert_system:false,has_bastion:false,additional_info:''})
const loading=ref(false); const result=ref<any>(null)
function renderSummary(text){if(!text)return '';return text.replace(/\n/g,'<br>').replace(/🔴/g,'<span style="color:var(--risk-p0)">🔴</span>').replace(/🟡/g,'<span style="color:var(--risk-p2)">🟡</span>')}
function fillSample(){Object.assign(form,{log_retention_days:30,has_backup:false,has_tamper_proof:false,backup_frequency:'daily',device_count:20,has_audit_mechanism:true,has_ntp:true,audit_frequency:'weekly',has_alert_system:false,has_bastion:false,additional_info:'syslog日志无加密传输，管理员账户使用默认密码'})}
async function submit(){
  loading.value=true;result.value=null
  try{const r=await Api.compliance.check(form);if(r.success)result.value=r.data;else ElMessage.error(r.msg)}catch{ElMessage.error('请求失败')}
  finally{loading.value=false}
}
</script>