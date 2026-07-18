<template>
  <div class="g-card" style="margin-bottom:12px">
    <div
      v-if="confidencePercent !== null && confidencePercent < 70"
      class="g-alert g-alert--warning" style="margin-bottom:12px"
    >
      <el-icon><WarningFilled /></el-icon>
      <span>低置信度识别结果（{{ confidencePercent }}%），建议人工复核确认</span>
    </div>
    <div
      v-if="isHighRisk"
      class="g-alert g-alert--danger" style="margin-bottom:12px"
    >
      <el-icon><CircleCloseFilled /></el-icon>
      <div>
        <div style="font-weight:600">高危风险 — 请立即处置</div>
        <div style="margin-top:4px;font-size:12px">{{ disposition || '建议立即隔离受影响资产，排查攻击来源，启动应急响应流程。' }}</div>
      </div>
    </div>
    <div class="g-card-header">
      <div>
        <div class="g-card-title">
          <RiskBadge :level="level" />
          <span>{{ title }}</span>
        </div>
        <div v-if="source" class="g-card-desc">匹配来源: {{ source }}</div>
      </div>
      <div v-if="confidencePercent !== null" style="text-align:right">
        <div style="font-size:12px;color:var(--text-tertiary)">置信度</div>
        <div style="font-size:18px;font-weight:600;color:var(--primary)">{{ confidencePercent }}%</div>
      </div>
    </div>
    <div
      v-if="details && Object.keys(details).length"
      style="font-size:13px;line-height:1.8"
    >
      <div
        v-for="(val, key) in details" :key="key"
        style="display:flex;gap:8px;padding:4px 0;border-bottom:1px solid var(--border-light)"
      >
        <span style="color:var(--text-tertiary);min-width:80px;flex-shrink:0">{{ key }}</span>
        <span style="color:var(--text-primary);word-break:break-all">{{ val }}</span>
      </div>
    </div>
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getRiskLevel } from '../config'
import RiskBadge from './RiskBadge.vue'

const props = withDefaults(defineProps<{
  title?: string
  level?: string
  confidence?: number
  source?: string
  details?: Record<string, string>
  disposition?: string
}>(), { level: 'normal' })

const risk = computed(() => getRiskLevel(props.level))
const confidencePercent = computed(() =>
  props.confidence ? Math.round(props.confidence) : null
)
const isHighRisk = computed(() =>
  ['critical', 'high', 'P0_高危', 'P1_中危'].includes(props.level)
)
</script>