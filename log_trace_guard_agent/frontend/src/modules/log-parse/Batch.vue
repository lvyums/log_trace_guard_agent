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
          <FileUpload
            ref="fileUploadRef"
            :disabled="loading"
            @update:files="onFilesUpdate"
            @upload-success="onUploadSuccess"
            @upload-error="onUploadError"
          />
        </div>
      </div>

      <div class="g-actions" style="margin-top:12px">
        <el-button type="primary" :loading="loading" :disabled="!input.trim() && !hasFiles" @click="submit">
          <el-icon><Search /></el-icon> 批量解析
        </el-button>
        <el-button :disabled="loading" @click="clear">清空</el-button>
        <el-button v-if="result" :disabled="loading" @click="exportResults">
          <el-icon style="margin-right:4px"><Download /></el-icon> 导出结果
        </el-button>
        <el-button v-if="result" type="primary" plain :disabled="loading" @click="sendToCorrelate">
          <el-icon><Connection /></el-icon> 送到关联分析
        </el-button>
      </div>
    </div>

    <!-- 结果展示 -->
    <div v-if="result" class="g-card slide">
      <div class="g-card-header">
        <div class="g-card-title"><el-icon><Document /></el-icon> 解析结果</div>
        <div class="g-actions">
          <el-select v-model="filterDevice" placeholder="设备类型" clearable size="small" style="width:120px;margin-right:8px">
            <el-option v-for="(count, type) in result.summary?.device_distribution" :key="type" :label="`${type} (${count})`" :value="type" />
          </el-select>
          <el-select v-model="filterRisk" placeholder="风险等级" clearable size="small" style="width:120px">
            <el-option v-for="(count, level) in result.summary?.risk_summary" :key="level" :label="`${level} (${count})`" :value="level" />
          </el-select>
        </div>
      </div>

      <!-- 基础统计 -->
      <el-descriptions :column="4" border size="small" style="margin-bottom:16px">
        <el-descriptions-item label="总条数">{{ result.total }}</el-descriptions-item>
        <el-descriptions-item label="成功">
          <el-tag type="success" size="small">{{ result.success_count }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="失败">
          <el-tag v-if="result.fail_count > 0" type="danger" size="small">{{ result.fail_count }}</el-tag>
          <span v-else>0</span>
        </el-descriptions-item>
        <el-descriptions-item label="成功率">{{ ((result.success_count / result.total) * 100).toFixed(1) }}%</el-descriptions-item>
      </el-descriptions>

      <!-- 设备类型分布 -->
      <div v-if="result.summary?.device_distribution && Object.keys(result.summary.device_distribution).length > 0" style="margin-bottom:16px">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px"><el-icon style="margin-right:4px"><DataBoard /></el-icon> 设备类型分布</div>
        <div style="display:flex;flex-wrap:wrap;gap:8px">
          <el-tag v-for="(count, type) in result.summary.device_distribution" :key="type" :type="getDeviceTagType(type)" size="small">
            {{ type }}: {{ count }}
          </el-tag>
        </div>
      </div>

      <!-- Top 源 IP -->
      <div v-if="result.summary?.top_src_ips && Object.keys(result.summary.top_src_ips).length > 0" style="margin-bottom:16px">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px"><el-icon style="margin-right:4px"><Position /></el-icon> Top 源 IP</div>
        <div style="display:flex;flex-wrap:wrap;gap:8px">
          <el-tag v-for="(count, ip) in result.summary.top_src_ips" :key="ip" size="small">
            {{ ip }}: {{ count }}
          </el-tag>
        </div>
      </div>

      <!-- 风险统计 -->
      <div v-if="result.summary?.risk_summary && Object.keys(result.summary.risk_summary).length > 0" style="margin-bottom:16px">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px"><el-icon style="margin-right:4px"><Warning /></el-icon> 风险统计</div>
        <div v-for="(count, level) in result.summary.risk_summary" :key="level" style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
          <RiskBadge :level="getLevelKey(String(level))" :label="String(level)" size="small" />
          <span style="font-size:13px">{{ count }} 条</span>
        </div>
      </div>

      <!-- 逐条结果 -->
      <div v-if="filteredItems.length > 0">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">
          <el-icon style="margin-right:4px"><List /></el-icon> 逐条结果 ({{ filteredItems.length }}/{{ result.items.length }})
        </div>
        <div v-for="(item, i) in filteredItems" :key="i" style="margin-bottom:8px;padding:8px;border:1px solid var(--border-color);border-radius:4px">
          <div style="font-size:12px;color:var(--text-tertiary);margin-bottom:4px;display:flex;justify-content:space-between">
            <span>#{{ item.index + 1 }} {{ item.log_line?.slice(0,60) || '' }}</span>
            <el-button size="small" text @click="copyLogLine(item.log_line)">
              <el-icon><CopyDocument /></el-icon>
            </el-button>
          </div>
          <div v-if="item.error" class="g-alert g-alert--danger" style="margin:0">{{ item.error }}</div>
          <div v-else style="font-size:12px">
            <el-tag size="small">{{ item.parse_result?.device_type || '未知' }}</el-tag>
            <RiskBadge v-if="item.risk_result?.risk_level" :level="getLevelKey(item.risk_result.risk_level)" :label="item.risk_result.risk_level" size="small" />
            <span v-if="item.parse_result?.user" style="margin-left:8px;color:var(--text-secondary)">用户: {{ item.parse_result.user }}</span>
            <span v-if="item.parse_result?.src_ip" style="margin-left:8px;color:var(--text-secondary)">源IP: {{ item.parse_result.src_ip }}</span>
            <span v-if="item.parse_result?.status" style="margin-left:8px;color:var(--text-secondary)">状态: {{ item.parse_result.status }}</span>
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
import { Utils } from '../../utils'
import { sendToCorrelate as storeSendToCorrelate } from '../../utils/crossModuleStore'
import RiskBadge from '../../components/RiskBadge.vue'
import EmptyGuide from '../../components/EmptyGuide.vue'
import FileUpload from '../../components/FileUpload.vue'

defineProps<{ mode?: string }>()

const input = ref('')
const doAssess = ref(true)
const loading = ref(false)
const result = ref<any>(null)
const fileUploadRef = ref<InstanceType<typeof FileUpload> | null>(null)

// 文件状态
const uploadedFilePaths = ref<string[]>([])
const hasFiles = computed(() => uploadedFilePaths.value.length > 0)

// 筛选条件
const filterDevice = ref('')
const filterRisk = ref('')

const sampleLogs = APP_CONFIG?.sampleData?.logs?.join('\n') || ''

// 筛选后的结果
const filteredItems = computed(() => {
  if (!result.value?.items) return []
  return result.value.items.filter((item: any) => {
    if (filterDevice.value && item.parse_result?.device_type !== filterDevice.value) return false
    if (filterRisk.value && item.risk_result?.risk_level !== filterRisk.value) return false
    return true
  })
})

function fillSample() { input.value = sampleLogs }

function getLevelKey(l: string): string {
  const m: Record<string, string> = {
    'P0_高危': 'P0', 'P1_中危': 'P1', 'P2_低危': 'P2', 'P3_噪音': 'P3',
    'P0': 'P0', 'P1': 'P1', 'P2': 'P2', 'P3': 'P3',
    'high': 'P0', 'medium': 'P1', 'low': 'P2', 'noise': 'P3',
  }
  return m[l] || 'normal'
}

function getDeviceTagType(type: string): string {
  const map: Record<string, string> = {
    ssh: 'danger', web: 'success', waf: 'warning', firewall: 'danger', db: 'primary', traffic: 'info',
  }
  return map[type] || 'info'
}

// FileUpload 组件回调
function onFilesUpdate(files: any[]) {
  uploadedFilePaths.value = files.map(f => f.path)
}

function onUploadSuccess(_files: any[]) {
  // 上传成功
}

function onUploadError(msg: string) {
  ElMessage.error(msg)
}

function clear() {
  fileUploadRef.value?.clearAll()
  input.value = ''
  result.value = null
  uploadedFilePaths.value = []
  filterDevice.value = ''
  filterRisk.value = ''
}

function copyLogLine(logLine: string) {
  Utils.copyText(logLine || '')
  ElMessage.success('已复制')
}

function exportResults() {
  if (!result.value) return

  const exportData = {
    summary: result.value.summary,
    items: result.value.items.map((item: any) => ({
      index: item.index,
      log_line: item.log_line,
      device_type: item.parse_result?.device_type,
      src_ip: item.parse_result?.src_ip,
      dst_ip: item.parse_result?.dst_ip,
      user: item.parse_result?.user,
      status: item.parse_result?.status,
      risk_level: item.risk_result?.risk_level,
      attack_type: item.risk_result?.attack_type,
      risk_desc: item.risk_result?.risk_desc,
      suggestion: item.risk_result?.suggestion,
      error: item.error,
    })),
  }

  const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `batch-parse-result-${new Date().toISOString().slice(0, 10)}.json`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('结果已导出')
}

async function submit() {
  const hasText = input.value.trim()
  if (!hasText && !hasFiles.value) { ElMessage.warning('请输入日志内容或上传文件'); return }
  loading.value = true; result.value = null
  filterDevice.value = ''
  filterRisk.value = ''
  try {
    let r: any
    if (hasFiles.value) {
      r = await Api.logParse.batchFile({ file_paths: uploadedFilePaths.value, assess: doAssess.value })
    } else {
      const lines = input.value.split('\n').filter(l => l.trim())
      r = await Api.logParse.batch({ logs: lines, assess: doAssess.value })
    }
    if (r.success) result.value = r.data; else ElMessage.error(r.msg)
  } catch { ElMessage.error('请求失败') }
  finally { loading.value = false }
}

// 送到关联分析：收集所有解析过的日志，传递到 log-correlate 模块
function sendToCorrelate() {
  if (!result.value?.items?.length) {
    ElMessage.warning('没有可发送的解析结果')
    return
  }
  const logs: string[] = []
  for (const item of result.value.items) {
    if (item.log_line) {
      logs.push(item.log_line)
    } else if (item.parse_result?.raw_log) {
      logs.push(item.parse_result.raw_log)
    }
  }
  if (!logs.length) {
    ElMessage.warning('没有可发送的日志内容')
    return
  }
  storeSendToCorrelate({
    logs,
    source: 'batch-parse',
  })
  window.location.hash = '#/log-correlate/analyze'
  ElMessage.success(`已发送 ${logs.length} 条日志到关联分析`)
}
</script>
