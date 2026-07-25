<template>
  <div class="g-stack">
    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><Grid /></el-icon> 批量解析</div>
          <div class="g-card-desc">支持粘贴多条日志或上传文件（.log/.txt/.csv/.json），批量解析+可选风险研判</div>
        </div>
        <el-button size="small" type="primary" plain @click="fillSample">填充测试日志</el-button>
      </div>
      <el-input v-model="input" type="textarea" :rows="8" placeholder="粘贴日志内容，每行一条..." :disabled="loading" @keyup.ctrl.enter="submit" />
      <div class="g-input-guide"><el-icon><InfoFilled /></el-icon><span>粘贴模式：每行一条日志，最多100条。文件模式：自动读取文件内容，最多500行。</span></div>

      <div class="g-param-row" style="margin-top:12px">
        <div class="g-param-item">
          <el-checkbox v-model="doAssess">同时进行风险研判</el-checkbox>
        </div>
        <div style="flex-grow:1;text-align:right">
          <input
            ref="fileInputRef"
            type="file"
            accept=".log,.txt,.csv,.json"
            style="display:none"
            multiple
            @change="onFileSelected"
          />
          <el-button size="small" :disabled="loading" @click="triggerFilePicker">
            <el-icon style="margin-right:4px"><Upload /></el-icon> 上传日志文件（可多选）
          </el-button>
        </div>
      </div>

      <div v-if="loadedFiles.length" style="margin-top:8px;display:flex;flex-wrap:wrap;gap:6px">
        <el-tag v-for="(name, i) in loadedFiles" :key="i" size="small" closable @close="removeFile(i)">
          {{ name }}
        </el-tag>
      </div>

      <div class="g-actions" style="margin-top:12px">
        <el-button type="primary" :loading="loading" :disabled="!input.trim() && !loadedFiles.length" @click="submit">
          <el-icon><Search /></el-icon> 批量解析
        </el-button>
        <el-button :disabled="loading" @click="clear">清空</el-button>
      </div>
    </div>
    <div v-if="result" class="g-card slide">
      <div class="g-card-header"><div class="g-card-title"><el-icon><Document /></el-icon> 解析结果</div></div>
      <el-descriptions :column="3" border size="small" style="margin-bottom:16px">
        <el-descriptions-item label="总条数">{{ result.total || result.items?.length || 0 }}</el-descriptions-item>
        <el-descriptions-item label="成功">{{ result.success_count || result.items?.filter((i: any)=>!i.error).length || 0 }}</el-descriptions-item>
        <el-descriptions-item label="失败">{{ result.fail_count || result.items?.filter((i: any)=>i.error).length || 0 }}</el-descriptions-item>
      </el-descriptions>
      <div v-if="result.risk_summary" style="margin-bottom:12px">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">风险统计</div>
        <div v-for="(count, level) in result.risk_summary" :key="String(level)" style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
          <RiskBadge :level="getLevelKey(String(level))" :label="String(level)" size="small" />
          <span style="font-size:13px">{{ count }} 条</span>
        </div>
      </div>
      <div v-if="result.items?.length">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">逐条结果</div>
        <div v-for="(item, i) in result.items" :key="i" style="margin-bottom:8px;padding:8px;border:1px solid var(--border-color);border-radius:4px">
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
      <EmptyGuide title="批量解析" desc="粘贴多条日志或上传 .log/.txt/.csv/.json 文件进行批量解析" action-text="填充测试日志" @action="fillSample" />
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
const fileInputRef = ref<HTMLInputElement | null>(null)
const loadedFiles = ref<string[]>([])
const uploadedFilePaths = ref<string[]>([])
const totalCount=computed(()=>input.value.trim()?input.value.split('\n').filter(l=>l.trim()).length:0)
const hasUploadedFiles = computed(() => uploadedFilePaths.value.length > 0)
const sampleLogs=APP_CONFIG?.sampleData?.logs?.join('\n')||''
function fillSample(){input.value=sampleLogs}
function getLevelKey(l: string): string {const m: Record<string, string>={'P0_高危':'P0','P1_中危':'P1','P2_低危':'P2','P3_噪音':'P3','P0':'P0','P1':'P1','P2':'P2','P3':'P3'};return m[l]||'normal'}

function triggerFilePicker() {
  fileInputRef.value?.click()
}

async function onFileSelected(event: Event) {
  const el = event.target as HTMLInputElement
  const files = el.files
  if (!files || files.length === 0) return

  loading.value = true
  result.value = null
  try {
    const formData = new FormData()
    for (const file of Array.from(files)) {
      formData.append('files', file)
    }
    const uploadRes = await Api.logParse.upload(formData)
    if (!uploadRes.success || !uploadRes.data?.file_paths?.length) {
      ElMessage.error(uploadRes.msg || '文件上传失败')
      return
    }
    const newPaths: string[] = uploadRes.data.file_paths
    const newNames = Array.from(files).map(f => f.name)
    uploadedFilePaths.value = [...uploadedFilePaths.value, ...newPaths]
    loadedFiles.value = [...loadedFiles.value, ...newNames]
    ElMessage.success(`已上传 ${newNames.length} 个文件`)
  } catch {
    ElMessage.error('文件上传失败')
  } finally {
    loading.value = false
    el.value = ''
  }
}

function removeFile(index: number) {
  const path = uploadedFilePaths.value[index]
  if (path) {
    Api.logParse.cleanup({ file_paths: [path] }).catch(() => {})
  }
  loadedFiles.value.splice(index, 1)
  uploadedFilePaths.value.splice(index, 1)
}

function clear() {
  if (uploadedFilePaths.value.length) {
    Api.logParse.cleanup({ file_paths: uploadedFilePaths.value }).catch(() => {})
  }
  input.value = ''
  result.value = null
  loadedFiles.value = []
  uploadedFilePaths.value = []
}

async function submit() {
  const hasText = input.value.trim()
  const hasFiles = hasUploadedFiles.value
  if (!hasText && !hasFiles) { ElMessage.warning('请输入日志内容或上传文件'); return }
  loading.value = true; result.value = null
  try {
    let r: any
    if (hasFiles) {
      // 文件模式：服务端读取文件并批量解析
      r = await Api.logParse.batchFile({ file_paths: uploadedFilePaths.value, assess: doAssess.value })
    } else {
      // 文本模式：按行分割
      const lines = input.value.split('\n').filter(l => l.trim())
      r = await Api.logParse.batch({ logs: lines, assess: doAssess.value })
    }
    if (r.success) result.value = r.data; else ElMessage.error(r.msg)
  } catch { ElMessage.error('请求失败') }
  finally { loading.value = false }
}
</script>
