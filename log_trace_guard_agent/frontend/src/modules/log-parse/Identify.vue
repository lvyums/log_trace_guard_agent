<template>
  <div class="g-stack">
    <AlertGuide type="info" title="日志识别是分析的起点">
      粘贴一行完整原始日志，系统会自动识别设备类型、日志格式、关键字段。
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
          <span>支持格式：syslog、JSON、CSV、纯文本。单条或多条均可。</span>
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

    <div v-if="result" class="g-card slide">
      <div class="g-card-header">
        <div class="g-card-title"><el-icon><Document /></el-icon> 识别结果</div>
      </div>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="设备类型">
          <RiskBadge :level="'normal'" :label="result.device_type || '未知'" />
        </el-descriptions-item>
        <el-descriptions-item label="置信度">
          {{ result.confidence ? Math.round(result.confidence) + '%' : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="识别依据">{{ result.identify_reason || '规则匹配' }}</el-descriptions-item>
      </el-descriptions>
      <div v-if="result.fields && Object.keys(result.fields).length" style="margin-top:16px">
        <div style="font-weight:600;margin-bottom:8px;font-size:13px">关键字段</div>
        <CodeBlock :code="JSON.stringify(result.fields, null, 2)" lang="json" />
      </div>
      <ResultGuide :content="APP_CONFIG.guidance.resultGuides.logParse" />
    </div>

    <div v-if="!result && !loading" class="g-card">
      <EmptyGuide
        title="等待日志输入"
        desc="在上方输入框粘贴日志内容，点击识别分析"
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
import CodeBlock from '../../components/CodeBlock.vue'
import ResultGuide from '../../components/ResultGuide.vue'
import EmptyGuide from '../../components/EmptyGuide.vue'

defineProps<{ mode?: string }>()

const input = ref('')
const loading = ref(false)
const result = ref<any>(null)
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
  result.value = null
  try {
    const res = await Api.logParse.identify({ log_line: input.value })
    if (res.success) {
      result.value = res.data
    } else {
      ElMessage.error(res.msg)
    }
  } catch {
    ElMessage.error('请求失败，请检查服务是否运行')
  } finally {
    loading.value = false
  }
}

function clear() {
  input.value = ''
  result.value = null
}
</script>