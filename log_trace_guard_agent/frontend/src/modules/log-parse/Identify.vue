<template>
  <div class="g-stack">
    <AlertGuide type="info" title="日志识别是分析的起点">
      粘贴一行完整原始日志，系统自动识别设备类型。识别后可直接跳转解析/研判，形成完整分析链路。
    </AlertGuide>

    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><Aim /></el-icon> 日志识别</div>
          <div class="g-card-desc">输入原始日志，AI自动识别设备类型、日志格式与关键字段</div>
        </div>
        <div class="g-actions">
          <el-button size="small" @click="showSample = !showSample">
            {{ showSample ? '收起' : '查看示例' }}
          </el-button>
          <el-button size="small" type="primary" plain @click="fillSample">填充测试日志</el-button>
        </div>
      </div>

      <div v-if="showSample" style="margin-bottom:12px">
        <div class="g-alert g-alert--info">
          <el-icon><InfoFilled /></el-icon>
          <span>支持格式：syslog、JSON、CSV、纯文本。多条日志逐行粘贴即可分别识别。</span>
        </div>
        <div class="g-code-block" style="font-size:12px">
          <div class="g-code-body" style="max-height:120px">
            <code>{{ sampleLogs }}</code>
          </div>
        </div>
      </div>

      <el-input
        v-model="input" type="textarea" :rows="6"
        placeholder="在此粘贴日志内容..." class="log-input-area"
        :disabled="loading"
        @keyup.ctrl.enter="submit" @keyup.meta.enter="submit"
      />
      <div class="g-input-guide">
        <el-icon><InfoFilled /></el-icon>
        <span>支持粘贴单条或多条日志，Ctrl+Enter 快速提交。最大50000字符。</span>
      </div>

      <div class="g-actions" style="margin-top:12px">
        <el-button type="primary" :loading="loading" :disabled="!input.trim()" @click="submit">
          <el-icon style="margin-right:4px"><Search /></el-icon> 识别分析
        </el-button>
        <el-button :disabled="loading" @click="clear">清空</el-button>
      </div>
    </div>

    <!-- 多条结果 -->
    <div v-if="results.length > 1" class="g-card slide">
      <div class="g-card-header">
        <div class="g-card-title"><el-icon><Document /></el-icon> 识别结果（{{ results.length }}条日志）</div>
      </div>
      <div v-for="(item, i) in results" :key="i"
           style="margin-bottom:12px;padding:12px;border:1px solid var(--border-color);border-radius:6px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <span style="font-weight:600;font-size:13px">日志 #{{ i + 1 }}</span>
          <template v-if="item.device_type !== 'unknown'">
            <RiskBadge :level="'normal'" :label="item.device_type" />
          </template>
          <template v-else>
            <RiskBadge :level="'P0'" label="未知" />
          </template>
        </div>
        <div class="g-code-body" style="font-size:11px;max-height:40px;margin-bottom:8px;padding:4px 8px;background:var(--bg-secondary);border-radius:4px">
          {{ item.raw_log }}
        </div>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="设备类型">
            <RiskBadge :level="item.device_type !== 'unknown' ? 'normal' : 'P0'"
                       :label="item.device_type || '未知'" />
          </el-descriptions-item>
          <el-descriptions-item label="置信度">
            {{ item.confidence ? Math.round(item.confidence) + '%' : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="识别依据" :span="2">
            <span style="font-size:12px">{{ item.identify_reason || '规则匹配' }}</span>
          </el-descriptions-item>
        </el-descriptions>
        <div style="margin-top:8px;display:flex;gap:8px">
          <el-button size="small" type="primary" plain @click="sendToParse(item.raw_log || input)">
            <el-icon><Document /></el-icon> 解析该日志
          </el-button>
          <el-button size="small" type="danger" plain @click="sendToAssess(item.raw_log || input)">
            <el-icon><Warning /></el-icon> 研判风险
          </el-button>
        </div>
      </div>
      <ResultGuide :content="APP_CONFIG.guidance.resultGuides.logParse" />
    </div>

    <!-- 单条结果 -->
    <div v-else-if="results.length === 1" class="g-card slide">
      <div class="g-card-header">
        <div class="g-card-title"><el-icon><Document /></el-icon> 识别结果</div>
      </div>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="设备类型">
          <RiskBadge :level="results[0].device_type !== 'unknown' ? 'normal' : 'P0'"
                     :label="results[0].device_type || '未知'" />
        </el-descriptions-item>
        <el-descriptions-item label="置信度">
          {{ results[0].confidence ? Math.round(results[0].confidence) + '%' : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="识别依据" :span="2">
          <span style="font-size:12px">{{ results[0].identify_reason || '规则匹配' }}</span>
        </el-descriptions-item>
      </el-descriptions>
      <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
        <el-button type="primary" @click="sendToParse(input)">
          <el-icon><Document /></el-icon> 去结构化解析
        </el-button>
        <el-button type="danger" @click="sendToAssess(input)">
          <el-icon><Warning /></el-icon> 去风险研判
        </el-button>
      </div>
      <div style="margin-top:12px;padding:12px;background:var(--bg-secondary);border-radius:6px;font-size:13px;line-height:1.8">
        <div style="font-weight:600;margin-bottom:6px">
          <el-icon><InfoFilled /></el-icon> 下一步建议
        </div>
        <div v-if="results[0].device_type && results[0].device_type !== 'unknown'" style="color:var(--text-secondary)">
          已识别为 <strong>{{ results[0].device_type }}</strong> 设备日志。建议继续「结构化解析」提取关键字段（源IP、用户、状态等），
          再通过「风险研判」评估是否存在安全威胁。
        </div>
        <div v-else style="color:var(--el-color-warning)">
          未能识别设备类型，建议尝试「风险研判」直接分析异常行为，或检查日志格式是否正确。
        </div>
      </div>
      <ResultGuide :content="APP_CONFIG.guidance.resultGuides.logParse" />
    </div>

    <div v-if="results.length === 0 && !loading" class="g-card">
      <EmptyGuide
        title="等待日志输入"
        desc="在上方输入框粘贴日志内容，点击识别分析。识别后可跳转解析和研判。"
        action-text="填充测试日志"
        @action="fillSample"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { APP_CONFIG } from '../../config'
import { Api } from '../../api'
import AlertGuide from '../../components/AlertGuide.vue'
import RiskBadge from '../../components/RiskBadge.vue'
import ResultGuide from '../../components/ResultGuide.vue'
import EmptyGuide from '../../components/EmptyGuide.vue'

defineProps<{ mode?: string }>()

const input = ref('')
const loading = ref(false)
const results = ref<any[]>([])
const showSample = ref(false)

const sampleLogs = APP_CONFIG.sampleData.logs.join('\n')

function fillSample() {
  input.value = sampleLogs
  showSample.value = false
}

async function submit() {
  if (!input.value.trim()) {
    ElMessage.warning('请输入日志内容后再提交')
    return
  }
  if (input.value.length > 50000) {
    ElMessage.error('输入内容过长（最大50000字符），请分批提交')
    return
  }
  loading.value = true
  results.value = []
  try {
    const res = await Api.logParse.identify({ log_line: input.value })
    if (res.success && res.data) {
      if (res.data.items) {
        results.value = res.data.items
      } else {
        results.value = [res.data]
      }
    } else {
      ElMessage.error(res.msg || '识别失败')
    }
  } catch {
    ElMessage.error('请求失败，请检查服务是否运行')
  } finally {
    loading.value = false
  }
}

function clear() {
  input.value = ''
  results.value = []
}

function sendToParse(logText: string) {
  sessionStorage.setItem('log-parse-input', logText)
  window.location.hash = '#/log-parse/parse'
}

function sendToAssess(logText: string) {
  sessionStorage.setItem('log-assess-input', logText)
  window.location.hash = '#/log-parse/assess'
}
</script>
