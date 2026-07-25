<template>
  <div class="g-stack">
    <AlertGuide type="info" title="生成专属指导手册">
      根据您的使用场景，AI 会生成一份完整的日志采集与分析指导手册，包含架构建议、配置示例、最佳实践等，可直接下载使用。
    </AlertGuide>
    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><Notebook /></el-icon> 指导手册生成</div>
          <div class="g-card-desc">填写您的使用场景，AI 生成定制化的指导手册</div>
        </div>
        <el-button size="small" type="primary" plain @click="fillExample">填充示例</el-button>
      </div>
      <el-form label-position="top" size="default">
        <el-form-item label="企业规模">
          <el-radio-group v-model="scale">
            <el-radio-button v-for="s in scaleOptions" :key="s.value" :value="s.value">{{ s.label }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="安全设备类型（多选）">
          <el-select v-model="deviceTypes" multiple placeholder="选择设备类型" style="width:100%">
            <el-option v-for="d in deviceOptions" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="使用场景">
          <el-input v-model="scenario" type="textarea" :rows="4" placeholder="描述您的使用场景，如：新建SOC团队需要一套完整的日志采集方案..." />
        </el-form-item>
        <el-form-item label="特殊需求（可选）">
          <el-input v-model="requirements" type="textarea" :rows="2" placeholder="如：需要满足等保2.0要求、预算有限等" />
        </el-form-item>
      </el-form>
      <div class="g-actions">
        <el-button type="primary" @click="submit" :loading="loading">生成手册</el-button>
      </div>
    </div>
    <div v-if="result" class="g-card slide">
      <div class="g-card-header">
        <div class="g-card-title"><el-icon><Document /></el-icon> 指导手册</div>
        <el-button type="success" @click="downloadMarkdown" :icon="Download">下载 Markdown</el-button>
      </div>
      <div class="guide-content" v-html="renderedContent"></div>
    </div>
    <div v-if="!result && !loading" class="g-card">
      <EmptyGuide title="填写场景生成指导手册" desc="企业规模、设备类型、使用场景越详细，生成的手册越精准" action-text="填充示例" @action="fillExample" />
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import { APP_CONFIG } from '../../config'
import { Api } from '../../api'
import AlertGuide from '../../components/AlertGuide.vue'
import EmptyGuide from '../../components/EmptyGuide.vue'
defineProps<{ mode?: string }>()
const scale = ref('small')
const deviceTypes = ref<string[]>([])
const scenario = ref('')
const requirements = ref('')
const loading = ref(false)
const result = ref<any>(null)
const deviceOptions = APP_CONFIG.sampleData.deviceTypes
const scaleOptions = [{ label: '小型（<100人）', value: 'small' }, { label: '中型（100-1000人）', value: 'medium' }, { label: '大型（>1000人）', value: 'large' }]

function fillExample() {
  scale.value = 'medium'
  deviceTypes.value = ['firewall', 'waf', 'ids']
  scenario.value = '公司刚建成新的数据中心，需要为所有安全设备配置日志采集，统一发送到 SIEM 平台进行分析。目前有 50 台防火墙、10 台 WAF、5 台 IDS。'
  requirements.value = '需要满足等保 2.0 三级要求，日志留存 180 天以上'
}

const renderedContent = computed(() => {
  if (!result.value?.content) return ''
  return simpleMarkdown(result.value.content)
})

function simpleMarkdown(text: string): string {
  // 代码块
  let result = text.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
  // 标题
  result = result.replace(/^### (.+)$/gm, '<h3>$1</h3>')
  result = result.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  result = result.replace(/^# (.+)$/gm, '<h1>$1</h1>')
  // 加粗
  result = result.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  // 行内代码（排除已在 pre 标签内的）
  result = result.replace(/`([^`\n]+)`/g, '<code>$1</code>')
  // 列表项
  result = result.replace(/^- (.+)$/gm, '<li>$1</li>')
  result = result.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
  // 换行
  result = result.replace(/\n/g, '<br>')
  return result
}

async function submit() {
  if (!scenario.value) { ElMessage.warning('请填写使用场景'); return }
  loading.value = true; result.value = null
  try {
    const r = await Api.advisory.guide({
      scale: scale.value,
      device_types: deviceTypes.value,
      scenario: scenario.value,
      requirements: requirements.value,
    })
    if (r.success) result.value = r.data; else ElMessage.error(r.msg)
  } catch { ElMessage.error('请求失败') }
  finally { loading.value = false }
}

function downloadMarkdown() {
  if (!result.value?.content) return
  const blob = new Blob([result.value.content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `日志采集指导手册_${new Date().toISOString().slice(0, 10)}.md`
  a.click()
  URL.revokeObjectURL(url)
}
</script>
<style scoped>
.guide-content {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-primary);
  max-height: 600px;
  overflow-y: auto;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
}
.guide-content :deep(h1) { font-size: 20px; margin: 16px 0 8px; }
.guide-content :deep(h2) { font-size: 17px; margin: 14px 0 6px; color: var(--color-primary); }
.guide-content :deep(h3) { font-size: 15px; margin: 12px 0 4px; }
.guide-content :deep(code) {
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}
.guide-content :deep(pre) {
  background: var(--bg-tertiary);
  padding: 12px 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}
.guide-content :deep(pre code) {
  background: none;
  padding: 0;
}
.guide-content :deep(ul) {
  padding-left: 20px;
  margin: 4px 0;
}
.guide-content :deep(li) {
  margin: 2px 0;
}
</style>
