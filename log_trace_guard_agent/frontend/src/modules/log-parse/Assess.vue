<template>
  <div class="g-stack">
    <AlertGuide type="warning" title="风险研判需要结合上下文">
      单独一条日志的风险判断有局限性。建议先通过「日志识别」确认设备类型，再到「结构化解析」提取关键字段，最后做综合研判。
    </AlertGuide>

    <div class="g-card">
      <div class="g-card-header">
        <div>
          <div class="g-card-title"><el-icon><Warning /></el-icon> 风险研判</div>
          <div class="g-card-desc">对日志内容进行安全风险评估，标注风险等级与处置建议</div>
        </div>
        <el-button size="small" type="primary" plain @click="fillSample">填充测试日志</el-button>
      </div>
      <el-input
        v-model="input" type="textarea" :rows="4"
        placeholder="粘贴待研判的日志..." :disabled="loading"
        @keyup.ctrl.enter="submit"
      />
      <div class="g-input-guide">
        <el-icon><InfoFilled /></el-icon>
        <span>从「日志识别」或「结构化解析」页面可自动跳转至此。可选指定设备类型提高精度。</span>
      </div>
      <div style="margin-top:12px">
        <el-select v-model="deviceType" placeholder="设备类型（可选）" clearable size="small" style="width:200px">
          <el-option v-for="d in deviceOptions" :key="d" :label="d" :value="d" />
        </el-select>
      </div>
      <div class="g-actions" style="margin-top:12px">
        <el-button type="primary" :loading="loading" @click="submit">风险研判</el-button>
      </div>
    </div>

    <div v-if="result" class="slide">
      <RiskCard
        :title="'风险研判结果'"
        :level="result.risk_level || 'normal'"
        :confidence="result.confidence"
        :source="result.match_rule_ids ? '规则引擎: ' + result.match_rule_ids.join(', ') : '规则匹配'"
        :details="result.attack_type ? { '攻击类型': result.attack_type, '风险描述': result.risk_desc, '处置建议': result.suggestion } : { '风险描述': result.risk_desc }"
        :disposition="result.suggestion"
      />
      <div style="margin-top:12px;display:flex;gap:8px">
        <el-button size="small" plain @click="goParse">
          <el-icon><Document /></el-icon> 查看结构化解析
        </el-button>
      </div>
    </div>

    <div v-if="!result && !loading" style="text-align:center;padding:48px 24px;color:var(--text-secondary)">
      <el-icon :size="48"><Warning /></el-icon>
      <div style="margin-top:12px;font-weight:500;font-size:15px">等待日志输入</div>
      <div style="margin-top:4px;font-size:13px">
        粘贴日志或从其他页面跳转过来进行风险研判
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { APP_CONFIG } from '../../config'
import { Api } from '../../api'
import AlertGuide from '../../components/AlertGuide.vue'
import RiskCard from '../../components/RiskCard.vue'

defineProps<{ mode?: string }>()

const input = ref('')
const deviceType = ref('')
const loading = ref(false)
const result = ref<any>(null)
const deviceOptions = APP_CONFIG.sampleData.deviceTypes

function fillSample() {
  input.value = APP_CONFIG.sampleData.logs[0]
  deviceType.value = 'ssh'
}

async function submit() {
  if (!input.value.trim()) {
    ElMessage.warning('请输入日志内容')
    return
  }
  loading.value = true
  result.value = null
  try {
    const res = await Api.logParse.assess({
      log_line: input.value,
      device_type: deviceType.value || undefined,
    })
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

function goParse() {
  sessionStorage.setItem('log-parse-input', input.value)
  window.location.hash = '#/log-parse/parse'
}

// 从 Identify 或 Parse 页面跳转过来时自动填入
onMounted(() => {
  const saved = sessionStorage.getItem('log-assess-input')
  if (saved) {
    input.value = saved
    sessionStorage.removeItem('log-assess-input')
    // 自动提交研判
    submit()
  }
})
</script>