<template>
  <div class="g-stack">
    <AlertGuide type="warning" title="采集方案必须满足等保要求">
      等保2.0明确要求：日志留存≥180天、传输加密、覆盖所有安全设备。生成方案后请逐项核对是否满足合规要求。
    </AlertGuide>
    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><Document /></el-icon> 采集方案生成</div>
          <div class="g-card-desc">根据设备类型和企业规模，生成标准化的日志采集配置方案</div>
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
          <el-input v-model="deviceModel" placeholder="具体型号可提高方案精准度" />
        </el-form-item>
        <el-form-item label="企业规模">
          <el-radio-group v-model="scale">
            <el-radio-button v-for="s in scaleOptions" :key="s.value" :value="s.value">{{ s.label }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <div class="g-actions">
        <el-button type="primary" @click="submit" :loading="loading">生成方案</el-button>
      </div>
    </div>
    <div v-if="result" class="g-card slide">
      <div class="g-card-header"><div class="g-card-title"><el-icon><Document /></el-icon> 采集方案</div></div>
      <div style="font-weight:600;font-size:15px;margin-bottom:12px">{{ result.device_type }} 采集方案</div>
      <el-descriptions :column="2" border size="small" style="margin-bottom:16px">
        <el-descriptions-item label="设备型号">{{ result.device_model || '-' }}</el-descriptions-item>
        <el-descriptions-item label="采集协议">{{ result.protocol || '-' }}</el-descriptions-item>
        <el-descriptions-item label="采集架构">{{ result.architecture || '-' }}</el-descriptions-item>
      </el-descriptions>
      <div v-if="result.steps?.length" style="margin-bottom:16px">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">实施步骤</div>
        <div v-for="(step, i) in result.steps" :key="i" style="display:flex;align-items:flex-start;gap:12px;margin-bottom:8px">
          <div style="width:24px;height:24px;border-radius:50%;background:var(--el-color-primary);color:#fff;display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0">{{ i+1 }}</div>
          <div style="flex:1;font-size:13px;color:var(--text-secondary)">{{ step }}</div>
        </div>
      </div>
      <div v-if="result.notes?.length" style="margin-bottom:16px">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">注意事项</div>
        <div v-for="(note, i) in result.notes" :key="i" style="font-size:12px;color:var(--text-secondary);margin-bottom:4px;padding-left:12px;border-left:2px solid var(--el-color-warning)">{{ note }}</div>
      </div>
      <div v-if="result.config_template">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">配置代码</div>
        <CodeBlock :code="typeof result.config_template === 'string' ? result.config_template : JSON.stringify(result.config_template,null,2)" lang="bash" />
      </div>
      <div v-if="result.rag_supplements?.length" style="margin-top:16px">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">知识库补充</div>
        <div v-for="(s, i) in result.rag_supplements" :key="i" style="font-size:12px;color:var(--text-secondary);margin-bottom:6px;padding:8px;background:var(--bg-tertiary);border-radius:4px">{{ s }}</div>
      </div>
    </div>
    <div v-if="!result && !loading" class="g-card">
      <EmptyGuide title="填写参数生成采集方案" desc="选择设备类型和企业规模，生成标准化配置方案" action-text="填充示例" @action="fillExample" />
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
const deviceType = ref(''); const deviceModel = ref(''); const scale = ref('small')
const loading = ref(false); const result = ref<any>(null)
const deviceOptions = APP_CONFIG.sampleData.deviceTypes
const scaleOptions = [{label:'小型（<100人）',value:'small'},{label:'中型（100-1000人）',value:'medium'},{label:'大型（>1000人）',value:'large'}]
function fillExample() { deviceType.value='firewall'; deviceModel.value='Huawei USG6000'; scale.value='medium' }
async function submit() {
  if (!deviceType.value) { ElMessage.warning('请选择设备类型'); return }
  loading.value=true; result.value=null
  try { const r=await Api.logCollect.plan({device_type:deviceType.value,device_model:deviceModel.value,scale:scale.value}); if(r.success) result.value=r.data; else ElMessage.error(r.msg) } catch { ElMessage.error('请求失败') }
  finally { loading.value=false }
}
</script>