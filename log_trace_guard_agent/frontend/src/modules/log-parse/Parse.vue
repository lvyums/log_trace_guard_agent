<template>
  <div class="g-stack">
    <AlertGuide type="info" title="结构化解析让日志可被检索和理解">
      原始日志是给人看的文本，结构化字段可被机器检索。点击字段名查看释义，或一键跳转风险研判。
    </AlertGuide>

    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><Document /></el-icon> 结构化解析</div>
          <div class="g-card-desc">将原始日志文本解析为标准化的结构化字段</div>
        </div>
        <el-button size="small" type="primary" plain @click="fillSample">填充测试日志</el-button>
      </div>
      <el-input
        v-model="input" type="textarea" :rows="4"
        placeholder="粘贴原始日志..." :disabled="loading"
        @keyup.ctrl.enter="submit"
      />
      <div class="g-input-guide">
        <el-icon><InfoFilled /></el-icon>
        <span>支持 syslog / JSON / CSV 格式。从「日志识别」页面可自动填入日志。</span>
      </div>
      <div class="g-actions" style="margin-top:12px">
        <el-button type="primary" :loading="loading" @click="submit">解析</el-button>
        <el-button v-if="result" size="small" type="danger" plain @click="goAssess">
          <el-icon><Warning /></el-icon> 风险研判
        </el-button>
      </div>
    </div>

    <div v-if="result" class="g-card slide">
      <div class="g-card-header">
        <div class="g-card-title"><el-icon><DataBoard /></el-icon> 解析结果</div>
        <div style="display:flex;gap:8px">
          <el-button size="small" @click="copyJson">复制JSON</el-button>
          <el-tooltip v-if="result.device_type && result.device_type !== 'unknown'" :content="'设备: ' + result.device_type">
            <RiskBadge :level="'normal'" :label="result.device_type" size="small" />
          </el-tooltip>
        </div>
      </div>

      <!-- 日志解读 -->
      <div v-if="interpretation" style="margin-bottom:16px;padding:12px;background:var(--bg-secondary);border-radius:6px;line-height:1.8">
        <div style="font-weight:600;margin-bottom:6px;font-size:13px">
          <el-icon><Reading /></el-icon> 日志解读
        </div>
        <div style="font-size:13px;color:var(--text-secondary);white-space:pre-wrap">{{ interpretation }}</div>
      </div>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="字段列表" name="fields">
          <el-table :data="fieldRows" border size="small" class="g-table" max-height="400"
                    @row-click="explainField">
            <el-table-column prop="name" label="字段名" width="180">
              <template #default="{ row }">
                <div style="display:flex;align-items:center;gap:4px">
                  <span class="field-name" style="cursor:pointer" :title="'点击查看释义'">
                    {{ row.name }}
                  </span>
                  <el-icon style="font-size:12px;color:var(--el-color-info);cursor:pointer"
                           @click.stop="explainField(row)">
                    <QuestionFilled />
                  </el-icon>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="value" label="值">
              <template #default="{ row }">
                <span :class="{ 'field-missing': row.value === '-' || row.value === '' }"
                      class="field-value">
                  {{ row.value || '-' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button size="small" text @click.stop="explainField(row)">
                  <el-icon style="margin-right:2px"><QuestionFilled /></el-icon>释义
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="原始JSON" name="json">
          <CodeBlock :code="JSON.stringify(result, null, 2)" lang="json" />
        </el-tab-pane>
      </el-tabs>

      <!-- 缺失字段提示 -->
      <div v-if="missingFields.length > 0" style="margin-top:12px">
        <el-alert :title="'缺失 ' + missingFields.length + ' 个关键字段'" type="warning" :closable="false" show-icon>
          <template #default>
            <div style="font-size:12px;margin-top:4px">
              字段 {{ missingFields.join('、') }} 未提取到。<br/>
              原因可能：日志不完整、格式特殊、或该设备日志不包含这些字段。
            </div>
          </template>
        </el-alert>
      </div>

      <!-- 字段释义弹窗 -->
      <el-dialog v-model="showExplain" :title="'字段释义: ' + explainFieldName" width="500px">
        <div v-if="explainLoading" style="text-align:center;padding:20px">
          <el-icon class="is-loading" :size="24"><Loading /></el-icon>
          <div style="margin-top:8px;font-size:13px">查询中...</div>
        </div>
        <div v-else-if="explainResult" style="white-space:pre-wrap;line-height:1.8;font-size:13px">
          {{ explainResult }}
        </div>
        <div v-else style="text-align:center;padding:20px;color:var(--text-secondary);font-size:13px">
          暂无释义数据
        </div>
      </el-dialog>

      <div style="margin-top:12px;display:flex;gap:8px">
        <el-button type="danger" plain @click="goAssess">
          <el-icon><Warning /></el-icon> 基于此结果进行风险研判
        </el-button>
      </div>
    </div>

    <div v-if="!result && !loading" class="g-card">
      <div style="text-align:center;padding:40px;color:var(--text-secondary)">
        <el-icon :size="48"><DataBoard /></el-icon>
        <div style="margin-top:8px;font-weight:500">粘贴日志进行结构化解析</div>
        <div style="font-size:12px;margin-top:4px">
          也可以从「日志识别」页面识别后直接跳转过来
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { APP_CONFIG } from '../../config'
import { Api } from '../../api'
import { Utils } from '../../utils'
import AlertGuide from '../../components/AlertGuide.vue'
import CodeBlock from '../../components/CodeBlock.vue'
import RiskBadge from '../../components/RiskBadge.vue'

defineProps<{ mode?: string }>()

const input = ref('')
const loading = ref(false)
const result = ref<any>(null)
const activeTab = ref('fields')
const showExplain = ref(false)
const explainLoading = ref(false)
const explainFieldName = ref('')
const explainResult = ref('')

function checkPrefill() {
  const saved = sessionStorage.getItem('log-parse-input')
  if (saved && saved !== input.value) {
    input.value = saved
    sessionStorage.removeItem('log-parse-input')
    submit()
  }
}

// 设备类型 → 日志解读模板
const INTERPRETATIONS: Record<string, (f: any) => string> = {
  ssh: (f) => {
    const parts: string[] = []
    if (f.user) parts.push(`用户 ${f.user}`)
    if (f.src_ip) parts.push(`从 ${f.src_ip}`)
    if (f.status === 'Failed' || f.status === 'failure') parts.push('尝试登录失败')
    else if (f.status) parts.push(`登录状态: ${f.status}`)
    if (f.detail) parts.push(f.detail)
    return parts.length ? `SSH 日志：${parts.join('，')}。` : 'SSH 登录事件日志。'
  },
  web: (f) => {
    const parts: string[] = []
    if (f.method) parts.push(f.method)
    if (f.url) parts.push(f.url)
    if (f.status) parts.push(`→ ${f.status}`)
    if (f.src_ip) parts.push(`来源: ${f.src_ip}`)
    return parts.length ? `Web 请求：${parts.join(' ')}。` : 'Web 访问日志。'
  },
  waf: (f) => {
    const parts: string[] = []
    if (f.action) parts.push(`动作: ${f.action}`)
    if (f.src_ip) parts.push(`来源: ${f.src_ip}`)
    if (f.rule_id) parts.push(`规则: ${f.rule_id}`)
    if (f.severity) parts.push(`严重度: ${f.severity}`)
    return parts.length ? `WAF 告警：${parts.join('，')}。` : 'WAF 安全日志。'
  },
  firewall: (f) => {
    const parts: string[] = []
    if (f.action) parts.push(f.action === 'BLOCK' ? '已拦截' : f.action)
    if (f.src_ip && f.dst_ip) parts.push(`${f.src_ip} → ${f.dst_ip}`)
    if (f.port) parts.push(`端口 ${f.port}`)
    if (f.protocol) parts.push(f.protocol)
    return parts.length ? `防火墙事件：${parts.join('，')}。` : '防火墙日志。'
  },
  db: (f) => {
    const parts: string[] = []
    if (f.user) parts.push(`用户 ${f.user}`)
    if (f.query) parts.push(`查询: ${f.query?.slice(0, 60)}`)
    if (f.status) parts.push(`状态: ${f.status}`)
    return parts.length ? `数据库日志：${parts.join('，')}。` : '数据库操作日志。'
  },
}

const fieldRows = computed(() => {
  if (!result.value) return []
  const obj = result.value || {}
  if (typeof obj !== 'object') return []
  const excludeFields = ['missing_fields', 'raw_log', 'fallback_note']
  return Object.entries(obj)
    .filter(([name]) => !excludeFields.includes(name) && !name.endsWith('_missing'))
    .map(([name, value]) => ({
      name,
      value: typeof value === 'object' ? JSON.stringify(value) : value == null ? '-' : String(value),
    }))
})

const missingFields = computed(() => {
  if (!result.value) return []
  return result.value.missing_fields || []
})

const interpretation = computed(() => {
  if (!result.value) return ''
  const dt = result.value.device_type || ''
  const fn = INTERPRETATIONS[dt]
  if (fn) return fn(result.value)
  // 通用解读
  const parts: string[] = []
  if (result.value.src_ip) parts.push(`源IP: ${result.value.src_ip}`)
  if (result.value.user) parts.push(`用户: ${result.value.user}`)
  if (result.value.status) parts.push(`状态: ${result.value.status}`)
  if (result.value.action) parts.push(`动作: ${result.value.action}`)
  return parts.length ? `该日志包含关键信息：${parts.join('，')}。` : ''
})

function fillSample() {
  input.value = APP_CONFIG.sampleData.logs[0]
}

async function submit() {
  if (!input.value.trim()) {
    ElMessage.warning('请输入日志内容')
    return
  }
  loading.value = true
  result.value = null
  activeTab.value = 'fields'
  try {
    const res = await Api.logParse.parse({ log_line: input.value })
    if (res.success) {
      result.value = res.data
    } else {
      ElMessage.error(res.msg)
    }
  } catch {
    ElMessage.error('请求失败')
  } finally {
    loading.value = false
  }
}

async function explainField(row: any) {
  const fieldName = row?.name || row
  if (!fieldName) return
  explainFieldName.value = fieldName
  showExplain.value = true
  explainLoading.value = true
  explainResult.value = ''
  try {
    const res = await Api.logParse.explain({ field_name: fieldName, device_type: result.value?.device_type })
    if (res.success && res.data) {
      explainResult.value = res.data.explanation || '暂无释义'
    } else {
      explainResult.value = '查询失败：' + (res.msg || '未知错误')
    }
  } catch {
    explainResult.value = '请求失败，请稍后重试'
  } finally {
    explainLoading.value = false
  }
}

function copyJson() {
  Utils.copyText(JSON.stringify(result.value, null, 2))
  ElMessage.success('已复制')
}

function goAssess() {
  // 保存原始日志到 sessionStorage，Assess.vue 读取
  sessionStorage.setItem('log-assess-input', input.value)
  window.location.hash = '#/log-parse/assess'
}

// 从 Identify 页面跳转过来时自动填入
// 同时监听 hashchange 以支持同一页面重新激活
onMounted(() => {
  checkPrefill()
  window.addEventListener('hashchange', checkPrefill)
})
onUnmounted(() => {
  window.removeEventListener('hashchange', checkPrefill)
})
</script>
