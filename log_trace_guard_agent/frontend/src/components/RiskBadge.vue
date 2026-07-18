<template>
  <span
    class="risk-badge"
    :class="badgeClass"
    :style="{ background: risk.bg, color: risk.color }"
  >
    {{ displayLabel }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getRiskLevel } from '../config'

const props = withDefaults(defineProps<{
  level?: string
  label?: string
}>(), {
  level: 'normal',
})

const risk = computed(() => getRiskLevel(props.level))
const displayLabel = computed(() => props.label || risk.value.label)

const badgeClass = computed(() => {
  const lv = props.level
  const clsMap: Record<string, string> = {
    critical: 'risk-badge--p0', 'P0_高危': 'risk-badge--p0',
    high: 'risk-badge--p1', 'P1_中危': 'risk-badge--p1',
    medium: 'risk-badge--p2', 'P2_低危': 'risk-badge--p2',
    low: 'risk-badge--p3', 'P3_噪音': 'risk-badge--p3',
    normal: 'risk-badge--normal',
  }
  return clsMap[lv] || 'risk-badge--' + lv
})
</script>