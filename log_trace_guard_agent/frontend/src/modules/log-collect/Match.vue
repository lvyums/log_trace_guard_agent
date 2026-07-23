<template>
  <div class="g-stack">
    <AlertGuide type="info" title="设备匹配决定采集配置">
      选错设备类型会导致生成的配置无法使用。如果你不确定设备类型，先用「日志识别」分析一条该设备的日志。
    </AlertGuide>
    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><Monitor /></el-icon> 设备匹配</div>
          <div class="g-card-desc">输入设备信息，自动匹配采集协议与配置方案</div>
        </div>
        <el-button size="small" type="primary" plain @click="fillExample">填充示例</el-button>
      </div>
      <el-form label-position="top" size="default">
        <el-form-item label="设备类型">
          <el-select v-model="deviceType" placeholder="选择设备类型" style="width:100%">
            <el-option v-for="d in deviceOptions" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="设备型号（可选）">
          <el-input v-model="deviceModel" placeholder="如: Huawei USG6000, Cisco ASA 5500" />
        </el-form-item>
      </el-form>
      <div class="g-actions">
        <el-button type="primary" @click="submit" :loading="loading">匹配</el-button>
      </div>
    </div>
    <div v-if="result" class="g-card slide">
      <div class="g-card-header">
        <div class="g-card-title"><el-icon><Connection /></el-icon> 匹配结果</div>
      </div>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="设备类型">{{ result.device_info?.device_type || result.plan?.device_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="设备型号">{{ result.device_info?.model || result.plan?.device_model || '-' }}</el-descriptions-item>
        <el-descriptions-item label="设备厂商">{{ result.device_info?.vendor || '-' }}</el-descriptions-item>
        <el-descriptions-item label="采集协议">{{ result.plan?.protocol || '-' }}</el-descriptions-item>
        <el-descriptions-item label="采集架构">{{ result.plan?.architecture || '-' }}</el-descriptions-item>
        <el-descriptions-item label="匹配置信度">{{ result.match_confidence ? Math.round(result.match_confidence) + '%' : '-' }}</el-descriptions-item>
        <el-descriptions-item label="匹配来源">{{ result.match_source || '工厂匹配' }}</el-descriptions-item>
      </el-descriptions>
      <div v-if="result.low_confidence_note" style="margin-top:12px">
        <el-alert :title="result.low_confidence_note" type="warning" show-icon :closable="false" />
      </div>
      <div v-if="result.plan?.steps?.length" style="margin-top:16px">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">实施步骤</div>
        <div v-for="(step, i) in result.plan.steps" :key="i" style="display:flex;align-items:flex-start;gap:12px;margin-bottom:8px">
          <div style="width:24px;height:24px;border-radius:50%;background:var(--el-color-primary);color:#fff;display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0">{{ i+1 }}</div>
          <div style="flex:1;font-size:13px;color:var(--text-secondary)">{{ step }}</div>
        </div>
      </div>
      <div v-if="result.plan?.notes?.length" style="margin-top:12px">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">注意事项</div>
        <div v-for="(note, i) in result.plan.notes" :key="i" style="font-size:12px;color:var(--text-secondary);margin-bottom:4px;padding-left:12px;border-left:2px solid var(--el-color-warning)">{{ note }}</div>
      </div>
      <div v-if="result.plan?.config_template" style="margin-top:16px">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">配置模板</div>
        <CodeBlock :code="typeof result.plan.config_template === 'string' ? result.plan.config_template : JSON.stringify(result.plan.config_template, null, 2)" lang="bash" />
      </div>
      <div v-if="result.rag_supplements?.length || result.plan?.rag_supplements?.length" style="margin-top:16px">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">知识库补充</div>
        <div v-for="(s, i) in (result.rag_supplements || result.plan?.rag_supplements || [])" :key="i" style="font-size:12px;color:var(--text-secondary);margin-bottom:6px;padding:8px;background:var(--bg-tertiary);border-radius:4px">{{ s }}</div>
      </div>
    </div>
    <div v-if="!result && !loading" class="g-card">
      <EmptyGuide title="等待输入" desc="选择设备类型，点击匹配获取采集协议和配置方案" action-text="填充示例" @action="fillExample" />
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { APP_CONFIG } from '../../config'
import { Api } from '../../api'
import AlertGuide from '../../components/AlertGuide.vue'
import CodeBlock from '../../components/CodeBlock.vue'
import EmptyGuide from '../../components/EmptyGuide.vue'
defineProps<{ mode?: string }>()
const deviceType = ref('')
const deviceModel = ref('')
const loading = ref(false)
const result = ref<any>(null)
const deviceOptions = APP_CONFIG.sampleData.deviceTypes
function fillExample() { deviceType.value = 'firewall'; deviceModel.value = 'Huawei USG6000' }
async function submit() {
  if (!deviceType.value) { ElMessage.warning('请选择设备类型'); return }
  loading.value = true; result.value = null
  try { const res = await Api.logCollect.match({ device_type: deviceType.value, device_model: deviceModel.value }); if (res.success) result.value = res.data; else ElMessage.error(res.msg) } catch { ElMessage.error('请求失败') }
  finally { loading.value = false }
}
</script>